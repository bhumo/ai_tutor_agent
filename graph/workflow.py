from __future__ import annotations

import time
import uuid
import re
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from rag.generator import AnswerGenerator, GeminiAnswerGenerator
from rag.observability import observed, score_current_trace
from rag.resources import TrustedResourceSearch
from rag.retriever import HybridRetriever
from rag.router import DomainJudge, GeminiDomainJudge
from rag.schemas import (
    AnswerSource, Citation, DomainDecision, TutorAnswer, TutorDomain,
)
from rag.web_search import FallbackAuditLogger


class WorkflowState(TypedDict, total=False):
    query: str
    trace_id: str
    decision: DomainDecision
    retrieval: Any
    answer: TutorAnswer


class TutorWorkflow:
    """Semantic routing first; category-scoped retrieval second."""

    def __init__(self, api_key: str | None = None, *, judge: DomainJudge | None = None,
                 retriever: HybridRetriever | None = None, generator: AnswerGenerator | None = None,
                 resource_search: TrustedResourceSearch | None = None,
                 audit_logger: FallbackAuditLogger | None = None, **_: Any):
        if (judge is None or generator is None) and not api_key:
            raise ValueError("api_key or both judge and generator are required")
        self.judge = judge or GeminiDomainJudge(api_key=api_key or "")
        self.generator = generator or GeminiAnswerGenerator(api_key=api_key or "")
        self.retriever = retriever or HybridRetriever()
        self.resource_search = resource_search or TrustedResourceSearch()
        self.audit_logger = audit_logger or FallbackAuditLogger(Path("logs/model_fallback.jsonl"))

        graph = StateGraph(WorkflowState)
        graph.add_node("scope_judge", self._scope_judge)
        graph.add_node("math_agent", self._domain_agent)
        graph.add_node("physics_agent", self._domain_agent)
        graph.add_node("chemistry_agent", self._domain_agent)
        graph.add_node("biology_agent", self._domain_agent)
        graph.add_node("computer_science_agent", self._domain_agent)
        graph.add_node("reject", self._reject)
        graph.set_entry_point("scope_judge")
        graph.add_conditional_edges("scope_judge", self._route, {
            "math": "math_agent", "physics": "physics_agent",
            "chemistry": "chemistry_agent", "biology": "biology_agent",
            "computer_science": "computer_science_agent", "unsupported": "reject",
        })
        for node in ("math_agent", "physics_agent", "chemistry_agent", "biology_agent",
                     "computer_science_agent", "reject"):
            graph.add_edge(node, END)
        self.app = graph.compile()

    @observed(name="semantic-scope-judge", as_type="evaluator")
    def _scope_judge(self, state: WorkflowState) -> WorkflowState:
        decision = self.judge.classify(state["query"])
        score_current_trace("router_confidence", decision.confidence)
        score_current_trace("supported_domain", decision.supported, data_type="BOOLEAN")
        return {"decision": decision}

    @staticmethod
    def _route(state: WorkflowState) -> str:
        return state["decision"].domain.value

    @observed(name="domain-agent", as_type="agent")
    def _domain_agent(self, state: WorkflowState) -> WorkflowState:
        domain = state["decision"].domain
        exact = self.retriever.exact_match(state["query"], domain=domain)
        if exact is not None:
            answer = self._exact_database_answer(state, exact)
            score_current_trace("exact_database_match", True, data_type="BOOLEAN")
            return {"answer": answer}
        if self._is_learning_request(state["query"]):
            questions = self.retriever.beginner_questions(state["query"], domain=domain)
            if questions:
                answer = self._learning_plan(state, questions)
                score_current_trace("learning_plan", True, data_type="BOOLEAN")
                return {"answer": answer}
        retrieval = self.retriever.retrieve(state["query"], domain=domain)
        if retrieval.confident:
            answer = self._grounded_answer(state, retrieval)
            score_current_trace("local_context_found", True, data_type="BOOLEAN")
        else:
            answer = self._model_fallback(state, retrieval)
            score_current_trace("local_context_found", False, data_type="BOOLEAN")
        return {"retrieval": retrieval, "answer": answer}

    @staticmethod
    def _is_learning_request(query: str) -> bool:
        normalized = re.sub(r"[^a-z0-9]+", " ", query.lower())
        learning_terms = (
            "learn", "teach", "study", "beginner", "start", "roadmap", "practice", "easy"
        )
        topic_terms = (
            "math", "algebra", "geometry", "matrix", "matrices", "vector", "vectors"
        )
        return any(term in normalized.split() for term in learning_terms) and any(
            term in normalized.split() for term in topic_terms
        )

    def _exact_database_answer(self, state: WorkflowState, hit: Any) -> TutorAnswer:
        decision = state["decision"]
        return TutorAnswer(
            answer=hit.answer,
            route="rag",
            source=AnswerSource.KNOWLEDGE_BASE,
            citations=[Citation(title=hit.question, purpose="evidence")],
            confidence=1.0,
            retrieval_latency_ms=0,
            trace_id=state["trace_id"],
            domain=decision.domain,
            routing_reason=decision.reason,
        )

    @observed(name="learning-plan", as_type="generation")
    def _learning_plan(self, state: WorkflowState, hits: list[Any]) -> TutorAnswer:
        questions = [
            {"id": hit.id, "question": hit.question, "answer": hit.answer} for hit in hits
        ]
        generated = self.generator.generate_learning_plan(state["query"], questions)
        allowed = {item["id"]: item for item in questions}
        cited = [item for item in generated.cited_context_ids if item in allowed]
        if not cited:
            cited = list(allowed)[:3]
        decision = state["decision"]
        return TutorAnswer(
            answer=generated.answer,
            route="learning_plan",
            source=AnswerSource.BLENDED,
            citations=[Citation(title=allowed[item]["question"], purpose="evidence") for item in cited],
            confidence=generated.confidence,
            retrieval_latency_ms=0,
            trace_id=state["trace_id"],
            domain=decision.domain,
            routing_reason=decision.reason,
        )

    @observed(name="grounded-generation", as_type="generation")
    def _grounded_answer(self, state: WorkflowState, retrieval: Any) -> TutorAnswer:
        contexts = [{"id": hit.id, "title": hit.question, "text": hit.answer}
                    for hit in retrieval.hits]
        generated = self.generator.generate(state["query"], contexts)
        allowed = {item["id"]: item for item in contexts}
        cited = [item for item in generated.cited_context_ids if item in allowed]
        if not cited:
            raise ValueError("LLM response did not cite retrieved evidence")
        decision = state["decision"]
        return TutorAnswer(
            answer=generated.answer, route="rag", source=AnswerSource.KNOWLEDGE_BASE,
            citations=[Citation(title=allowed[item]["title"], purpose="evidence") for item in cited],
            confidence=generated.confidence, retrieval_latency_ms=retrieval.latency_ms,
            trace_id=state["trace_id"], domain=decision.domain, routing_reason=decision.reason,
        )

    @observed(name="model-knowledge-fallback", as_type="generation")
    def _model_fallback(self, state: WorkflowState, retrieval: Any) -> TutorAnswer:
        started = time.perf_counter()
        decision = state["decision"]
        found = self.resource_search.search(state["query"], decision.domain)
        resources = [{**item, "id": f"resource-{index}"} for index, item in enumerate(found, 1)]
        generated = self.generator.generate_from_model(
            state["query"], decision.domain.value, resources
        )
        lookup = {item["id"]: item for item in resources}
        cited = [item for item in generated.cited_context_ids if item in lookup]
        if not cited:
            cited = list(lookup)[:1]
        self.audit_logger.log(
            query=state["query"], trace_id=state["trace_id"], status="success",
            result_count=len(resources), provider="trusted_resource_catalog",
        )
        return TutorAnswer(
            answer=generated.answer, route="model_fallback", source=AnswerSource.MODEL_FALLBACK,
            citations=[Citation(title=lookup[item]["title"], url=lookup[item]["url"],
                                purpose="further_reading") for item in cited],
            confidence=generated.confidence,
            retrieval_latency_ms=retrieval.latency_ms + (time.perf_counter() - started) * 1000,
            trace_id=state["trace_id"], domain=decision.domain, routing_reason=decision.reason,
        )

    def _reject(self, state: WorkflowState) -> WorkflowState:
        decision = state["decision"]
        return {"answer": TutorAnswer(
            answer="I can currently tutor math, physics, chemistry, biology, and computer science. Please ask a question in one of those areas.",
            route="rejected", source=AnswerSource.REJECTED, citations=[], confidence=decision.confidence,
            retrieval_latency_ms=0, trace_id=state["trace_id"], domain=decision.domain,
            routing_reason=decision.reason,
        )}

    @observed(name="tutor-workflow", as_type="agent")
    def process(self, query: str, trace_id: str | None = None) -> TutorAnswer:
        resolved_trace_id = trace_id or str(uuid.uuid4())
        exact = self.retriever.exact_match(query)
        if exact is not None:
            decision = DomainDecision(
                supported=True,
                domain=exact.domain,
                reason="Exact normalized match in the curated question bank.",
                confidence=1.0,
            )
            return self._exact_database_answer(
                {"query": query, "trace_id": resolved_trace_id, "decision": decision}, exact
            )
        state = self.app.invoke({"query": query, "trace_id": resolved_trace_id})
        return TutorAnswer.model_validate(state["answer"])

    def process_query(self, query: str) -> str:
        return self.process(query).answer
