import pytest

from modules.cie.proposal import Proposal, to_blind_proposal
from modules.cie.critique import (
    BlindCritique,
    CritiqueCategory,
    CritiqueFinding,
    validate_critique,
)


def sample_proposal():
    return to_blind_proposal(
        Proposal(
            proposal_id="P-001",
            task_id="T-001",
            hypothesis="H1",
            reasoning="Because X",
            confidence=0.8,
            evidence_refs=("E-001",),
            falsification_condition="Observation Y",
        )
    )


def test_valid_critique():
    proposal = sample_proposal()

    critique = BlindCritique(
        proposal_id="P-001",
        findings=(
            CritiqueFinding(
                category=CritiqueCategory.INSUFFICIENT_EVIDENCE,
                explanation="One source does not establish the claim.",
                suggested_revision="Add independent evidence.",
            ),
        ),
        summary="Evidence needs strengthening.",
    )

    validate_critique(proposal, critique)


def test_mismatched_proposal_rejected():
    critique = BlindCritique(
        proposal_id="P-999",
        findings=(),
        summary="",
    )

    with pytest.raises(ValueError):
        validate_critique(sample_proposal(), critique)


def test_empty_explanation_rejected():
    with pytest.raises(ValueError):
        CritiqueFinding(
            category=CritiqueCategory.LOGIC,
            explanation=" ",
            suggested_revision="Clarify the reasoning.",
        )


def test_invalid_category_rejected():
    with pytest.raises(ValueError):
        CritiqueFinding(
            category="trust_score",
            explanation="Invalid category",
            suggested_revision="",
        )


def test_proposal_identity_not_required():
    proposal = sample_proposal()

    assert not hasattr(proposal, "agent_id")
    assert not hasattr(proposal, "model_id")
    assert not hasattr(proposal, "confidence")


def test_wrong_proposal_type_rejected():
    critique = BlindCritique(
        proposal_id="P-001",
        findings=(),
        summary="",
    )

    with pytest.raises(TypeError):
        validate_critique("P-001", critique)
