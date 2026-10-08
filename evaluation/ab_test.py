"""Paired A/B quality gate for retrieval and semantic-routing changes."""

from __future__ import annotations

import argparse
import json
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from rag.config import DEFAULT_GEMINI_MODEL
from rag.retriever import HybridRetriever
from rag.router import GeminiDomainJudge
from rag.schemas import TutorDomain


class VariantConfig(BaseModel):
    name: str
    retrieval_threshold: float = Field(ge=0.0)
    top_k: int = Field(default=3, ge=1, le=20)
    judge_model: str = DEFAULT_GEMINI_MODEL


class ABCase(BaseModel):
    id: str
    query: str
    expected_domain: TutorDomain
    expected_route: str
    expected_document: str | None = None


class VariantMetrics(BaseModel):
    name: str
    case_count: int
    domain_accuracy: float | None
    route_accuracy: float
    retrieval_hit_rate: float
    rag_coverage: float
    retrieval_p95_ms: float
    failures: list[dict]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_variant(config: VariantConfig, cases: list[ABCase], *, api_key: str | None = None,
                     latency_runs: int = 30) -> VariantMetrics:
    retriever = HybridRetriever(threshold=config.retrieval_threshold)
    judge = GeminiDomainJudge(api_key, model=config.judge_model) if api_key else None
    domain_correct = route_correct = retrieval_correct = retrieval_total = rag_count = 0
    failures: list[dict] = []
    latencies: list[float] = []

    for case in cases:
        predicted_domain = judge.classify(case.query).domain if judge else case.expected_domain
        if judge:
            domain_correct += predicted_domain == case.expected_domain
        if predicted_domain == TutorDomain.UNSUPPORTED:
            predicted_route = "rejected"
            result = None
        else:
            result = retriever.retrieve(case.query, top_k=config.top_k, domain=predicted_domain)
            latencies.append(result.latency_ms)
            predicted_route = "rag" if result.confident else "model_fallback"
            rag_count += predicted_route == "rag"

        route_correct += predicted_route == case.expected_route
        document_ok = True
        if case.expected_document:
            retrieval_total += 1
            document_ok = bool(result and any(hit.id == case.expected_document for hit in result.hits))
            retrieval_correct += document_ok
        if predicted_domain != case.expected_domain or predicted_route != case.expected_route or not document_ok:
            failures.append({
                "id": case.id, "predicted_domain": predicted_domain.value,
                "expected_domain": case.expected_domain.value,
                "predicted_route": predicted_route, "expected_route": case.expected_route,
                "expected_document": case.expected_document,
                "retrieved_documents": [hit.id for hit in result.hits] if result else [],
            })

    supported = [case for case in cases if case.expected_domain != TutorDomain.UNSUPPORTED]
    # Use repeated local retrievals for a stable latency sample without extra LLM calls.
    for _ in range(latency_runs):
        for case in supported:
            latencies.append(retriever.retrieve(
                case.query, top_k=config.top_k, domain=case.expected_domain
            ).latency_ms)
    p95 = statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 2 else (latencies[0] if latencies else 0)
    return VariantMetrics(
        name=config.name, case_count=len(cases),
        domain_accuracy=domain_correct / len(cases) if judge else None,
        route_accuracy=route_correct / len(cases),
        retrieval_hit_rate=retrieval_correct / retrieval_total if retrieval_total else 1.0,
        rag_coverage=rag_count / len(supported) if supported else 0.0,
        retrieval_p95_ms=p95, failures=failures,
    )


def promotion_decision(baseline: VariantMetrics, candidate: VariantMetrics,
                       max_quality_regression: float = 0.0, latency_budget_ms: float = 200.0) -> tuple[bool, list[str]]:
    reasons = []
    for metric in ("route_accuracy", "retrieval_hit_rate"):
        delta = getattr(candidate, metric) - getattr(baseline, metric)
        if delta < -max_quality_regression:
            reasons.append(f"{metric} regressed by {abs(delta):.3f}")
    if baseline.domain_accuracy is not None and candidate.domain_accuracy is not None:
        delta = candidate.domain_accuracy - baseline.domain_accuracy
        if delta < -max_quality_regression:
            reasons.append(f"domain_accuracy regressed by {abs(delta):.3f}")
    if candidate.retrieval_p95_ms > latency_budget_ms:
        reasons.append(f"retrieval p95 {candidate.retrieval_p95_ms:.2f}ms exceeds {latency_budget_ms:.2f}ms")
    return not reasons, reasons


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("evaluation/variants/baseline.json"))
    parser.add_argument("--candidate", type=Path, default=Path("evaluation/variants/candidate.example.json"))
    parser.add_argument("--cases", type=Path, default=Path("evaluation/ab_cases.json"))
    parser.add_argument("--live", action="store_true", help="Call Gemini judges for both variants")
    parser.add_argument("--max-quality-regression", type=float, default=0.0)
    parser.add_argument("--latency-budget-ms", type=float, default=200.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = [ABCase.model_validate(item) for item in load_json(args.cases)]
    baseline_config = VariantConfig.model_validate(load_json(args.baseline))
    candidate_config = VariantConfig.model_validate(load_json(args.candidate))
    api_key = os.environ.get("GEMINI_API_KEY") if args.live else None
    if args.live and not api_key:
        raise SystemExit("--live requires GEMINI_API_KEY")
    baseline = evaluate_variant(baseline_config, cases, api_key=api_key)
    candidate = evaluate_variant(candidate_config, cases, api_key=api_key)
    promote, reasons = promotion_decision(
        baseline, candidate, args.max_quality_regression, args.latency_budget_ms
    )
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if args.live else "offline",
        "baseline": baseline.model_dump(), "candidate": candidate.model_dump(),
        "deltas": {
            "route_accuracy": candidate.route_accuracy - baseline.route_accuracy,
            "retrieval_hit_rate": candidate.retrieval_hit_rate - baseline.retrieval_hit_rate,
            "retrieval_p95_ms": candidate.retrieval_p95_ms - baseline.retrieval_p95_ms,
        },
        "promote_candidate": promote, "reasons": reasons,
    }
    output = args.output or Path("evaluation/results") / f'ab-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report: {output}")
    if not promote:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
