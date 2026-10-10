from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .proposal import BlindProposal


class CritiqueCategory(str, Enum):
    LOGIC = "logic"
    CONTRADICTION = "contradiction"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FALSIFIABILITY = "falsifiability"
    ASSUMPTION = "assumption"


@dataclass(frozen=True, slots=True)
class CritiqueFinding:
    category: CritiqueCategory
    explanation: str
    suggested_revision: str

    def __post_init__(self):
        if not isinstance(self.category, CritiqueCategory):
            raise ValueError("Invalid critique category")

        if not isinstance(self.explanation, str) or not self.explanation.strip():
            raise ValueError("Explanation is required")

        if not isinstance(self.suggested_revision, str):
            raise ValueError("Suggested revision must be text")


@dataclass(frozen=True, slots=True)
class BlindCritique:
    proposal_id: str
    findings: tuple[CritiqueFinding, ...]
    summary: str

    def __post_init__(self):
        if not isinstance(self.proposal_id, str) or not self.proposal_id.strip():
            raise ValueError("Proposal ID is required")

        if not isinstance(self.findings, tuple) or not all(
            isinstance(item, CritiqueFinding) for item in self.findings
        ):
            raise ValueError("Findings must be a tuple of CritiqueFinding")

        if not isinstance(self.summary, str):
            raise ValueError("Summary must be text")


def validate_critique(
    proposal: BlindProposal,
    critique: BlindCritique,
) -> None:
    if not isinstance(proposal, BlindProposal):
        raise TypeError("Expected BlindProposal")

    if not isinstance(critique, BlindCritique):
        raise TypeError("Expected BlindCritique")

    if proposal.proposal_id != critique.proposal_id:
        raise ValueError("Critique references a different proposal")
