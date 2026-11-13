"""Explicit UI edits require evidence/revisions and never replace existing stores."""
import pytest

from core.project_context import ProjectContext
from core.project_files import ProjectFileError, create_backup, create_project_file
from eaon_kernel import ContinuityKernel
from ui.project_binding import (create_and_attach_project, memory_history, restore_and_attach_project,
                                revoke_saved_memory, save_memory)


class FakeOrchestrator:
    def __init__(self, **options):
        self.options = options


def state_for(path):
    return {"project_context": ProjectContext(path, "p"), "messages": [{"role": "assistant", "content": "old state"}],
            "draft": "old voice", "draft_stt_ms": 5, "last_recording": "old recording", "microphone_version": 0}


def test_create_and_attach_uses_new_project_and_clears_previous_inputs(tmp_path):
    state = {"messages": ["old"], "draft": "old voice"}
    path = create_and_attach_project(state, tmp_path / "new.db", "p", "New project", goal="Goal", first_task="Task",
                                    orchestrator_factory=FakeOrchestrator)
    assert state["project_context"].project_card()["title"] == "New project"
    assert state["messages"] == [] and state["draft"] == ""
    assert ContinuityKernel(path).recover("p")["next_task"]["text"] == "Task"


def test_failed_creation_keeps_current_binding_and_file(tmp_path):
    path = create_project_file(tmp_path / "kept.db", "p", "Keep")
    state = state_for(path)
    previous, before = dict(state), path.read_bytes()
    with pytest.raises(ProjectFileError, match="^project_file_exists$"):
        create_and_attach_project(state, path, "different", "Replacement", orchestrator_factory=FakeOrchestrator)
    assert state == previous and path.read_bytes() == before


def test_restore_attaches_new_copy_and_preserves_previous_store(tmp_path):
    path = create_project_file(tmp_path / "source.db", "p", "Original")
    state, original = state_for(path), path.read_bytes()
    copy = create_backup(path, tmp_path / "backups")
    restored = restore_and_attach_project(state, copy, tmp_path / "new-copy.db", "p", backup_dir=tmp_path / "backups",
                                          orchestrator_factory=FakeOrchestrator)
    assert state["project_context"].db == restored.resolve()
    assert state["messages"] == [] and path.read_bytes() == original


def test_memory_confirmation_requires_evidence_and_does_not_save_chat_implicitly(tmp_path):
    path = create_project_file(tmp_path / "source.db", "p", "Memory")
    state = state_for(path)
    before = ContinuityKernel(path).verify()
    with pytest.raises(ProjectFileError, match="^project_memory_invalid$"):
        save_memory(state, "decision", "Keep state local", status="confirmed")
    assert ContinuityKernel(path).verify() == before
    assert state["messages"]
    save_memory(state, "decision", "Keep state local", status="confirmed", source_text="Explicit decision evidence", source_uri="note://decision")
    record = memory_history(state)["decision"]
    assert record["status"] == "confirmed" and record["revision"] == 1
    assert record["sources"][0]["text"] == "Explicit decision evidence"
    assert state["messages"] == [] and state["draft"] == ""


def test_stale_update_and_revocation_fail_then_current_revision_is_revoked(tmp_path):
    path = create_project_file(tmp_path / "source.db", "p", "Memory")
    state = state_for(path)
    save_memory(state, "preference", "Concise", status="hypothesis")
    save_memory(state, "preference", "Detailed", expected_revision=1)
    before = ContinuityKernel(path).verify()
    with pytest.raises(ProjectFileError, match="^project_memory_conflict$"):
        save_memory(state, "preference", "Stale input", expected_revision=1)
    with pytest.raises(ProjectFileError, match="^project_memory_conflict$"):
        revoke_saved_memory(state, "preference", 1, "Stale revoke")
    assert ContinuityKernel(path).verify() == before
    revoke_saved_memory(state, "preference", 2, "Superseded explicitly")
    assert memory_history(state)["preference"]["lifecycle"] == "revoked"
    assert "preference" not in state["project_context"].project_card()["memories"]


@pytest.mark.parametrize("key", ["skill:unsafe", "procedure:unsafe", " Procedural :unsafe"])
def test_plain_memory_editor_cannot_create_procedural_cards(tmp_path, key):
    path = create_project_file(tmp_path / "source.db", "p", "Memory")
    state = state_for(path)
    before = ContinuityKernel(path).verify()
    with pytest.raises(ProjectFileError, match="^project_memory_procedural$"):
        save_memory(state, key, "Do something", status="confirmed", source_text="source", source_uri="note://source")
    assert ContinuityKernel(path).verify() == before


def test_existing_sources_are_preserved_on_explicit_update(tmp_path):
    path = create_project_file(tmp_path / "source.db", "p", "Memory")
    state = state_for(path)
    save_memory(state, "decision", "First", status="confirmed", source_text="first evidence", source_uri="note://first")
    save_memory(state, "decision", "Second", status="confirmed", source_text="second evidence", source_uri="note://second", expected_revision=1)
    record = memory_history(state)["decision"]
    assert len(record["sources"]) == 2
    assert {source["uri"] for source in record["sources"]} == {"note://first", "note://second"}
