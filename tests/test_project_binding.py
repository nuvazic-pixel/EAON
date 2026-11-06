"""Project switching must not carry prior chat or voice data across bindings."""
import os
import unittest
from unittest.mock import patch

from core.project_context import ProjectContextError
from ui.project_binding import attach_project, detach_project, reset_conversation


class FakeContext:
    def __init__(self, db, project_id, **options):
        self.project_id = project_id
        self.options = options

    def project_card(self):
        return {"project_id": self.project_id}


class FakeOrchestrator:
    def __init__(self, **options):
        self.options = options


class ProjectBindingTests(unittest.TestCase):
    def state(self):
        return {"messages": [{"role": "assistant", "content": "old project secret"}],
                "draft": "old microphone draft", "last_recording": "old recording",
                "draft_stt_ms": 12, "microphone_version": 4,
                "project_context": object(), "orchestrator": object()}

    def assert_chat_cleared(self, state, version):
        self.assertEqual(state["messages"], [])
        self.assertEqual(state["draft"], "")
        self.assertIsNone(state["last_recording"])
        self.assertIsNone(state["draft_stt_ms"])
        self.assertEqual(state["microphone_version"], version)

    def test_switch_selects_new_local_project_and_clears_prior_chat_and_audio(self):
        state = self.state()
        previous = state["project_context"]
        attach_project(state, "fixture.db", "new-project", context_factory=FakeContext,
                       orchestrator_factory=FakeOrchestrator)
        self.assertIsNot(state["project_context"], previous)
        self.assertEqual(state["project_context"].project_id, "new-project")
        self.assertEqual(state["orchestrator"].options,
                         {"local_only": True, "context_session": state["project_context"]})
        self.assert_chat_cleared(state, 5)

    def test_failed_validation_keeps_existing_project_and_all_pending_input(self):
        class BrokenContext(FakeContext):
            def project_card(self):
                raise ProjectContextError("context_integrity_failed")
        state = self.state()
        previous = dict(state)
        with self.assertRaisesRegex(ProjectContextError, "context_integrity_failed"):
            attach_project(state, "fixture.db", "broken", context_factory=BrokenContext,
                           orchestrator_factory=FakeOrchestrator)
        self.assertEqual(state, previous)

    def test_failed_orchestrator_creation_keeps_current_session(self):
        def broken_orchestrator(**options):
            raise ValueError("private configuration detail")
        state = self.state()
        previous = dict(state)
        with self.assertRaisesRegex(ProjectContextError, "^context_invalid_configuration$"):
            attach_project(state, "fixture.db", "new-project", context_factory=FakeContext,
                           orchestrator_factory=broken_orchestrator)
        self.assertEqual(state, previous)

    def test_clear_conversation_retains_attached_project_and_orchestrator(self):
        state = self.state()
        context, orchestrator = state["project_context"], state["orchestrator"]
        reset_conversation(state)
        self.assertIs(state["project_context"], context)
        self.assertIs(state["orchestrator"], orchestrator)
        self.assert_chat_cleared(state, 5)

    def test_detach_creates_unbound_local_conversation_and_clears_private_input(self):
        state = self.state()
        detach_project(state, orchestrator_factory=FakeOrchestrator)
        self.assertIsNone(state["project_context"])
        self.assertEqual(state["orchestrator"].options, {"local_only": True})
        self.assert_chat_cleared(state, 5)

    def test_synapse_configuration_does_not_copy_token_into_ui_settings(self):
        state = self.state()
        with patch.dict(os.environ, {"SYNAPSE_TOKEN": "private-token-sentinel"}):
            attach_project(state, "fixture.db", "new-project", synapse_url="http://127.0.0.1:8000",
                           collection_id="owned-collection", context_factory=FakeContext,
                           orchestrator_factory=FakeOrchestrator)
        self.assertEqual(state["project_context"].options,
                         {"synapse_url": "http://127.0.0.1:8000", "collection_id": "owned-collection"})
        self.assertNotIn("private-token-sentinel", repr(state))
        self.assertFalse(any("token" in key.lower() for key in state))


if __name__ == "__main__":
    unittest.main()
