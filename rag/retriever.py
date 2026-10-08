"""Small-corpus hybrid retrieval: BM25-like lexical + dense concept vectors."""

from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from rag.schemas import KnowledgeDocument, RetrievalHit, RetrievalResult, TutorDomain

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {"a", "an", "and", "are", "do", "does", "for", "how", "i", "in", "is", "of", "the", "to", "what", "who"}
QUESTION_WRAPPERS = (
    re.compile(r"^\s*please\s+help\s+me\s+(?:solve|answer|understand)\s*[:,-]?\s*", re.I),
    re.compile(r"^\s*can\s+you\s+(?:solve|answer|explain)\s+(?:this\s+)?(?:problem|question)?\s*[:,-]?\s*", re.I),
    re.compile(r"^\s*i\s+need\s+help\s+with\s*[:,-]?\s*", re.I),
)
CONCEPTS = {
    "force": {"force", "newton", "mass", "acceleration"},
    "energy": {"energy", "work", "joule", "kinetic", "potential"},
    "motion": {"motion", "velocity", "speed", "distance", "time"},
    "algebra": {"algebra", "equation", "variable", "solve", "linear"},
    "derivative": {"derivative", "calculus", "slope", "rate", "change"},
    "probability": {"probability", "chance", "outcome", "event"},
    "atom": {"atom", "electron", "proton", "neutron", "nucleus"},
    "cell": {"cell", "membrane", "nucleus", "biology", "organelle"},
    "algorithm": {"algorithm", "complexity", "steps", "computer", "program"},
    "rag": {"rag", "retrieval", "generation", "embedding", "context"},
    "linear_algebra": {"linear", "algebra", "matrix", "vector", "determinant", "eigenvalue"},
    "geometry": {"geometry", "triangle", "circle", "rectangle", "area", "perimeter", "angle"},
}


def normalize_question(text: str) -> str:
    """Normalize harmless punctuation and whitespace differences for exact lookup."""
    return " ".join(tokenize(text))


def question_lookup_keys(text: str) -> list[str]:
    """Return exact keys plus narrowly-scoped conversational-wrapper variants."""
    keys = [normalize_question(text)]
    for wrapper in QUESTION_WRAPPERS:
        unwrapped = wrapper.sub("", text, count=1)
        if unwrapped != text:
            normalized = normalize_question(unwrapped)
            if normalized and normalized not in keys:
                keys.append(normalized)
    return keys


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOP_WORDS]


def concept_vector(text: str) -> list[float]:
    tokens = set(tokenize(text))
    return [len(tokens & words) / len(words) for words in CONCEPTS.values()]


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    denominator = math.sqrt(sum(a * a for a in left)) * math.sqrt(
        sum(b * b for b in right)
    )
    return dot / denominator if denominator else 0.0


class HybridRetriever:
    def __init__(self, corpus_path: Path | None = None, threshold: float = 0.032):
        path = corpus_path or Path(__file__).with_name("data") / "knowledge.json"
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            validated = TypeAdapter(list[KnowledgeDocument]).validate_python(parsed)
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            raise ValueError(f"Invalid retrieval corpus: {path}") from error
        self.documents = [document.model_dump(mode="json") for document in validated]
        document_ids = [doc["id"] for doc in self.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("Retrieval corpus document IDs must be unique")
        if not self.documents:
            raise ValueError("Retrieval corpus cannot be empty")
        self.threshold = threshold
        self._tokens = [
            tokenize(f'{doc["topic"]} {doc["question"]} {doc["answer"]}')
            for doc in self.documents
        ]
        self._vectors = [concept_vector(" ".join(tokens)) for tokens in self._tokens]
        self._document_frequency = Counter(
            token for tokens in self._tokens for token in set(tokens)
        )
        self._average_length = sum(map(len, self._tokens)) / len(self._tokens)
        normalized_questions = [normalize_question(doc["question"]) for doc in self.documents]
        if len(normalized_questions) != len(set(normalized_questions)):
            raise ValueError("Retrieval corpus questions must be unique after normalization")
        self._exact_questions = {
            question: index for index, question in enumerate(normalized_questions)
        }

    def _bm25(self, query_tokens: list[str], index: int) -> float:
        terms = Counter(self._tokens[index])
        length = len(self._tokens[index]) or 1
        score = 0.0
        for token in query_tokens:
            frequency = terms[token]
            if not frequency:
                continue
            idf = math.log(1 + (len(self.documents) - self._document_frequency[token] + 0.5) / (self._document_frequency[token] + 0.5))
            score += idf * frequency * 2.2 / (
                frequency + 1.2 * (0.25 + 0.75 * length / self._average_length)
            )
        return score

    def exact_match(self, query: str, domain: TutorDomain | None = None) -> RetrievalHit | None:
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        index = next(
            (self._exact_questions[key] for key in question_lookup_keys(query)
             if key in self._exact_questions),
            None,
        )
        if index is None:
            return None
        document = self.documents[index]
        if domain is not None and document["domain"] != domain.value:
            return None
        return RetrievalHit(**document, score=1.0)

    def beginner_questions(
        self, query: str, domain: TutorDomain, limit: int = 5
    ) -> list[RetrievalHit]:
        """Return easy, topic-relevant Q&A examples for a learning plan."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        result = self.retrieve(query, top_k=max(limit * 4, 20), domain=domain)
        beginner_ids = {
            doc["id"] for doc in self.documents if doc["difficulty"] == "beginner"
        }
        selected = [hit for hit in result.hits if hit.id in beginner_ids]
        if len(selected) < limit:
            seen = {hit.id for hit in selected}
            for document in self.documents:
                if (
                    document["domain"] == domain.value
                    and document["difficulty"] == "beginner"
                    and document["id"] not in seen
                ):
                    selected.append(RetrievalHit(**document, score=0.0))
                    seen.add(document["id"])
                    if len(selected) == limit:
                        break
        return selected[:limit]

    @staticmethod
    def _ranks(scores: list[float]) -> dict[int, int]:
        return {index: rank for rank, (index, _) in enumerate(sorted(enumerate(scores), key=lambda item: item[1], reverse=True), 1)}

    def retrieve(self, query: str, top_k: int = 3, domain: TutorDomain | None = None) -> RetrievalResult:
        started = time.perf_counter()
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if not query.strip():
            return RetrievalResult(hits=[], latency_ms=(time.perf_counter() - started) * 1000, confident=False)
        exact = self.exact_match(query, domain=domain)
        if exact is not None:
            return RetrievalResult(
                hits=[exact],
                latency_ms=(time.perf_counter() - started) * 1000,
                confident=True,
            )
        query_tokens = tokenize(query)
        sparse = [self._bm25(query_tokens, index) for index in range(len(self.documents))]
        query_vector = concept_vector(query)
        dense = [cosine(query_vector, vector) for vector in self._vectors]
        allowed = [i for i, doc in enumerate(self.documents) if domain is None or doc["domain"] == domain.value]
        if not allowed:
            return RetrievalResult(hits=[], latency_ms=(time.perf_counter() - started) * 1000, confident=False)
        sparse_local = [sparse[i] for i in allowed]
        dense_local = [dense[i] for i in allowed]
        sparse_order = self._ranks(sparse_local)
        dense_order = self._ranks(dense_local)
        sparse_ranks = {allowed[local]: rank for local, rank in sparse_order.items()}
        dense_ranks = {allowed[local]: rank for local, rank in dense_order.items()}
        # Reciprocal-rank fusion is robust when component scores use different scales.
        fused = {i: 1 / (60 + sparse_ranks[i]) + 1 / (60 + dense_ranks[i]) for i in allowed}
        selected = sorted(allowed, key=fused.__getitem__, reverse=True)[:top_k]
        hits = [RetrievalHit(**self.documents[i], score=fused[i]) for i in selected]
        latency_ms = (time.perf_counter() - started) * 1000
        lexical_overlap = len(set(query_tokens) & set(self._tokens[selected[0]]))
        # One generic shared word is not enough to keep a question in-domain.
        # Concept-vector agreement supports short queries such as "define atom".
        evidence_match = lexical_overlap >= 2 or max(dense[i] for i in allowed) > 0.2
        confident = bool(hits and hits[0].score >= self.threshold and evidence_match)
        return RetrievalResult(hits=hits, latency_ms=latency_ms, confident=confident)
