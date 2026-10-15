"""Trusted action registry and deterministic, fail-closed authorization.

This module does not execute actions or mint capabilities. The registry and policy
snapshot must be controlled by trusted application code, never by the planner.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class ActionSpec:
    action_id: str
    required_permissions: frozenset[str]
    blocked_by_rules: frozenset[str] = frozenset()
    required_facts: frozenset[str] = frozenset()
    forbidden_facts: frozenset[str] = frozenset()
    cost: int = 0
    fallback: bool = False


# Illustrative policy catalogue, owned by trusted code, not AI-generated plans.
ACTION_CATALOG = MappingProxyType({
    "cloud_export": ActionSpec(
        "cloud_export", frozenset({"cloud:export"}),
        blocked_by_rules=frozenset({"DATA_LOCAL_ONLY"}),
        required_facts=frozenset({"disk_failing"}), cost=1,
    ),
    "local_snapshot": ActionSpec(
        "local_snapshot", frozenset({"storage:local_backup"}),
        required_facts=frozenset({"disk_failing", "local_backup_available"}), cost=2,
    ),
    "diagnose_disk": ActionSpec(
        "diagnose_disk", frozenset({"storage:read"}),
        required_facts=frozenset({"disk_failing"}), cost=3,
    ),
    "continue_writes": ActionSpec(
        "continue_writes", frozenset({"storage:write"}),
        forbidden_facts=frozenset({"disk_failing"}), cost=0,
    ),
    "pause_writes": ActionSpec(
        "pause_writes", frozenset({"emergency:pause"}),
        required_facts=frozenset({"disk_failing"}), cost=5, fallback=True,
    ),
    "quarantine_disk": ActionSpec(
        "quarantine_disk", frozenset({"emergency:quarantine"}),
        required_facts=frozenset({"disk_failing"}), cost=6, fallback=True,
    ),
})


@dataclass(frozen=True, slots=True)
class PolicySnapshot:
    permissions: frozenset[str]
    protected_rules: frozenset[str]
    observed_facts: frozenset[str]

    def __post_init__(self) -> None:
        for key in ("permissions", "protected_rules", "observed_facts"):
            items = getattr(self, key)
            if not isinstance(items, frozenset) or not all(
                isinstance(item, str) and bool(item.strip()) for item in items
            ):
                raise ValueError(f"{key} must be frozenset of nonempty strings")


@dataclass(frozen=True, slots=True)
class Authorization:
    allowed: bool
    reasons: tuple[str, ...]


def authorize(action_id: str, policy: PolicySnapshot) -> Authorization:
    """Check a known action against trusted policy and observed state."""
    if not isinstance(policy, PolicySnapshot):
        raise TypeError("Expected PolicySnapshot")
    if not isinstance(action_id, str):
        return Authorization(False, ("Invalid action identifier",))

    spec = ACTION_CATALOG.get(action_id)
    if spec is None:
        return Authorization(False, ("Unknown action: default deny",))

    reasons: list[str] = []
    missing_permissions = spec.required_permissions - policy.permissions
    if missing_permissions:
        reasons.append("Missing permissions: " + ", ".join(sorted(missing_permissions)))

    violated = spec.blocked_by_rules & policy.protected_rules
    if violated:
        reasons.append("Protected policy: " + ", ".join(sorted(violated)))

    missing_facts = spec.required_facts - policy.observed_facts
    if missing_facts:
        reasons.append("Unverified preconditions: " + ", ".join(sorted(missing_facts)))

    forbidden = spec.forbidden_facts & policy.observed_facts
    if forbidden:
        reasons.append("Unsafe state: " + ", ".join(sorted(forbidden)))

    return Authorization(not reasons, tuple(reasons))
