from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class TutorDomain(str, Enum):
    MATH = "math"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    COMPUTER_SCIENCE = "computer_science"
    UNSUPPORTED = "unsupported"


class DomainDecision(BaseModel):
    supported: bool
    domain: TutorDomain
    reason: str = Field(min_length=1, max_length=240)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def consistent_support_flag(self):
        if self.supported == (self.domain == TutorDomain.UNSUPPORTED):
            raise ValueError("supported and domain are inconsistent")
        return self


class AnswerSource(str, Enum):
    KNOWLEDGE_BASE = "knowledge_base"
    WEB_FALLBACK = "web_fallback"
    SPECIALIST = "specialist"
    MODEL_FALLBACK = "model_fallback"
    BLENDED = "blended"
    REJECTED = "rejected"


class Citation(BaseModel):
    title: str = Field(min_length=1)
    url: HttpUrl | None = None
    purpose: Literal["evidence", "further_reading"] = "evidence"


class TutorAnswer(BaseModel):
    answer: str = Field(min_length=1)
    route: Literal[
        "rag", "math_agent", "physics_agent", "model_fallback", "learning_plan", "rejected"
    ]
    source: AnswerSource
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    retrieval_latency_ms: float = Field(ge=0.0)
    trace_id: str

    domain: TutorDomain
    routing_reason: str

    @model_validator(mode="after")
    def require_evidence_unless_rejected(self):
        if self.source != AnswerSource.REJECTED and not self.citations:
            raise ValueError("at least one citation is required")
        return self


class GroundedGeneration(BaseModel):
    """Schema enforced at the LLM boundary before API serialization."""

    answer: str = Field(min_length=1)
    cited_context_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class RetrievalHit(BaseModel):
    id: str
    topic: str
    question: str
    answer: str
    score: float = Field(ge=0.0)
    domain: TutorDomain


class KnowledgeDocument(BaseModel):
    id: str = Field(min_length=1)
    domain: TutorDomain
    topic: str = Field(min_length=1)
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"


class RetrievalResult(BaseModel):
    hits: list[RetrievalHit]
    latency_ms: float = Field(ge=0.0)
    confident: bool
