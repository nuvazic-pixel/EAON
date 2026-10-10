from __future__ import annotations

from dataclasses import dataclass, fields
from math import isfinite

FORBIDDEN_BLIND_FIELDS = frozenset({
    "agent_id", "model_id", "domain",
    "trust_score", "confidence",
    "evidence_quality", "collective_score",
})


@dataclass(frozen=True, slots=True)
class Proposal:
    proposal_id: str
    task_id: str
    hypothesis: str
    reasoning: str
    confidence: float
    evidence_refs: tuple[str, ...]
    falsification_condition: str

    def __post_init__(self):
        for name in ("proposal_id", "task_id", "hypothesis"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")

        if type(self.confidence) not in (float, int):
            raise ValueError("confidence must be numeric")
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be finite and within [0,1]")

        for name in ("reasoning", "falsification_condition"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be text")

        if not isinstance(self.evidence_refs, tuple) or not all(
            isinstance(ref, str) for ref in self.evidence_refs
        ):
            raise ValueError("evidence_refs must be a tuple of strings")


@dataclass(frozen=True, slots=True)
class ProposalProvenance:
    proposal_id: str
    agent_id: str
    model_id: str
    domain: str


@dataclass(frozen=True, slots=True)
class BlindProposal:
    proposal_id: str
    hypothesis: str
    reasoning: str
    evidence_refs: tuple[str, ...]
    falsification_condition: str


def to_blind_proposal(proposal: Proposal) -> BlindProposal:
    blind = BlindProposal(
        proposal_id=proposal.proposal_id,
        hypothesis=proposal.hypothesis,
        reasoning=proposal.reasoning,
        evidence_refs=proposal.evidence_refs,
        falsification_condition=proposal.falsification_condition,
    )
    leaked = {f.name for f in fields(blind)} & FORBIDDEN_BLIND_FIELDS
    if leaked:
        raise RuntimeError(f"Forbidden blind fields: {sorted(leaked)}")
    return blind
