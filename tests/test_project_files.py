"""Project-file operations preserve originals and restore only verified snapshots."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import sqlite3
from types import SimpleNamespace

import pytest

from core import project_files
from core.project_files import (ProjectFileError, create_backup, create_project_file,
                                list_backups, receipt_path, restore_backup)
from eaon_kernel import ContinuityKernel


@pytest.fixture
def project(tmp_path):
    path = create_project_file(tmp_path / "source.db", "p", "File fixture", goal="Keep state", first_task="Check backup")
    kernel = ContinuityKernel(path)
    kernel.record_memory("p", "latency", "Not measured", status="unknown")
    return kernel


def test_new_project_has_goal_and_first_task_and_refuses_existing_data(project):
    before = project.path.read_bytes()
    card = project.recover("p")
    assert card["title"] == "File fixture" and card["active_goal"]["text"] == "Keep state"
    assert card["next_task"]["text"] == "Check backup"
    with pytest.raises(ProjectFileError, match="^project_file_exists$"):
        create_project_file(project.path, "other", "Other")
    assert project.path.read_bytes() == before


@pytest.mark.parametrize("options", [{"title": ""}, {"first_task": "A task without a goal"}, {"max_tasks": True}])
def test_invalid_new_project_never_becomes_visible(tmp_path, options):
    target = tmp_path / "not-created.db"
    args = {"title": "Valid", **options}
    with pytest.raises(ProjectFileError, match="^project_create_invalid$"):
        create_project_file(target, "p", **args)
    assert not target.exists()


def test_backup_and_receipt_match_a_verified_snapshot_without_source_writes(project, tmp_path):
    before_bytes, before_head = project.path.read_bytes(), project.verify()
    copy = create_backup(project.path, tmp_path / "backups")
    receipt = json.loads(receipt_path(copy).read_text())
    assert receipt["sha256"] == sha256(copy.read_bytes()).hexdigest()
    assert receipt["bytes"] == copy.stat().st_size
    assert ContinuityKernel(copy).verify() == before_head
    assert receipt["journal_head"] == before_head["head"]
    assert project.path.read_bytes() == before_bytes
    assert list_backups(tmp_path / "backups") == [copy]


def test_backup_captures_committed_state_not_an_uncommitted_writer(project, tmp_path):
    before = project.verify()
    writer = sqlite3.connect(project.path)
    try:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE events SET payload='uncommitted-bad-data' WHERE seq=1")
        copy = create_backup(project.path, tmp_path / "backups")
        assert ContinuityKernel(copy).verify() == before
    finally:
        writer.rollback()
        writer.close()
    assert project.verify() == before


def test_restore_uses_a_new_target_and_retains_source_and_copy(project, tmp_path):
    copy = create_backup(project.path, tmp_path / "backups")
    before_copy, before_source = copy.read_bytes(), project.path.read_bytes()
    target = restore_backup(copy, tmp_path / "restored.db", backup_dir=tmp_path / "backups")
    assert ContinuityKernel(target).recover("p") == project.recover("p")
    assert copy.read_bytes() == before_copy and project.path.read_bytes() == before_source
    with pytest.raises(ProjectFileError, match="^restore_target_exists$"):
        restore_backup(copy, project.path)
    assert project.path.read_bytes() == before_source


def test_modified_copy_is_rejected_before_restored_file_is_published(project, tmp_path):
    copy = create_backup(project.path, tmp_path / "backups")
    with copy.open("ab") as stream:
        stream.write(b"tampered")
    target = tmp_path / "restored.db"
    with pytest.raises(ProjectFileError, match="^backup_digest_mismatch$"):
        restore_backup(copy, target)
    assert not target.exists()


def test_receipt_head_is_checked_after_digest(project, tmp_path):
    copy = create_backup(project.path, tmp_path / "backups")
    receipt = json.loads(receipt_path(copy).read_text())
    receipt["journal_head"] = "wrong-external-head"
    receipt_path(copy).write_text(json.dumps(receipt))
    target = tmp_path / "restored.db"
    with pytest.raises(ProjectFileError, match="^backup_integrity_failed$"):
        restore_backup(copy, target)
    assert not target.exists()


def test_missing_receipt_and_wrong_selected_folder_are_rejected(project, tmp_path):
    copy = create_backup(project.path, tmp_path / "backups")
    with pytest.raises(ProjectFileError, match="^backup_invalid_receipt$"):
        restore_backup(copy, tmp_path / "restored.db", backup_dir=tmp_path / "unselected")
    receipt_path(copy).unlink()
    with pytest.raises(ProjectFileError, match="^backup_invalid_receipt$"):
        restore_backup(copy, tmp_path / "restored.db")
    assert not (tmp_path / "restored.db").exists()


def test_backup_listing_is_one_explicit_folder_and_named_receipts_only(project, tmp_path):
    folder = tmp_path / "backups"
    copy = create_backup(project.path, folder)
    (folder / "other.db").write_text("not a selected backup")
    (folder / "private.json").write_text("not a selected receipt")
    create_backup(project.path, folder / "nested")
    assert list_backups(folder) == [copy]


def test_backup_name_collision_preserves_the_original_receipt(project, tmp_path, monkeypatch):
    fixed = datetime(2026, 11, 13, tzinfo=timezone.utc)
    monkeypatch.setattr(project_files, "datetime", SimpleNamespace(now=lambda zone: fixed, fromisoformat=datetime.fromisoformat))
    monkeypatch.setattr(project_files, "uuid4", lambda: SimpleNamespace(hex="1" * 32))
    copy = create_backup(project.path, tmp_path / "backups")
    original = receipt_path(copy).read_bytes()
    with pytest.raises(ProjectFileError):
        create_backup(project.path, tmp_path / "backups")
    assert receipt_path(copy).read_bytes() == original
    assert ContinuityKernel(copy).verify() == project.verify()


def test_invalid_source_is_not_offered_as_a_backup(tmp_path):
    source = tmp_path / "not-a-kernel.db"
    source.write_text("private invalid input")
    with pytest.raises(ProjectFileError):
        create_backup(source, tmp_path / "backups")
    assert source.read_text() == "private invalid input"
    assert list_backups(tmp_path / "backups") == []
