# Senior AI Engineering Review

## Executive Assessment

This repository is a credible educational prototype for semantic routing, domain-scoped hybrid retrieval, structured generation, tracing, and staged evaluation. It is not yet production-ready. The ten-document corpus and synchronous single-process architecture are intentionally small; reported sub-200 ms retrieval applies only to local retrieval, not end-to-end requests.

## Scope and Agent Harness

The LangGraph harness has a useful separation of concerns: semantic scope judge, five domain paths, grounded generation, model fallback, and rejection. Pydantic validates routing and answer boundaries, and protocols allow fake judges/generators in tests.

Important gaps:

- Domain nodes currently call the same implementation; they are labels, not independently tooled specialists.
- There is no durable conversation/checkpoint state, retry policy, timeout budget, cancellation, or circuit breaker.
- Legacy agents and tools remain alongside the new harness, increasing ambiguity and dependency risk.
- Prompt versions are embedded in code rather than versioned or managed as deployable artifacts.

## Scalability and Reliability

The in-memory corpus is appropriate for ten topics. It performs an O(n) scan and uses hand-authored concept vectors, so it should not be presented as scalable semantic search. For growth, use an ingestion pipeline, real embeddings, a vector index plus BM25 service, document/version metadata, and reranking.

FastAPI handlers call synchronous LLM and HTTP code from async routes, which can block workers. Move model and search calls to async clients, add request timeouts and concurrency limits, and initialize dependencies through an application factory rather than at import time. Replace JSONL audit files with structured centralized logs; local disk is ephemeral on many deployments. Raw queries also require retention, redaction, and access policies.

## Evaluation Strategy

The staged design is correct:

- labeled domain accuracy for the judge;
- route accuracy and retrieval hit@k for orchestration/retrieval;
- Ragas faithfulness only for context-grounded answers;
- factual correctness and answer relevance for model fallbacks.

The current set is too small for release confidence. Expand it with paraphrases, ambiguous cross-domain requests, prompt injection, unsafe requests, multi-turn references, calculation/tool cases, empty evidence, malformed model output, and provider failures. Use human-reviewed references and an evaluator model different from the generation model to reduce correlated bias.

## Observability

Langfuse spans and trace scores cover routing, domain execution, retrieval, and generation. Add model name, prompt version, token usage, cost, end-to-end latency, retry count, retrieval IDs/scores, fallback reason, and deployment version. The application trace ID should be explicitly correlated with the Langfuse trace. Silent tracing failures protect availability but need a local metric or alert.

## Release and A/B Testing

`evaluation/ab_test.py` runs paired baseline/candidate comparisons over the same labeled cases. Offline mode tests retrieval without API cost; `--live` compares LLM judges. It writes JSON reports and blocks promotion on route/retrieval regression or p95 budget failure.

This is an offline quality gate, not an online experiment system. Production A/B testing additionally needs stable user assignment, exposure logging, sample-size planning, guardrail metrics, and rollback controls.

## Recommended Roadmap

1. Remove or migrate legacy agent paths; add an application factory and async model adapters.
2. Grow and version the labeled evaluation set before expanding the corpus.
3. Add real embeddings, reranking, and a persistent hybrid index when corpus size justifies them.
4. Add fallback factual-correctness evaluation, safety checks, and adversarial tests.
5. Correlate Langfuse traces with request IDs and capture cost/token/service-level metrics.
6. Only then add online experimentation and production traffic splitting.
