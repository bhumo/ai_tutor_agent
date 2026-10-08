"""Stage-aware evaluation: routing, retrieval, then Ragas faithfulness."""

import os
import sys
import types

from langchain_google_genai import ChatGoogleGenerativeAI

# Ragas 0.4.3 still imports the removed community VertexAI adapter at module load,
# even when evaluation uses Gemini. Supply an inert import-only adapter so the
# optional evaluator can coexist with the maintained LangChain 1.x runtime.
_vertexai_module = "langchain_community.chat_models.vertexai"
if _vertexai_module not in sys.modules:
    compatibility_module = types.ModuleType(_vertexai_module)
    compatibility_module.ChatVertexAI = type("ChatVertexAI", (), {})
    sys.modules[_vertexai_module] = compatibility_module

from ragas import EvaluationDataset, evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness

from graph.workflow import TutorWorkflow
from rag.config import DEFAULT_GEMINI_MODEL, get_gemini_client_options
from rag.retriever import HybridRetriever
from rag.router import GeminiDomainJudge
from rag.schemas import TutorDomain


CASES = [
    ("What is Newton's second law?", TutorDomain.PHYSICS, "physics-force"),
    ("Explain what a derivative means.", TutorDomain.MATH, "math-derivative"),
    ("What is retrieval-augmented generation?", TutorDomain.COMPUTER_SCIENCE, "ai-rag"),
    ("What structures are found in a cell?", TutorDomain.BIOLOGY, "biology-cell"),
    ("How do I bake sourdough?", TutorDomain.UNSUPPORTED, None),
]


def main() -> None:
    api_key = os.environ["GEMINI_API_KEY"]
    judge = GeminiDomainJudge(api_key)
    retriever = HybridRetriever()
    workflow = TutorWorkflow(api_key=api_key, judge=judge, retriever=retriever)
    routing_correct = 0
    retrieval_correct = 0
    retrieval_total = 0
    faithfulness_samples = []

    for question, expected_domain, expected_document in CASES:
        decision = judge.classify(question)
        routing_correct += decision.domain == expected_domain
        if expected_document is None:
            continue
        retrieval_total += 1
        retrieval = retriever.retrieve(question, domain=expected_domain)
        retrieval_correct += bool(retrieval.hits and retrieval.hits[0].id == expected_document)
        answer = workflow.process(question)
        if answer.source.value != "knowledge_base":
            raise SystemExit(f"Expected grounded RAG answer for: {question}")
        faithfulness_samples.append({
            "user_input": question,
            "response": answer.answer,
            "retrieved_contexts": [hit.answer for hit in retrieval.hits],
        })

    routing_accuracy = routing_correct / len(CASES)
    retrieval_hit_rate = retrieval_correct / retrieval_total
    print(f"Routing accuracy: {routing_accuracy:.3f}")
    print(f"Retrieval hit@1: {retrieval_hit_rate:.3f}")
    if routing_accuracy < 0.90 or retrieval_hit_rate < 0.90:
        raise SystemExit("Routing or retrieval quality gate failed")

    evaluator = LangchainLLMWrapper(ChatGoogleGenerativeAI(
        model=DEFAULT_GEMINI_MODEL, google_api_key=api_key,
        **get_gemini_client_options(),
    ))
    result = evaluate(
        dataset=EvaluationDataset.from_list(faithfulness_samples),
        metrics=[Faithfulness(llm=evaluator)],
    )
    score = float(result.to_pandas()["faithfulness"].mean())
    print(f"Ragas faithfulness: {score:.3f}")
    if score < 0.80:
        raise SystemExit("Faithfulness gate failed: expected >= 0.80")


if __name__ == "__main__":
    main()
