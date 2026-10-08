# Evaluation Flow

Evaluate each pipeline boundary separately:

1. **Routing accuracy** compares the Pydantic LLM judge's domain with labeled cases, including unsupported requests.
2. **Retrieval hit@1** checks category-scoped retrieval against the expected document ID.
3. **Deterministic hallucination gate** checks every stored Q&A under four conversational
   phrasings, requires the same record at rank 1, requires verbatim stored-answer integrity,
   rejects unknown evidence IDs, and tests unsupported distractors across every domain.
4. **Ragas faithfulness** evaluates only knowledge-base answers against their retrieved contexts.

Do not run faithfulness on `model_fallback` answers: they intentionally use model knowledge, and their links are further reading rather than evidence. A production iteration should add labeled references and Ragas factual correctness for that route.

Run the credentialed gates with `python -m evaluation.run_ragas`. Unit tests remain deterministic and credential-free.

Run the full offline hallucination gate with:

```bash
python -m evaluation.hallucination
```

## Paired A/B Gate

Copy `evaluation/variants/candidate.example.json`, change the candidate settings, and run:

```bash
python -m evaluation.ab_test \
  --baseline evaluation/variants/baseline.json \
  --candidate evaluation/variants/candidate.example.json
```

Offline mode uses labeled domains as an oracle and makes no LLM calls. Add `--live` to compare the configured Gemini judge models; this requires `GEMINI_API_KEY`. Reports are written under `evaluation/results/`, and the process exits with status 1 when route accuracy or retrieval hit rate regresses, or candidate retrieval p95 exceeds 200 ms.

This harness is a pre-release paired evaluation. It does not split production users or establish statistical significance.
