from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvidenceStance(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class EvidenceStatus(str, Enum):
    INSUFFICIENT = "insufficient"
    CONTESTED = "contested"
    SUPPORTED = "supported"


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    origin_id: str
    stance: EvidenceStance
    verified: bool

    def __post_init__(self):
        for name in ("evidence_id", "origin_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")

        if not isinstance(self.stance, EvidenceStance):
            raise ValueError("Invalid evidence stance")

        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    status: EvidenceStatus
    supporting_origins: tuple[str, ...]
    contradicting_origins: tuple[str, ...]
    missing_evidence_ids: tuple[str, ...]


def evaluate_evidence(
    evidence_refs: tuple[str, ...],
    records: tuple[EvidenceRecord, ...],
) -> EvidenceAssessment:
    if not isinstance(evidence_refs, tuple) or not all(
        isinstance(ref, str) and ref.strip() for ref in evidence_refs
    ):
        raise ValueError("evidence_refs must be a tuple of non-empty strings")

    if not isinstance(records, tuple) or not all(
        isinstance(record, EvidenceRecord) for record in records
    ):
        raise ValueError("records must be a tuple of EvidenceRecord")

    record_map = {}
    for record in records:
        if record.evidence_id in record_map:
            raise ValueError("Duplicate evidence_id")
        record_map[record.evidence_id] = record

    supporting = set()
    contradicting = set()
    missing = set()

    for ref in evidence_refs:
        record = record_map.get(ref)

        if record is None or not record.verified:
            missing.add(ref)
            continue

        if record.stance == EvidenceStance.SUPPORTS:
            supporting.add(record.origin_id)
        else:
            contradicting.add(record.origin_id)

    if contradicting:
        status = EvidenceStatus.CONTESTED
    elif supporting and not missing:
        status = EvidenceStatus.SUPPORTED
    else:
        status = EvidenceStatus.INSUFFICIENT

    return EvidenceAssessment(
        status=status,
        supporting_origins=tuple(sorted(supporting)),
        contradicting_origins=tuple(sorted(contradicting)),
        missing_evidence_ids=tuple(sorted(missing)),
    )
