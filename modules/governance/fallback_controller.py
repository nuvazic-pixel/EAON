"""Preauthorized, deterministic fallbacks. No device operations are performed."""

from __future__ import annotations

from .policy_kernel import ACTION_CATALOG, PolicySnapshot, authorize

FALLBACK_PRIORITY = ("pause_writes", "quarantine_disk")


def choose_fallback(policy: PolicySnapshot) -> str | None:
    for action_id in FALLBACK_PRIORITY:
        # The trusted registry decides which actions really are fallbacks.
        if ACTION_CATALOG[action_id].fallback and authorize(action_id, policy).allowed:
            return action_id
    return None
