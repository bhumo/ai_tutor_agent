from typing import Protocol

from langchain_google_genai import ChatGoogleGenerativeAI

from rag.config import DEFAULT_GEMINI_MODEL, get_gemini_client_options
from rag.schemas import GroundedGeneration


class AnswerGenerator(Protocol):
    def generate(self, query: str, contexts: list[dict[str, str]]) -> GroundedGeneration: ...
    def generate_from_model(self, query: str, domain: str, resources: list[dict[str, str]]) -> GroundedGeneration: ...
    def generate_learning_plan(self, query: str, questions: list[dict[str, str]]) -> GroundedGeneration: ...


class GeminiAnswerGenerator:
    """Gemini adapter whose output is parsed and validated by Pydantic."""

    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL):
        model_client = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            **get_gemini_client_options(),
        )
        self.structured_model = model_client.with_structured_output(GroundedGeneration)

    def generate(self, query: str, contexts: list[dict[str, str]]) -> GroundedGeneration:
        evidence = "\n\n".join(
            f'[{item["id"]}] {item["title"]}: {item["text"]}' for item in contexts
        )
        result = self.structured_model.invoke(
            "You are a careful tutor. Answer only from the evidence below. "
            "If it is incomplete, say so. Return only evidence IDs in cited_context_ids.\n\n"
            f"Question: {query}\n\nEvidence:\n{evidence}"
        )
        return GroundedGeneration.model_validate(result)

    def generate_from_model(self, query: str, domain: str, resources: list[dict[str, str]]) -> GroundedGeneration:
        reading = "\n".join(
            f'[{item["id"]}] {item["title"]}: {item["description"]}' for item in resources
        )
        result = self.structured_model.invoke(
            f"You are the {domain} tutor. The local knowledge base had no adequate answer. "
            "Answer using your general model knowledge, state uncertainty where appropriate, "
            "and select relevant IDs from the allow-listed further reading. Do not claim those "
            "resources were evidence for your answer.\n\n"
            f"Question: {query}\n\nFurther reading:\n{reading}"
        )
        return GroundedGeneration.model_validate(result)

    def generate_learning_plan(
        self, query: str, questions: list[dict[str, str]]
    ) -> GroundedGeneration:
        question_bank = "\n".join(
            f'[{item["id"]}] {item["question"]} — {item["answer"]}' for item in questions
        )
        result = self.structured_model.invoke(
            "Act as a patient tutor. Give a concise beginner learning plan using your general "
            "knowledge, then include a short practice section based on the supplied question bank. "
            "Do not reveal practice answers immediately. Cite the IDs of the practice questions you "
            "selected in cited_context_ids.\n\n"
            f"Student request: {query}\n\nBeginner question bank:\n{question_bank}"
        )
        return GroundedGeneration.model_validate(result)
