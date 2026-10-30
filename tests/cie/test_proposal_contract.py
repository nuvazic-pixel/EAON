from dataclasses import asdict, fields
import pytest

from modules.cie.proposal import (
    Proposal, BlindProposal, ProposalProvenance,
    FORBIDDEN_BLIND_FIELDS, to_blind_proposal,
)


def sample(confidence=0.93):
    return Proposal(
        proposal_id="P-001",
        task_id="T-001",
        hypothesis="H1",
        reasoning="Evidence supports H1",
        confidence=confidence,
        evidence_refs=("E-001",),
        falsification_condition="Observation X",
    )


def test_blind_contract():
    blind = to_blind_proposal(sample())
    assert isinstance(blind, BlindProposal)
    assert {f.name for f in fields(blind)}.isdisjoint(
        FORBIDDEN_BLIND_FIELDS
    )
    assert set(asdict(blind)).isdisjoint(FORBIDDEN_BLIND_FIELDS)


def test_confidence_is_hidden():
    assert not hasattr(to_blind_proposal(sample()), "confidence")


def test_identity_is_separate():
    provenance = ProposalProvenance(
        "P-001", "agent-1", "model-1", "architecture"
    )
    blind = to_blind_proposal(sample())
    assert provenance.agent_id == "agent-1"
    assert not hasattr(blind, "agent_id")
    assert not hasattr(blind, "model_id")


@pytest.mark.parametrize(
    "value", [-0.1, 1.1, float("nan"), float("inf")]
)
def test_invalid_confidence(value):
    with pytest.raises(ValueError):
        sample(value)


def test_blind_is_immutable():
    blind = to_blind_proposal(sample())

    with pytest.raises((AttributeError, TypeError)):
        blind.agent_id = "leak"

    assert not hasattr(blind, "agent_id")

    with pytest.raises((AttributeError, TypeError)):
        blind.hypothesis = "Modified"

    assert blind.hypothesis == "H1"
