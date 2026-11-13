"""Create project files and copy verified SQLite snapshots without replacing data."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
from uuid import uuid4

from eaon_kernel import ContinuityKernel, IntegrityError, ValidationError
from eaon_kernel.contracts import text


class ProjectFileError(RuntimeError):
    """Stable UI error code without paths or source contents."""


def _path(value):
    try:
        if not str(value).strip():
            raise ValueError
        return Path(value).expanduser().absolute()
    except (TypeError, ValueError, OSError):
        raise ProjectFileError("project_file_invalid_path") from None


def _stage(target):
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".eaon-stage-", suffix=".db", dir=target.parent)
    os.close(handle)
    return Path(name)


def _publish(staged, target, exists_code):
    """Same-directory hard link publishes a verified file exclusively on all OSes."""
    try:
        os.link(staged, target)
    except FileExistsError:
        raise ProjectFileError(exists_code) from None


def _digest(path):
    result = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def create_project_file(path, project_id, title, *, owner_id="local", goal="", first_task="", max_tasks=8):
    """Build a new verified store off-path, then publish without overwriting."""
    target = _path(path)
    try:
        text(project_id, "project_id", 200)
        text(title, "title", 1000)
        text(owner_id, "owner_id", 200)
        if type(max_tasks) is not int or not 1 <= max_tasks <= 100:
            raise ValueError
        if type(goal) is not str or type(first_task) is not str:
            raise ValueError
        if goal:
            text(goal, "goal")
        if first_task:
            text(first_task, "first task")
            if not goal:
                raise ValueError
    except (ValidationError, ValueError, TypeError):
        raise ProjectFileError("project_create_invalid") from None
    if os.path.lexists(target):
        raise ProjectFileError("project_file_exists")
    staged, stage_dir, created = None, None, False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        stage_dir = Path(tempfile.mkdtemp(prefix=".eaon-new-", dir=target.parent))
        staged = stage_dir / "store.db"
        kernel = ContinuityKernel.create(staged)
        created = True
        kernel.create_project(project_id, title, owner_id=owner_id, max_tasks=max_tasks)
        if goal:
            kernel.set_goal(project_id, "initial-goal", goal)
        if first_task:
            kernel.add_task(project_id, "initial-task", first_task)
        kernel.verify()
        _publish(staged, target, "project_file_exists")
        return target
    except ProjectFileError:
        raise
    except (OSError, IntegrityError, ValidationError, sqlite3.DatabaseError):
        raise ProjectFileError("project_create_failed") from None
    finally:
        if staged is not None and created:
            staged.unlink(missing_ok=True)
        if stage_dir is not None:
            try:
                stage_dir.rmdir()
            except OSError:
                pass


def receipt_path(path):
    return Path(path).with_suffix(".receipt.json")


def create_backup(source, backup_dir):
    """SQLite backup API captures committed state; no source store is written."""
    source = _path(source).resolve()
    destination = _path(backup_dir)
    if not source.is_file():
        raise ProjectFileError("backup_invalid_source")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = destination / f"eaon-backup-{stamp}-{uuid4().hex[:12]}.db"
    staged, published, receipt_created = None, False, False
    try:
        staged = _stage(target)
        expires = time.monotonic() + 15
        def progress(_status, _remaining, _total):
            if time.monotonic() > expires:
                raise ProjectFileError("backup_busy")
        reader = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=10)
        writer = None
        try:
            writer = sqlite3.connect(staged)
            reader.backup(writer, pages=128, progress=progress, sleep=0.01)
            writer.execute("PRAGMA journal_mode=DELETE")
        finally:
            if writer is not None:
                writer.close()
            reader.close()
        verified = ContinuityKernel(staged).verify()
        receipt = {"schema": "eaon.project-backup.v1", "file": target.name,
                   "sha256": _digest(staged), "bytes": staged.stat().st_size,
                   "journal_head": verified["head"], "event_count": verified["event_count"],
                   "created_at": datetime.now(timezone.utc).isoformat(), "source_name": source.name}
        # An orphan receipt after interruption is excluded by list_backups.
        with receipt_path(target).open("x", encoding="utf-8") as stream:
            receipt_created = True
            json.dump(receipt, stream, sort_keys=True, indent=2)
            stream.write("\n")
        _publish(staged, target, "backup_target_exists")
        published = True
        return target
    except ProjectFileError:
        raise
    except IntegrityError:
        raise ProjectFileError("backup_integrity_failed") from None
    except (OSError, ValueError, sqlite3.DatabaseError):
        raise ProjectFileError("backup_failed") from None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
        if not published and receipt_created:
            receipt_path(target).unlink(missing_ok=True)


def _receipt(backup):
    sidecar = receipt_path(backup)
    try:
        if backup.is_symlink() or sidecar.is_symlink() or not backup.is_file():
            raise ValueError
        if sidecar.stat().st_size > 8192:
            raise ValueError
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        if (type(data) is not dict or set(data) != {"schema", "file", "sha256", "bytes", "journal_head", "event_count", "created_at", "source_name"}
                or data["schema"] != "eaon.project-backup.v1" or data["file"] != backup.name
                or type(data["sha256"]) is not str or re.fullmatch("[0-9a-f]{64}", data["sha256"]) is None
                or type(data["bytes"]) is not int or data["bytes"] < 1
                or type(data["event_count"]) is not int or data["event_count"] < 0
                or type(data["journal_head"]) is not str or not data["journal_head"]
                or type(data["source_name"]) is not str
                or datetime.fromisoformat(data["created_at"]).tzinfo is None):
            raise ValueError
        return data
    except (OSError, ValueError, TypeError, KeyError):
        raise ProjectFileError("backup_invalid_receipt") from None


def list_backups(backup_dir, limit=20):
    """Inspect only named receipts in this explicit directory, never recursively."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ProjectFileError("backup_invalid_receipt")
    folder = _path(backup_dir)
    if not folder.is_dir():
        return []
    copies = []
    try:
        for sidecar in sorted(folder.glob("eaon-backup-*.receipt.json"), reverse=True):
            backup = sidecar.with_suffix("").with_suffix(".db")
            try:
                _receipt(backup)
            except ProjectFileError:
                continue
            copies.append(backup)
            if len(copies) == limit:
                break
        return copies
    except OSError:
        raise ProjectFileError("backup_failed") from None


def restore_backup(backup, target, *, backup_dir=None):
    """Restore into a new path after digest, chain and head verification."""
    backup, target = _path(backup), _path(target)
    if backup_dir is not None and backup.parent.resolve() != _path(backup_dir).resolve():
        raise ProjectFileError("backup_invalid_receipt")
    if os.path.lexists(target):
        raise ProjectFileError("restore_target_exists")
    receipt = _receipt(backup)
    staged = None
    try:
        staged = _stage(target)
        # Verify the exact bytes restored, not an earlier separate read of the source.
        with backup.open("rb") as reader, staged.open("wb") as writer:
            for block in iter(lambda: reader.read(1024 * 1024), b""):
                writer.write(block)
            writer.flush()
            os.fsync(writer.fileno())
        if staged.stat().st_size != receipt["bytes"] or _digest(staged) != receipt["sha256"]:
            raise ProjectFileError("backup_digest_mismatch")
        verified = ContinuityKernel(staged).verify(expected_head=receipt["journal_head"])
        if verified["event_count"] != receipt["event_count"]:
            raise ProjectFileError("backup_integrity_failed")
        _publish(staged, target, "restore_target_exists")
        return target
    except ProjectFileError:
        raise
    except IntegrityError:
        raise ProjectFileError("backup_integrity_failed") from None
    except (OSError, ValueError, sqlite3.DatabaseError):
        raise ProjectFileError("restore_failed") from None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
