"""ENCR resolver: a proposal is never an authorization.

The AI planner supplies only action IDs; it cannot alter the policy snapshot,
registry, evidence gate or fallback priority. Results are decisions, not effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from modules.cie.evidence_gate import EvidenceGateResult, GateStatus
from .fallback_controller import choose_fallback
from .policy_kernel import ACTION_CATALOG, PolicySnapshot, authorize


class Outcome(str, Enum):
    PERMIT = "permit"
    SAFE_FALLBACK = "safe_fallback"
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class RejectedAction:
    action_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConflictDecision:
    outcome: Outcome
    selected_action: str | None
    evidence_status: GateStatus
    rejected_actions: tuple[RejectedAction, ...]
    reason: str
    human_review_required: bool


def resolve_conflict(
    proposals: tuple[str, ...],
    evidence: EvidenceGateResult,
    policy: PolicySnapshot,
) -> ConflictDecision:
    if not isinstance(proposals, tuple) or not all(
        isinstance(item, str) for item in proposals
    ):
        raise TypeError("Proposals must be a tuple of action IDs")
    if not isinstance(evidence, EvidenceGateResult):
        raise TypeError("Expected EvidenceGateResult")
    if not isinstance(policy, PolicySnapshot):
        raise TypeError("Expected trusted PolicySnapshot")

    rejected: list[RejectedAction] = []
    permitted: list[str] = []
    if evidence.status == GateStatus.PASS:
        for action_id in dict.fromkeys(proposals):
            auth = authorize(action_id, policy)
            spec = ACTION_CATALOG.get(action_id)
            if auth.allowed and spec is not None and not spec.fallback:
                permitted.append(action_id)
            else:
                reasons = auth.reasons or ("Fallback cannot be selected by planner",)
                rejected.append(RejectedAction(action_id, reasons))
    else:
        rejected = [
            RejectedAction(a, ("Evidence gate did not PASS",))
            for a in dict.fromkeys(proposals)
        ]

    if permitted:
        chosen = min(permitted, key=lambda a: (ACTION_CATALOG[a].cost, a))
        return ConflictDecision(
            Outcome.PERMIT, chosen, evidence.status, tuple(rejected),
            "Authorized proposal; decision only, no execution", False,
        )

    fallback = choose_fallback(policy)
    if fallback is not None:
        return ConflictDecision(
            Outcome.SAFE_FALLBACK, fallback, evidence.status, tuple(rejected),
            "No admissible proposal; preauthorized fallback (decision only)", True,
        )

    return ConflictDecision(
        Outcome.ESCALATE, None, evidence.status, tuple(rejected),
        "No admissible proposal or preauthorized fallback", True,
    )
