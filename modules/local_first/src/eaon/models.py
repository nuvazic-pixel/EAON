from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Claim:
    text: str
    source_id: str
    evidence: str
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RouteDecision:
    backend: str
    reason: str
    private: bool = True


@dataclass(slots=True)
class RealityCheck:
    verdict: str
    score: float
    warnings: list[str] = field(default_factory=list)
    supporting_claim_ids: list[int] = field(default_factory=list)
    contradicting_claim_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RunResult:
    goal: str
    answer: str
    route: RouteDecision
    reality_check: RealityCheck
    evidence: list[Claim]
    run_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "answer": self.answer,
            "route": asdict(self.route),
            "reality_check": self.reality_check.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "run_id": self.run_id,
        }
