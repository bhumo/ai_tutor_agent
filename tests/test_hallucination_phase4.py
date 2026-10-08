import pytest

from evaluation.hallucination import evaluate_hallucination_gate
from graph.workflow import TutorWorkflow
from rag.schemas import DomainDecision, GroundedGeneration, TutorDomain


class MathJudge:
    def classify(self, query):
        return DomainDecision(
            supported=True, domain=TutorDomain.MATH,
            reason="Math evaluation case.", confidence=1.0,
        )


class UnknownCitationGenerator:
    def generate(self, query, contexts):
        return GroundedGeneration(
            answer="Invented claim.", cited_context_ids=["not-retrieved"], confidence=0.99
        )

    def generate_from_model(self, query, domain, resources):
        raise AssertionError("unexpected fallback")

    def generate_learning_plan(self, query, questions):
        raise AssertionError("unexpected learning plan")


def test_full_corpus_hallucination_gate_passes():
    report = evaluate_hallucination_gate()
    assert report.documents >= 500
    assert report.variant_cases == report.documents * 4
    assert report.passed, report.failures[:10]


def test_grounded_generation_rejects_hallucinated_citation_id(tmp_path):
    workflow = TutorWorkflow(judge=MathJudge(), generator=UnknownCitationGenerator())
    with pytest.raises(ValueError, match="did not cite retrieved evidence"):
        workflow.process("Explain the determinant of a two by two matrix")
