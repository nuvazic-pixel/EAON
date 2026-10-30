from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .evidence import EvidenceAssessment, EvidenceStatus


class GateStatus(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class EvidenceProvenance:
    evidence_id: str
    source_uri: str
    verified_by: str
    verified_at: datetime
    method: str

    def __post_init__(self):
        for name in ("evidence_id", "source_uri", "verified_by", "method"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")

        if not isinstance(self.verified_at, datetime):
            raise ValueError("verified_at must be datetime")

        if self.verified_at.tzinfo is None or self.verified_at.utcoffset() is None:
            raise ValueError("verified_at must include timezone")


@dataclass(frozen=True, slots=True)
class EvidencePolicy:
    min_independent_origins: int = 2
    require_provenance: bool = True

    def __post_init__(self):
        if type(self.min_independent_origins) is not int:
            raise ValueError("min_independent_origins must be integer")
        if self.min_independent_origins < 1:
            raise ValueError("min_independent_origins must be positive")
        if type(self.require_provenance) is not bool:
            raise ValueError("require_provenance must be boolean")


@dataclass(frozen=True, slots=True)
class EvidenceGateResult:
    status: GateStatus
    reasons: tuple[str, ...]


def apply_evidence_gate(
    assessment: EvidenceAssessment,
    provenance: tuple[EvidenceProvenance, ...],
    policy: EvidencePolicy | None = None,
    *,
    required_evidence_ids: tuple[str, ...] = (),
) -> EvidenceGateResult:
    policy = policy if policy is not None else EvidencePolicy()

    if not isinstance(assessment, EvidenceAssessment):
        raise TypeError("Expected EvidenceAssessment")
    if not isinstance(policy, EvidencePolicy):
        raise TypeError("Expected EvidencePolicy")
    if not isinstance(provenance, tuple) or not all(
        isinstance(item, EvidenceProvenance) for item in provenance
    ):
        raise TypeError("Expected tuple of EvidenceProvenance")
    if not isinstance(required_evidence_ids, tuple) or not all(
        isinstance(item, str) and item.strip()
        for item in required_evidence_ids
    ):
        raise ValueError("Invalid required_evidence_ids")

    if assessment.status == EvidenceStatus.CONTESTED:
        return EvidenceGateResult(
            GateStatus.BLOCK,
            ("Contradictory verified evidence exists.",),
        )

    if assessment.status == EvidenceStatus.INSUFFICIENT:
        return EvidenceGateResult(
            GateStatus.BLOCK,
            ("Evidence is insufficient or missing.",),
        )

    reasons = []

    if len(assessment.supporting_origins) < policy.min_independent_origins:
        reasons.append("Not enough independent supporting origins.")

    if policy.require_provenance:
        ids = [item.evidence_id for item in provenance]

        if len(ids) != len(set(ids)):
            reasons.append("Duplicate provenance records.")

        missing = set(required_evidence_ids) - set(ids)

        if not required_evidence_ids:
            reasons.append("Required evidence IDs were not supplied.")
        elif missing:
            reasons.append("Missing provenance: " + ", ".join(sorted(missing)))

    if reasons:
        return EvidenceGateResult(GateStatus.REVIEW, tuple(reasons))

    return EvidenceGateResult(GateStatus.PASS, ())
