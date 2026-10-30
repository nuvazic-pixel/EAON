import pytest

from modules.cie.evidence import (
    EvidenceRecord,
    EvidenceStance,
    EvidenceStatus,
    evaluate_evidence,
)


def record(eid, origin, stance=EvidenceStance.SUPPORTS, verified=True):
    return EvidenceRecord(eid, origin, stance, verified)


def test_missing_evidence():
    result = evaluate_evidence(("E1",), ())
    assert result.status == EvidenceStatus.INSUFFICIENT
    assert result.missing_evidence_ids == ("E1",)


def test_verified_support():
    result = evaluate_evidence(("E1",), (record("E1", "O1"),))
    assert result.status == EvidenceStatus.SUPPORTED


def test_duplicate_origin_not_independent():
    result = evaluate_evidence(
        ("E1", "E2"),
        (record("E1", "O1"), record("E2", "O1")),
    )
    assert result.supporting_origins == ("O1",)


def test_independent_origins():
    result = evaluate_evidence(
        ("E1", "E2"),
        (record("E1", "O1"), record("E2", "O2")),
    )
    assert result.supporting_origins == ("O1", "O2")


def test_contradictory_evidence():
    result = evaluate_evidence(
        ("E1", "E2"),
        (
            record("E1", "O1"),
            record("E2", "O2", EvidenceStance.CONTRADICTS),
        ),
    )
    assert result.status == EvidenceStatus.CONTESTED


def test_unverified_evidence_not_counted():
    result = evaluate_evidence(
        ("E1",),
        (record("E1", "O1", verified=False),),
    )
    assert result.status == EvidenceStatus.INSUFFICIENT
    assert result.supporting_origins == ()


def test_duplicate_evidence_id_rejected():
    with pytest.raises(ValueError):
        evaluate_evidence(
            ("E1",),
            (record("E1", "O1"), record("E1", "O2")),
        )


def test_invalid_verified_value_rejected():
    with pytest.raises(ValueError):
        record("E1", "O1", verified=1)


def test_empty_evidence_is_insufficient():
    result = evaluate_evidence((), ())
    assert result.status == EvidenceStatus.INSUFFICIENT

def test_same_origin_with_opposing_evidence_is_contested():
    result = evaluate_evidence(
        ("E1", "E2"),
        (
            record("E1", "O1", EvidenceStance.SUPPORTS),
            record("E2", "O1", EvidenceStance.CONTRADICTS),
        ),
    )

    assert result.status == EvidenceStatus.CONTESTED
    assert result.supporting_origins == ("O1",)
    assert result.contradicting_origins == ("O1",)


def test_missing_evidence_prevents_supported_status():
    result = evaluate_evidence(
        ("E1", "E2"),
        (record("E1", "O1"),),
    )

    assert result.status == EvidenceStatus.INSUFFICIENT
    assert result.missing_evidence_ids == ("E2",)
