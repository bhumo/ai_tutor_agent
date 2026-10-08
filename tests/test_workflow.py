import json

import pytest
from pydantic import ValidationError

from graph.workflow import TutorWorkflow
from rag.schemas import DomainDecision, GroundedGeneration, TutorDomain
from rag.web_search import FallbackAuditLogger


class FakeJudge:
    def classify(self, query):
        lowered = query.lower()
        if "bread" in lowered or "sistine" in lowered:
            return DomainDecision(supported=False, domain=TutorDomain.UNSUPPORTED,
                                  reason="The request is outside supported STEM tutoring.", confidence=0.99)
        domain = TutorDomain.PHYSICS if "energy" in lowered else TutorDomain.MATH
        return DomainDecision(supported=True, domain=domain,
                              reason=f"This is a {domain.value} learning question.", confidence=0.95)


class FakeGenerator:
    def generate(self, query, contexts):
        return GroundedGeneration(answer=f'Grounded answer from {contexts[0]["title"]}',
                                  cited_context_ids=[contexts[0]["id"]], confidence=0.9)

    def generate_from_model(self, query, domain, resources):
        return GroundedGeneration(answer=f"General {domain} explanation",
                                  cited_context_ids=[resources[0]["id"]], confidence=0.7)

    def generate_learning_plan(self, query, questions):
        return GroundedGeneration(
            answer="Start with vectors and linear equations, then practice the suggested problems.",
            cited_context_ids=[item["id"] for item in questions[:3]], confidence=0.85,
        )


def make_workflow(tmp_path):
    return TutorWorkflow(judge=FakeJudge(), generator=FakeGenerator(),
                         audit_logger=FallbackAuditLogger(tmp_path / "fallback.jsonl"))


def test_judge_routes_known_question_then_domain_retrieval_answers(tmp_path):
    answer = make_workflow(tmp_path).process("What is kinetic energy?")
    assert answer.route == "rag"
    assert answer.domain == "physics"
    assert answer.source == "knowledge_base"
    assert answer.citations[0].purpose == "evidence"


def test_supported_question_missing_from_corpus_uses_model_and_safe_resources(tmp_path):
    answer = make_workflow(tmp_path).process("How do quadratic equations work?", trace_id="trace-123")
    event = json.loads((tmp_path / "fallback.jsonl").read_text().strip())
    assert answer.route == "model_fallback"
    assert answer.domain == "math"
    assert answer.citations[0].purpose == "further_reading"
    assert answer.citations[0].url.host in {"www.khanacademy.org", "openstax.org"}
    assert event["provider"] == "trusted_resource_catalog"
    assert event["trace_id"] == "trace-123"


def test_model_fallback_supplies_safe_citation_when_model_returns_none(tmp_path):
    workflow = make_workflow(tmp_path)
    workflow.generator.generate_from_model = lambda query, domain, resources: GroundedGeneration(
        answer=f"General {domain} explanation", cited_context_ids=[], confidence=0.7
    )

    answer = workflow.process("How do quadratic equations work?")

    assert answer.route == "model_fallback"
    assert len(answer.citations) == 1
    assert answer.citations[0].purpose == "further_reading"


def test_exact_database_question_returns_stored_answer_verbatim(tmp_path):
    workflow = make_workflow(tmp_path)
    question = "Solve 2x + 0 = 2."
    stored = workflow.retriever.exact_match(question, TutorDomain.MATH)

    answer = workflow.process(question)

    assert stored is not None
    assert answer.answer == stored.answer
    assert answer.route == "rag"
    assert answer.source == "knowledge_base"
    assert answer.confidence == 1.0


def test_exact_database_question_bypasses_router_and_generator(tmp_path):
    class FailingJudge:
        def classify(self, query):
            raise AssertionError("Exact database lookup should bypass the model router")

    class FailingGenerator(FakeGenerator):
        def generate(self, query, contexts):
            raise AssertionError("Exact database lookup should bypass generation")

    workflow = TutorWorkflow(
        judge=FailingJudge(), generator=FailingGenerator(),
        audit_logger=FallbackAuditLogger(tmp_path / "fallback.jsonl"),
    )

    answer = workflow.process("solve 2X + 0 = 2!!!")

    assert answer.answer.endswith("Therefore x = 1.")
    assert answer.source == "knowledge_base"


def test_learning_request_blends_model_plan_with_beginner_question_bank(tmp_path):
    answer = make_workflow(tmp_path).process("I am a beginner. Teach me linear algebra.")

    assert answer.route == "learning_plan"
    assert answer.source == "blended"
    assert len(answer.citations) == 3
    assert all(citation.purpose == "evidence" for citation in answer.citations)


def test_unsupported_question_is_rejected_without_fallback(tmp_path):
    log_path = tmp_path / "fallback.jsonl"
    answer = make_workflow(tmp_path).process("How do I bake sourdough bread?")
    assert answer.route == "rejected"
    assert answer.domain == "unsupported"
    assert answer.citations == []
    assert not log_path.exists()


def test_invalid_llm_output_is_rejected():
    with pytest.raises(ValidationError):
        GroundedGeneration(answer="", cited_context_ids=[], confidence=2)


def test_inconsistent_judge_output_is_rejected():
    with pytest.raises(ValidationError):
        DomainDecision(supported=True, domain=TutorDomain.UNSUPPORTED,
                       reason="invalid", confidence=0.8)
