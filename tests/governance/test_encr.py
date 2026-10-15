"""Deterministic stress tests for proposer/guardian separation."""

import unittest

from modules.cie.evidence_gate import EvidenceGateResult, GateStatus
from modules.governance.policy_kernel import PolicySnapshot, authorize
from modules.governance.normative_conflict import Outcome, resolve_conflict


def policy(*permissions, facts=("disk_failing",), rules=("DATA_LOCAL_ONLY",)):
    return PolicySnapshot(frozenset(permissions), frozenset(rules), frozenset(facts))


def evidence(status=GateStatus.PASS):
    return EvidenceGateResult(status, ())


class ENCRTests(unittest.TestCase):
    def test_known_permitted_action(self):
        p = policy("storage:local_backup", facts=("disk_failing", "local_backup_available"))
        d = resolve_conflict(("local_snapshot",), evidence(), p)
        self.assertEqual((d.outcome, d.selected_action), (Outcome.PERMIT, "local_snapshot"))
        self.assertFalse(d.human_review_required)

    def test_level_3_empirical_truth_cannot_override_normative_policy(self):
        p = policy("cloud:export", "emergency:pause")
        d = resolve_conflict(("cloud_export",), evidence(GateStatus.PASS), p)
        self.assertEqual(d.outcome, Outcome.SAFE_FALLBACK)
        self.assertEqual(d.selected_action, "pause_writes")
        self.assertIn("Protected policy", d.rejected_actions[0].reasons[0])

    def test_cloud_without_permission_still_denied(self):
        p = policy("emergency:pause", rules=())
        d = resolve_conflict(("cloud_export",), evidence(), p)
        self.assertEqual(d.selected_action, "pause_writes")

    def test_unknown_or_imaginary_override_denied(self):
        p = policy("cloud:export", "emergency:pause")
        d = resolve_conflict(("override_policy_then_cloud_export",), evidence(), p)
        self.assertEqual(d.outcome, Outcome.SAFE_FALLBACK)
        self.assertIn("Unknown action", d.rejected_actions[0].reasons[0])

    def test_evidence_review_never_authorizes_plan(self):
        p = policy("storage:local_backup", "emergency:pause", facts=("disk_failing", "local_backup_available"))
        d = resolve_conflict(("local_snapshot",), evidence(GateStatus.REVIEW), p)
        self.assertEqual(d.outcome, Outcome.SAFE_FALLBACK)
        self.assertEqual(d.selected_action, "pause_writes")

    def test_contested_evidence_never_authorizes_plan(self):
        p = policy("storage:local_backup", "emergency:pause", facts=("disk_failing", "local_backup_available"))
        d = resolve_conflict(("local_snapshot",), evidence(GateStatus.BLOCK), p)
        self.assertEqual(d.outcome, Outcome.SAFE_FALLBACK)

    def test_rejected_plan_with_no_fallback_escalates(self):
        p = policy("cloud:export")
        d = resolve_conflict(("cloud_export",), evidence(), p)
        self.assertEqual((d.outcome, d.selected_action), (Outcome.ESCALATE, None))
        self.assertTrue(d.human_review_required)

    def test_lack_of_observation_fails_closed(self):
        p = policy("storage:local_backup", "emergency:pause", facts=())
        d = resolve_conflict(("local_snapshot",), evidence(), p)
        self.assertEqual(d.outcome, Outcome.ESCALATE)

    def test_unsafe_write_is_denied_even_if_permitted_by_role(self):
        p = policy("storage:write", "emergency:pause")
        d = resolve_conflict(("continue_writes",), evidence(), p)
        self.assertEqual(d.outcome, Outcome.SAFE_FALLBACK)
        self.assertIn("Unsafe state", d.rejected_actions[0].reasons[0])

    def test_planner_cannot_directly_choose_fallback(self):
        p = policy("emergency:pause")
        d = resolve_conflict(("pause_writes",), evidence(), p)
        self.assertEqual(d.outcome, Outcome.SAFE_FALLBACK)
        self.assertIn("cannot be selected", d.rejected_actions[0].reasons[0])

    def test_cheapest_trusted_action_selected(self):
        p = policy("storage:local_backup", "storage:read", "emergency:pause", facts=("disk_failing", "local_backup_available"))
        d = resolve_conflict(("diagnose_disk", "local_snapshot"), evidence(), p)
        self.assertEqual(d.selected_action, "local_snapshot")

    def test_cloud_rejected_but_valid_local_choice_selected(self):
        p = policy("cloud:export", "storage:local_backup", facts=("disk_failing", "local_backup_available"))
        d = resolve_conflict(("cloud_export", "local_snapshot"), evidence(), p)
        self.assertEqual(d.outcome, Outcome.PERMIT)
        self.assertEqual(d.selected_action, "local_snapshot")
        self.assertEqual(d.rejected_actions[0].action_id, "cloud_export")

    def test_unknown_action_default_deny(self):
        self.assertFalse(authorize("invented_operation", policy()).allowed)

    def test_untrusted_policy_is_invalid(self):
        with self.assertRaises(ValueError):
            PolicySnapshot({"cloud:export"}, frozenset(), frozenset())

    def test_no_execution_side_effect_or_mutation(self):
        p = policy("cloud:export", "emergency:pause")
        before = (p.permissions, p.protected_rules, p.observed_facts)
        for _ in range(20):
            d = resolve_conflict(("cloud_export",), evidence(), p)
            self.assertNotEqual(d.selected_action, "cloud_export")
        self.assertEqual(before, (p.permissions, p.protected_rules, p.observed_facts))


if __name__ == "__main__":
    unittest.main()
