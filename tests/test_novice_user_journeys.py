"""Acceptance tests for students who have no knowledge of the app or its corpus."""

from pathlib import Path

import pytest

from graph.workflow import TutorWorkflow
from rag.schemas import DomainDecision, GroundedGeneration, TutorDomain
from rag.web_search import FallbackAuditLogger


class NoviceJudge:
    """Deterministic stand-in for the semantic router in user-journey tests."""

    def classify(self, query: str) -> DomainDecision:
        lowered = query.lower()
        if any(term in lowered for term in ("bread", "hotel", "french revolution", "help")):
            return DomainDecision(
                supported=False,
                domain=TutorDomain.UNSUPPORTED,
                reason="This request is outside the supported tutoring domains.",
                confidence=0.99,
            )
        return DomainDecision(
            supported=True,
            domain=TutorDomain.MATH,
            reason="This is a mathematics learning request.",
            confidence=0.95,
        )


class NoviceGenerator:
    def generate(self, query, contexts):
        return GroundedGeneration(
            answer=f'Here is a database-grounded explanation: {contexts[0]["text"]}',
            cited_context_ids=[contexts[0]["id"]],
            confidence=0.9,
        )

    def generate_from_model(self, query, domain, resources):
        return GroundedGeneration(
            answer="Here is a beginner-friendly explanation using general model knowledge.",
            cited_context_ids=[],
            confidence=0.7,
        )

    def generate_learning_plan(self, query, questions):
        prompts = "; ".join(item["question"] for item in questions[:3])
        return GroundedGeneration(
            answer=f"Start with the basics, then try these exercises: {prompts}",
            cited_context_ids=[item["id"] for item in questions[:3]],
            confidence=0.85,
        )


@pytest.fixture
def workflow(tmp_path: Path) -> TutorWorkflow:
    return TutorWorkflow(
        judge=NoviceJudge(),
        generator=NoviceGenerator(),
        audit_logger=FallbackAuditLogger(tmp_path / "fallback.jsonl"),
    )


class TestNoviceDiscovery:
    def test_user_can_ask_exact_question_without_knowing_database_exists(self, workflow):
        answer = workflow.process("Solve 2x + 0 = 2.")
        assert answer.answer == (
            "Subtract 0 from both sides to get 2x = 2, then divide by 2. Therefore x = 1."
        )
        assert answer.source == "knowledge_base"
        assert answer.confidence == 1.0

    def test_case_punctuation_and_whitespace_do_not_break_exact_lookup(self, workflow):
        answer = workflow.process("   SOLVE 2X + 0 = 2!!!   ")
        assert answer.answer.endswith("Therefore x = 1.")
        assert answer.source == "knowledge_base"

    @pytest.mark.parametrize(
        "query",
        [
            "can u show me how vectors add?",
            "whats a determnant and how does it work?",
            "circle radius 10 area?",
        ],
    )
    def test_casual_or_misspelled_math_still_gets_a_safe_answer(self, workflow, query):
        answer = workflow.process(query)
        assert answer.answer
        assert answer.domain == TutorDomain.MATH
        assert answer.route in {"rag", "model_fallback"}
        assert answer.citations


class TestNoviceLearningRequests:
    @pytest.mark.parametrize(
        "query",
        [
            "I know nothing about geometry. Where do I start?",
            "I am a beginner. Teach me linear algebra.",
            "give me an easy algebra question",
            "I want to practice vectors",
        ],
    )
    def test_learning_language_returns_plan_and_database_exercises(self, workflow, query):
        answer = workflow.process(query)
        assert answer.route == "learning_plan"
        assert answer.source == "blended"
        assert answer.answer
        assert 1 <= len(answer.citations) <= 3
        assert all(citation.purpose == "evidence" for citation in answer.citations)


class TestNoviceUnhappyPaths:
    @pytest.mark.parametrize(
        "query",
        [
            "How do I bake bread?",
            "Recommend a hotel",
            "What caused the French Revolution?",
            "help",
        ],
    )
    def test_unsupported_or_context_free_requests_fail_safely(self, workflow, query):
        answer = workflow.process(query)
        assert answer.route == "rejected"
        assert answer.source == "rejected"
        assert "math" in answer.answer.lower()
        assert answer.citations == []

    def test_exact_question_from_wrong_domain_cannot_leak_through_retriever(self, workflow):
        assert workflow.retriever.exact_match(
            "Solve 2x + 0 = 2.", TutorDomain.PHYSICS
        ) is None

    def test_empty_input_has_no_retrieval_confidence(self, workflow):
        result = workflow.retriever.retrieve("", domain=TutorDomain.MATH)
        assert result.hits == []
        assert result.confident is False
