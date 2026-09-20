from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field


Decision = Literal["answer", "abstain"]
Category = Literal[
    "insufficient_information",
    "contradiction_detection",
    "rule_shift",
    "error_repair",
]


class ModelAnswer(BaseModel):
    decision: Decision
    answer: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


@dataclass(slots=True)
class BenchmarkCase:
    case_id: str
    category: Category
    prompt: str
    expected_decision: Decision
    accepted_answers: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AdapterResponse:
    text: str
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CaseResult:
    case: BenchmarkCase
    parsed_answer: ModelAnswer | None
    raw_response: str
    parse_ok: bool
    correct: bool
    confidence_score: float
    abstention_true_positive: bool
    abstention_false_positive: bool
    abstention_false_negative: bool
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case.case_id,
            "category": self.case.category,
            "expected_decision": self.case.expected_decision,
            "accepted_answers": list(self.case.accepted_answers),
            "model_answer": self.parsed_answer.model_dump() if self.parsed_answer else None,
            "raw_response": self.raw_response,
            "parse_ok": self.parse_ok,
            "correct": self.correct,
            "confidence_score": round(self.confidence_score, 6),
            "latency_ms": round(self.latency_ms, 3),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "error": self.error,
            "metadata": self.case.metadata,
        }
