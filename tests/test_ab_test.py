import json

from evaluation.ab_test import ABCase, VariantConfig, evaluate_variant, promotion_decision


def load_cases():
    return [ABCase.model_validate(item) for item in json.loads(
        open("evaluation/ab_cases.json", encoding="utf-8").read()
    )]


def test_baseline_ab_metrics_meet_quality_and_latency_gates():
    metrics = evaluate_variant(
        VariantConfig(name="baseline", retrieval_threshold=0.032, top_k=3),
        load_cases(), latency_runs=2,
    )
    assert metrics.route_accuracy == 1.0
    assert metrics.retrieval_hit_rate == 1.0
    assert metrics.retrieval_p95_ms < 200


def test_promotion_gate_rejects_retrieval_regression():
    cases = load_cases()
    baseline = evaluate_variant(VariantConfig(name="a", retrieval_threshold=0.032), cases, latency_runs=1)
    candidate = evaluate_variant(VariantConfig(name="b", retrieval_threshold=1.0), cases, latency_runs=1)
    promote, reasons = promotion_decision(baseline, candidate)
    assert promote is False
    assert any("route_accuracy regressed" in reason for reason in reasons)
