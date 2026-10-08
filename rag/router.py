from typing import Protocol

from langchain_google_genai import ChatGoogleGenerativeAI

from rag.config import DEFAULT_GEMINI_MODEL, get_gemini_client_options
from rag.schemas import DomainDecision


class DomainJudge(Protocol):
    def classify(self, query: str) -> DomainDecision: ...


class GeminiDomainJudge:
    """Semantic scope and routing judge, independent from retrieval."""

    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL):
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            **get_gemini_client_options(),
        )
        self.structured_model = llm.with_structured_output(DomainDecision)

    def classify(self, query: str) -> DomainDecision:
        prompt = f"""Classify this tutoring request semantically.
Supported domains are math, physics, chemistry, biology, and computer_science.
Select unsupported for history, politics, entertainment, cooking, travel, medical advice,
or anything outside those five educational domains. A word overlap is not evidence of domain.
Return a short reason and calibrated confidence. Do not answer the question.

Request: {query}"""
        return DomainDecision.model_validate(self.structured_model.invoke(prompt))
