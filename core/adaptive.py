"""Deterministic adaptive model selection for EAON.

The policy is deliberately provider-agnostic: it selects capability tiers,
not SDK clients. Execution adapters can map those tiers to concrete models.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TaskEnvelope:
    task: str
    complexity: float
    privacy_level: str = "cloud_ok"
    evidence_required: bool = False
    max_cost_usd: Optional[float] = None
    max_latency_s: Optional[float] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.complexity <= 1.0:
            raise ValueError("complexity must be between 0.0 and 1.0")
        if self.privacy_level not in {"local", "cloud_ok"}:
            raise ValueError("privacy_level must be 'local' or 'cloud_ok'")
        if self.max_cost_usd is not None and self.max_cost_usd < 0:
            raise ValueError("max_cost_usd must be non-negative")
        if self.max_latency_s is not None and self.max_latency_s < 0:
            raise ValueError("max_latency_s must be non-negative")


@dataclass(frozen=True)
class AdaptiveRoute:
    tier: str
    reason: str
    require_verification: bool = False


class AdaptiveModelPolicy:
    """Small, auditable baseline policy for adaptive intelligence routing."""

    def __init__(self, low_threshold: float = 0.35, high_threshold: float = 0.75):
        if not 0.0 <= low_threshold <= high_threshold <= 1.0:
            raise ValueError("thresholds must satisfy 0 <= low <= high <= 1")
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold

    def select(self, envelope: TaskEnvelope) -> AdaptiveRoute:
        if envelope.privacy_level == "local":
            return AdaptiveRoute("local", "privacy=local", envelope.evidence_required)

        if envelope.complexity < self.low_threshold:
            return AdaptiveRoute(
                "luna",
                f"complexity<{self.low_threshold:.2f}",
                envelope.evidence_required,
            )

        if envelope.complexity <= self.high_threshold:
            return AdaptiveRoute(
                "sol",
                f"{self.low_threshold:.2f}<=complexity<={self.high_threshold:.2f}",
                envelope.evidence_required,
            )

        return AdaptiveRoute(
            "sol",
            f"complexity>{self.high_threshold:.2f}",
            True,
        )
