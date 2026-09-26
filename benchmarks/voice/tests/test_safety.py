import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eaon_c3.journal import StateJournal, verify
from eaon_c3.safety import (
    DryRunSession, EmergencyStop, InterlockError, MockToolExecutor, VoiceToolAttempt,
)


class TestNetworkBoundary:
    def __init__(self, blocked=True):
        self.blocked = blocked

    def verify_isolated(self):
        return self.blocked


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "journal.jsonl"
        self.executor = MockToolExecutor()
        self.stop = EmergencyStop()
        self.network = TestNetworkBoundary()
        self.journal = StateJournal(self.path)

    def session(self, **overrides):
        config = dict(
            dry_run=True, executor=self.executor, real_tool_registry=None,
            network_boundary=self.network, journal=self.journal,
            emergency_stop=self.stop, authorized_model_id="local-llama3",
            allowed_model_ids=frozenset({"local-llama3"}),
            tool_validators={"light": lambda args: args == {"level": 1}},
        )
        config.update(overrides)
        return DryRunSession(**config)

    def attempt(self, **overrides):
        data = dict(requested_tool="light", arguments={"level": 1},
                    model_id="local-llama3", wake_valid=True, source="human",
                    intent_confidence=0.9, raw_model_output='{"tool":"light"}',
                    shadow_recommendation="another-model")
        data.update(overrides)
        return VoiceToolAttempt(**data)

    def test_preflight_rejects_each_injected_fault_before_any_mock_call(self):
        class RealExecutor:
            calls = 0

            def execute(self, tool):
                self.calls += 1
                raise AssertionError("must never be reached")

        real = RealExecutor()
        faults = (
            (dict(dry_run=False), "dry_run_required"),
            (dict(executor=real), "mock_executor_required"),
            (dict(real_tool_registry=object()), "real_registry_must_be_disconnected"),
            (dict(network_boundary=TestNetworkBoundary(False)), "outbound_network_not_blocked"),
            (dict(authorized_model_id="unknown"), "unknown_authorized_model_id"),
        )
        for overrides, reason in faults:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(InterlockError, reason):
                    self.session(**overrides).start()
        self.stop.trip()
        with self.assertRaisesRegex(InterlockError, "emergency_stop_disarmed"):
            self.session().start()
        self.assertEqual(self.executor.calls, 0)
        self.assertEqual(real.calls, 0)

    def test_journal_must_accept_preflight_write(self):
        with patch.object(self.journal, "append", side_effect=OSError("read only")):
            with self.assertRaisesRegex(InterlockError, "journal_write_failed"):
                self.session().start()
        self.assertFalse(self.stop.armed)
        self.assertEqual(self.executor.calls, 0)

    def test_authorized_path_is_simulated_with_parent_linked_redacted_trajectory(self):
        session = self.session()
        session.start()
        result = session.attempt(self.attempt())
        self.assertEqual(result["status"], "SIMULATED")
        self.assertFalse(result["real_world_effect"])
        self.assertEqual(self.executor.calls, 1)
        self.assertEqual(verify(self.path), (True, 8, None))
        records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        events = [record["payload"] for record in records]
        self.assertEqual([event["event"] for event in events], [
            "preflight", "wake", "raw_model_output", "parsed_call", "policy_decision",
            "simulated_call", "tool_result", "postcondition",
        ])
        self.assertEqual({event["session_id"] for event in events}, {session.session_id})
        self.assertEqual({event["turn_id"] for event in events[1:]}, {events[1]["turn_id"]})
        for parent, child in zip(events[1:-1], events[2:]):
            self.assertEqual(child["parent_span_id"], parent["span_id"])
        self.assertEqual(events[3]["shadow_recommendation"], "another-model")
        self.assertEqual(events[-1]["valid"], True)
        content = self.path.read_text(encoding="utf-8")
        self.assertNotIn('{"tool":"light"}', content)
        self.assertNotIn('"level": 1', content)

    def test_missing_wake_echo_unknown_model_confidence_and_arguments_are_blocked(self):
        session = self.session()
        session.start()
        cases = (
            (dict(wake_valid=False), "wake_not_authorized"),
            (dict(source="tts"), "source_not_verified_human"),
            (dict(source="unknown"), "source_not_verified_human"),
            (dict(model_id=None), "model_id_not_authorized"),
            (dict(model_id="other"), "model_id_not_authorized"),
            (dict(intent_confidence=0.1), "intent_not_confident"),
            (dict(arguments={"level": 3}), "arguments_invalid"),
            (dict(arguments={"level": object()}), "arguments_not_serializable"),
            (dict(requested_tool="physical_device"), "capability_not_allowed"),
        )
        for overrides, reason in cases:
            with self.subTest(reason=reason):
                result = session.attempt(self.attempt(**overrides))
                self.assertEqual(result["status"], "blocked_dry_run")
                self.assertEqual(result["reason"], reason)
        self.assertEqual(session.blocked_actions, len(cases))
        self.assertEqual(self.executor.calls, 0)
        events = [json.loads(line)["payload"]["event"]
                  for line in self.path.read_text(encoding="utf-8").splitlines()]
        self.assertNotIn("simulated_call", events)

    def test_capability_policy_is_snapshotted_at_session_creation(self):
        validators = {"light": lambda args: args == {"level": 1}}
        session = self.session(tool_validators=validators)
        session.start()
        validators["physical_device"] = lambda args: True
        result = session.attempt(self.attempt(requested_tool="physical_device"))
        self.assertEqual(result["reason"], "capability_not_allowed")
        self.assertEqual(self.executor.calls, 0)

    def test_stop_or_network_change_after_start_refuses_to_continue(self):
        for change, reason in (("stop", "emergency_stop_disarmed"),
                               ("network", "outbound_network_not_blocked")):
            with self.subTest(change=change):
                self.stop = EmergencyStop()
                self.network = TestNetworkBoundary()
                session = self.session()
                session.start()
                if change == "stop":
                    self.stop.trip()
                else:
                    self.network.blocked = False
                with self.assertRaisesRegex(InterlockError, reason):
                    session.attempt(self.attempt())
        self.assertEqual(self.executor.calls, 0)

    def test_stop_between_policy_and_mock_never_reaches_executor(self):
        session = self.session()
        session.start()
        append = self.journal.append

        def trip_when_ready(event_type, entity, payload):
            record = append(event_type, entity, payload)
            if payload["event"] == "simulated_call":
                self.stop.trip()
            return record

        with patch.object(self.journal, "append", side_effect=trip_when_ready):
            with self.assertRaisesRegex(InterlockError, "emergency_stop_disarmed"):
                session.attempt(self.attempt())
        self.assertEqual(self.executor.calls, 0)

    def test_tampered_or_missing_journal_refuses_subsequent_attempt(self):
        session = self.session()
        session.start()
        original = self.path.read_text(encoding="utf-8")
        self.path.write_text(original.replace('"PASS"', '"FAIL"'), encoding="utf-8")
        with self.assertRaisesRegex(InterlockError, "journal_integrity_error"):
            session.attempt(self.attempt())
        self.path.unlink()
        with self.assertRaisesRegex(InterlockError, "journal_missing_after_start"):
            session.attempt(self.attempt())
        self.assertEqual(self.executor.calls, 0)

    def test_valid_but_truncated_chain_is_detected_against_session_head(self):
        session = self.session()
        session.start()
        session.attempt(self.attempt(wake_valid=False))
        first_record = self.path.read_text(encoding="utf-8").splitlines()[0]
        self.path.write_text(first_record + "\n", encoding="utf-8")
        self.assertTrue(verify(self.path)[0])  # The local chain alone cannot spot truncation.
        with self.assertRaisesRegex(InterlockError, "journal_integrity_error"):
            session.attempt(self.attempt())
        self.assertEqual(self.executor.calls, 0)

    def test_bad_mock_postcondition_trips_stop(self):
        session = self.session()
        session.start()
        bad_result = {"status": "SIMULATED", "validated": True,
                      "real_world_effect": True}
        with patch.object(self.executor, "execute", return_value=bad_result):
            with self.assertRaisesRegex(InterlockError, "mock_postcondition_failed"):
                session.attempt(self.attempt())
        self.assertFalse(self.stop.armed)
        self.assertTrue(verify(self.path)[0])

    def test_malformed_journal_line_returns_invalid_instead_of_crashing(self):
        self.path.write_text("[]\n", encoding="utf-8")
        self.assertEqual(verify(self.path), (False, 1, "malformed record"))
        with self.assertRaisesRegex(InterlockError, "journal_integrity_error"):
            self.session().start()

    def test_journal_failure_during_attempt_trips_stop(self):
        session = self.session()
        session.start()
        with patch.object(self.journal, "append", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(InterlockError, "journal_write_failed"):
                session.attempt(self.attempt())
        self.assertFalse(self.stop.armed)
        self.assertEqual(self.executor.calls, 0)


if __name__ == "__main__":
    unittest.main()
