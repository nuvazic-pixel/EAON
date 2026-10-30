from datetime import datetime, timezone

from modules.cie.evidence import EvidenceAssessment, EvidenceStatus
from modules.cie.evidence_gate import (
    EvidenceGateResult,
    EvidencePolicy,
    EvidenceProvenance,
    GateStatus,
    apply_evidence_gate,
)


def assessment(status=EvidenceStatus.SUPPORTED, origins=("O1", "O2")):
    return EvidenceAssessment(
        status=status,
        supporting_origins=origins,
        contradicting_origins=(),
        missing_evidence_ids=(),
    )


def provenance(eid):
    return EvidenceProvenance(
        evidence_id=eid,
        source_uri="https://example.org/source/" + eid,
        verified_by="local-reviewer",
        verified_at=datetime(2026, 10, 11, tzinfo=timezone.utc),
        method="manual-review",
    )


def test_gate_pass():
    result = apply_evidence_gate(
        assessment(),
        (provenance("E1"), provenance("E2")),
        required_evidence_ids=("E1", "E2"),
    )
    assert result.status == GateStatus.PASS


def test_gate_blocks_conflict():
    result = apply_evidence_gate(
        assessment(EvidenceStatus.CONTESTED),
        (),
    )
    assert result.status == GateStatus.BLOCK


def test_gate_blocks_insufficient():
    result = apply_evidence_gate(
        assessment(EvidenceStatus.INSUFFICIENT),
        (),
    )
    assert result.status == GateStatus.BLOCK


def test_gate_reviews_single_origin():
    result = apply_evidence_gate(
        assessment(origins=("O1",)),
        (provenance("E1"),),
        required_evidence_ids=("E1",),
    )
    assert result.status == GateStatus.REVIEW


def test_gate_reviews_missing_provenance():
    result = apply_evidence_gate(
        assessment(),
        (provenance("E1"),),
        required_evidence_ids=("E1", "E2"),
    )
    assert result.status == GateStatus.REVIEW


def test_gate_reviews_unspecified_evidence_ids():
    result = apply_evidence_gate(assessment(), ())
    assert result.status == GateStatus.REVIEW


def test_gate_reviews_duplicate_provenance():
    result = apply_evidence_gate(
        assessment(),
        (provenance("E1"), provenance("E1")),
        required_evidence_ids=("E1",),
    )
    assert result.status == GateStatus.REVIEW


def test_policy_rejects_invalid_threshold():
    import pytest
    with pytest.raises(ValueError):
        EvidencePolicy(min_independent_origins=0)


def test_provenance_rejects_naive_timestamp():
    import pytest
    with pytest.raises(ValueError):
        EvidenceProvenance(
            "E1", "https://example.org", "reviewer",
            datetime(2026, 10, 11), "manual",
        )
