"""Production-oriented contract, relevance, isolation, and performance tests."""

import json
import math
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from rag.retriever import HybridRetriever
from rag.schemas import TutorDomain


CASES_PATH = Path(__file__).with_name("retrieval_cases.json")


@pytest.fixture(scope="module")
def retriever() -> HybridRetriever:
    return HybridRetriever()


@pytest.fixture(scope="module")
def golden_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def reciprocal_rank(returned: list[str], relevant: set[str]) -> float:
    for rank, document_id in enumerate(returned, 1):
        if document_id in relevant:
            return 1 / rank
    return 0.0


class TestCorpusContract:
    def test_corpus_has_unique_ids_and_supported_domains(self, retriever):
        ids = [document["id"] for document in retriever.documents]
        assert len(ids) == len(set(ids))
        assert all(document["domain"] != TutorDomain.UNSUPPORTED for document in retriever.documents)

    @pytest.mark.parametrize("missing_field", ["id", "domain", "topic", "question", "answer"])
    def test_malformed_corpus_is_rejected_at_startup(self, tmp_path, missing_field):
        document = {
            "id": "doc-1", "domain": "math", "topic": "algebra",
            "question": "What is x?", "answer": "A variable.",
        }
        document.pop(missing_field)
        path = tmp_path / "bad-corpus.json"
        path.write_text(json.dumps([document]), encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid retrieval corpus"):
            HybridRetriever(path)

    def test_duplicate_document_ids_are_rejected(self, tmp_path):
        document = {
            "id": "duplicate", "domain": "math", "topic": "algebra",
            "question": "What is x?", "answer": "A variable.",
        }
        path = tmp_path / "duplicate.json"
        path.write_text(json.dumps([document, document]), encoding="utf-8")
        with pytest.raises(ValueError, match="must be unique"):
            HybridRetriever(path)

    def test_normalized_duplicate_questions_are_rejected(self, tmp_path):
        documents = [
            {
                "id": "one", "domain": "math", "topic": "algebra",
                "question": "Solve x + 1 = 2.", "answer": "x = 1.",
            },
            {
                "id": "two", "domain": "math", "topic": "algebra",
                "question": "  SOLVE x + 1 = 2!!! ", "answer": "x = 1.",
            },
        ]
        path = tmp_path / "normalized-duplicate.json"
        path.write_text(json.dumps(documents), encoding="utf-8")
        with pytest.raises(ValueError, match="unique after normalization"):
            HybridRetriever(path)

    def test_empty_corpus_is_rejected(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="cannot be empty"):
            HybridRetriever(path)

    def test_expanded_math_bank_has_expected_size_and_balance(self, retriever):
        linear_algebra = [doc for doc in retriever.documents if doc["id"].startswith("la-")]
        geometry = [doc for doc in retriever.documents if doc["id"].startswith("geo-")]
        assert len(linear_algebra) == 250
        assert len(geometry) == 250
        assert sum(doc["difficulty"] == "beginner" for doc in retriever.documents) >= 300


class TestRetrievalQuality:
    def test_exact_match_ignores_case_punctuation_and_extra_whitespace(self, retriever):
        hit = retriever.exact_match("  SOLVE 2X + 0 = 2!!! ", TutorDomain.MATH)
        assert hit is not None
        assert hit.id == "la-equation-001"
        assert hit.score == 1.0

    def test_exact_match_respects_domain_boundary(self, retriever):
        assert retriever.exact_match(
            "Solve 2x + 0 = 2.", TutorDomain.PHYSICS
        ) is None

    @pytest.mark.parametrize(
        ("query", "expected_prefix"),
        [
            ("Find the determinant of the matrix [[1, -3], [2, -6]].", "la-determinant-"),
            ("A circle has radius 10 units. Find its exact area and circumference.", "geo-circle-"),
            ("Find the distance between (-20, -8) and (-17, -4).", "geo-distance-"),
        ],
    )
    def test_known_bank_questions_retrieve_correct_record(self, retriever, query, expected_prefix):
        result = retriever.retrieve(query, domain=TutorDomain.MATH, top_k=3)
        assert result.confident
        assert result.hits[0].id.startswith(expected_prefix)

    def test_beginner_question_selection_is_relevant_and_bounded(self, retriever):
        hits = retriever.beginner_questions(
            "I want to learn geometry as a beginner", TutorDomain.MATH, limit=5
        )
        assert len(hits) == 5
        assert all(hit.domain == TutorDomain.MATH for hit in hits)
        assert all(hit.id.startswith("geo-") for hit in hits)
    def test_golden_set_top1_accuracy_and_mrr(self, retriever, golden_cases):
        top1 = 0
        reciprocal_ranks = []
        for case in golden_cases:
            result = retriever.retrieve(
                case["query"], domain=TutorDomain(case["domain"]), top_k=3
            )
            returned = [hit.id for hit in result.hits]
            relevant = set(case["relevant"])
            top1 += bool(returned and returned[0] in relevant)
            reciprocal_ranks.append(reciprocal_rank(returned, relevant))
            assert result.confident, f'{case["id"]} was unexpectedly sent to fallback'
        assert top1 / len(golden_cases) >= 0.95
        assert statistics.mean(reciprocal_ranks) >= 0.95

    @pytest.mark.parametrize(
        ("query", "domain"),
        [
            ("How do I bake sourdough bread?", TutorDomain.MATH),
            ("What caused the French Revolution?", TutorDomain.PHYSICS),
            ("Recommend a hotel in Paris", TutorDomain.COMPUTER_SCIENCE),
            ("Who painted the Sistine Chapel?", TutorDomain.BIOLOGY),
        ],
    )
    def test_out_of_corpus_queries_are_not_confident(self, retriever, query, domain):
        assert retriever.retrieve(query, domain=domain).confident is False

    def test_domain_filter_never_leaks_cross_domain_documents(self, retriever):
        for domain in TutorDomain:
            if domain == TutorDomain.UNSUPPORTED:
                continue
            result = retriever.retrieve("energy atom cell algorithm equation", domain=domain, top_k=20)
            assert result.hits
            assert {hit.domain for hit in result.hits} == {domain}

    def test_ranked_scores_are_finite_nonnegative_and_descending(self, retriever):
        result = retriever.retrieve("force mass acceleration", domain=TutorDomain.PHYSICS)
        scores = [hit.score for hit in result.hits]
        assert all(math.isfinite(score) and score >= 0 for score in scores)
        assert scores == sorted(scores, reverse=True)

    def test_retrieval_is_deterministic_and_does_not_mutate_index(self, retriever):
        before = json.dumps(retriever.documents, sort_keys=True)
        rankings = [
            [hit.id for hit in retriever.retrieve(
                "instantaneous tangent slope", domain=TutorDomain.MATH
            ).hits]
            for _ in range(20)
        ]
        assert all(ranking == rankings[0] for ranking in rankings)
        assert json.dumps(retriever.documents, sort_keys=True) == before


class TestInputContract:
    @pytest.mark.parametrize("query", ["", " ", "\n\t"])
    def test_blank_query_returns_no_hits(self, retriever, query):
        result = retriever.retrieve(query, domain=TutorDomain.MATH)
        assert result.hits == []
        assert result.confident is False

    @pytest.mark.parametrize("query", [None, 42, ["energy"]])
    def test_non_string_query_is_rejected(self, retriever, query):
        with pytest.raises(TypeError, match="query must be a string"):
            retriever.retrieve(query)

    @pytest.mark.parametrize("top_k", [0, -1, -100])
    def test_invalid_top_k_is_rejected(self, retriever, top_k):
        with pytest.raises(ValueError, match="top_k must be at least 1"):
            retriever.retrieve("energy", top_k=top_k)

    def test_large_top_k_is_safely_bounded_by_domain_size(self, retriever):
        result = retriever.retrieve("physics", top_k=10_000, domain=TutorDomain.PHYSICS)
        assert len(result.hits) == 3

    def test_long_and_unicode_query_does_not_crash(self, retriever):
        query = "⚛️ énergie 能量 kinetic " + "explain " * 5_000
        result = retriever.retrieve(query, domain=TutorDomain.PHYSICS)
        assert result.hits
        assert result.latency_ms >= 0


class TestOperationalBehavior:
    def test_concurrent_reads_return_identical_results(self, retriever):
        def retrieve_ids(_):
            return [hit.id for hit in retriever.retrieve(
                "mass acceleration force", domain=TutorDomain.PHYSICS
            ).hits]

        with ThreadPoolExecutor(max_workers=8) as executor:
            rankings = list(executor.map(retrieve_ids, range(100)))
        assert all(ranking == rankings[0] for ranking in rankings)

    def test_warm_retrieval_p95_is_below_service_budget(self, retriever):
        for _ in range(20):
            retriever.retrieve("Explain kinetic energy", domain=TutorDomain.PHYSICS)
        latencies = [
            retriever.retrieve("Explain kinetic energy", domain=TutorDomain.PHYSICS).latency_ms
            for _ in range(500)
        ]
        p95 = statistics.quantiles(latencies, n=100)[94]
        assert p95 < 200, f"retrieval p95 was {p95:.2f}ms"
