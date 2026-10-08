"""Deterministic hallucination and grounded-retrieval release gate."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from rag.retriever import HybridRetriever
from rag.schemas import TutorDomain


QUERY_VARIANTS = (
    "{question}",
    "Please help me solve: {question}",
    "Can you explain this problem: {question}",
    "I need help with: {question}",
)

UNSUPPORTED_DISTRACTORS = (
    "How do I bake sourdough bread?",
    "Recommend a hotel in Paris.",
    "Who painted the Sistine Chapel?",
    "Write a sales email for a shoe store.",
)


@dataclass(frozen=True)
class HallucinationReport:
    documents: int
    variant_cases: int
    answer_integrity: float
    retrieval_hit_at_1: float
    unsupported_abstention: float
    failures: list[dict[str, str]]

    @property
    def passed(self) -> bool:
        return (
            self.answer_integrity == 1.0
            and self.retrieval_hit_at_1 == 1.0
            and self.unsupported_abstention == 1.0
        )


def evaluate_hallucination_gate(
    retriever: HybridRetriever | None = None,
) -> HallucinationReport:
    """Check that known Q&A stays verbatim and distractors do not become grounded."""
    retriever = retriever or HybridRetriever()
    failures: list[dict[str, str]] = []
    integrity_correct = retrieval_correct = total = 0

    for document in retriever.documents:
        domain = TutorDomain(document["domain"])
        for template in QUERY_VARIANTS:
            total += 1
            query = template.format(question=document["question"])
            exact = retriever.exact_match(query, domain=domain)
            retrieval = retriever.retrieve(query, domain=domain, top_k=3)
            retrieved_id = retrieval.hits[0].id if retrieval.hits else ""
            if exact is not None and exact.answer == document["answer"]:
                integrity_correct += 1
            else:
                failures.append({
                    "kind": "answer_integrity", "document_id": document["id"],
                    "query": query,
                })
            if retrieval.confident and retrieved_id == document["id"]:
                retrieval_correct += 1
            else:
                failures.append({
                    "kind": "retrieval_hit_at_1", "document_id": document["id"],
                    "query": query, "retrieved_id": retrieved_id,
                })

    abstained = 0
    for query in UNSUPPORTED_DISTRACTORS:
        # Run against every supported domain to catch accidental cross-domain grounding.
        domain_results = [
            retriever.retrieve(query, domain=domain).confident
            for domain in TutorDomain if domain != TutorDomain.UNSUPPORTED
        ]
        if not any(domain_results):
            abstained += 1
        else:
            failures.append({"kind": "unsupported_abstention", "query": query})

    return HallucinationReport(
        documents=len(retriever.documents),
        variant_cases=total,
        answer_integrity=integrity_correct / total if total else 0.0,
        retrieval_hit_at_1=retrieval_correct / total if total else 0.0,
        unsupported_abstention=abstained / len(UNSUPPORTED_DISTRACTORS),
        failures=failures,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate_hallucination_gate()
    payload = asdict(report) | {"passed": report.passed}
    rendered = json.dumps(payload, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if not report.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
