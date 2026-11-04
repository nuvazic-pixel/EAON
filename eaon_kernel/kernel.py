"""Transactional, replay-verified project continuity. No model or tool executor."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from .contracts import ConflictError, IntegrityError, SourceRef, ValidationError, text


POLICY = {"version": "eaon.continuity.v1", "confirmed_requires_sources": True,
          "single_active_goal": True, "max_pending_tasks": 100,
          "owner_scope": "project", "source_digest": "captured_text_sha256",
          "memory_states": ["confirmed", "hypothesis", "unknown"]}


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


POLICY_HASH = sha256(canonical(POLICY).encode()).hexdigest()


def event_hash(seq: int, kind: str, payload: str, previous: str) -> str:
    return sha256(canonical([seq, kind, payload, previous]).encode("utf-8")).hexdigest()


def _fields(data: dict, expected: set[str]) -> None:
    if type(data) is not dict or set(data) != expected:
        raise ValidationError("Unexpected event fields")


def _id(value, label="identifier") -> str:
    return text(value, label, 200)


def _apply(state: dict, kind: str, data: dict) -> None:
    if type(data) is not dict:
        raise ValidationError("Event data must be an object")
    project_id = _id(data.get("project_id"), "project_id")
    if kind == "project.created":
        _fields(data, {"project_id", "title", "max_tasks", "owner_id"})
        text(data["title"], "title", 1000)
        _id(data["owner_id"], "owner_id")
        if type(data["max_tasks"]) is not int or not 1 <= data["max_tasks"] <= 100:
            raise ValidationError("max_tasks must be an integer between 1 and 100")
        if project_id in state:
            raise ConflictError("Project already exists")
        state[project_id] = {**data, "active_goal": None, "goal_history": [], "tasks": [], "memories": {}}
        return
    if project_id not in state:
        raise ValidationError("Unknown project")
    project = state[project_id]
    if kind == "goal.started":
        _fields(data, {"project_id", "goal_id", "text"})
        goal_id = _id(data["goal_id"], "goal_id")
        text(data["text"], "goal text")
        if project["active_goal"] is not None:
            raise ConflictError("Close the active goal before starting another")
        if any(goal["id"] == goal_id for goal in project["goal_history"]):
            raise ConflictError("Goal identifier was already used")
        project["active_goal"] = {"id": goal_id, "text": data["text"]}
        project["goal_history"].append({**project["active_goal"], "status": "active"})
    elif kind == "goal.closed":
        _fields(data, {"project_id"})
        if project["active_goal"] is None:
            raise ConflictError("No active goal")
        if any(task["status"] == "pending" for task in project["tasks"]):
            raise ConflictError("Complete pending tasks before closing the goal")
        project["goal_history"][-1]["status"] = "closed"
        project["active_goal"] = None
    elif kind == "task.added":
        _fields(data, {"project_id", "task_id", "text"})
        _id(data["task_id"], "task_id")
        text(data["text"], "task text")
        if project["active_goal"] is None:
            raise ConflictError("A task requires an active goal")
        if any(task["id"] == data["task_id"] for task in project["tasks"]):
            raise ConflictError("Task identifier was already used")
        if sum(task["status"] == "pending" for task in project["tasks"]) >= project["max_tasks"]:
            raise ConflictError("Pending task budget exhausted")
        project["tasks"].append({"id": data["task_id"], "text": data["text"],
                                 "goal_id": project["active_goal"]["id"], "status": "pending"})
    elif kind == "task.completed":
        _fields(data, {"project_id", "task_id"})
        task = next((item for item in project["tasks"] if item["id"] == data["task_id"]), None)
        if task is None or task["status"] != "pending":
            raise ConflictError("Task is absent or already completed")
        task["status"] = "completed"
    elif kind == "memory.recorded":
        _fields(data, {"project_id", "key", "text", "status", "sources", "expected_revision"})
        key = _id(data["key"], "memory key")
        text(data["text"], "memory text")
        if type(data["status"]) is not str or data["status"] not in POLICY["memory_states"]:
            raise ValidationError("Unknown memory status")
        if type(data["sources"]) is not list:
            raise ValidationError("Sources must be an array")
        for source in data["sources"]:
            _fields(source, {"source_id", "uri", "text", "sha256"})
            SourceRef(**source)
        if data["status"] == "confirmed" and not data["sources"]:
            raise ValidationError("Confirmed memory requires captured source evidence")
        expected = data["expected_revision"]
        if expected is not None and (type(expected) is not int or expected < 1):
            raise ValidationError("expected_revision must be a positive integer")
        prior = project["memories"].get(key)
        if (prior and expected != prior["revision"]) or (not prior and expected is not None):
            raise ConflictError("Memory changed or exists; provide its current expected_revision explicitly")
        project["memories"][key] = {"text": data["text"], "status": data["status"],
                                    "sources": deepcopy(data["sources"]),
                                    "lifecycle": "active",
                                    "revision": prior["revision"] + 1 if prior else 1}
    elif kind == "memory.revoked":
        _fields(data, {"project_id", "key", "expected_revision", "reason"})
        text(data["reason"], "revocation reason")
        prior = project["memories"].get(data["key"])
        if prior is None or type(data["expected_revision"]) is not int or prior["revision"] != data["expected_revision"]:
            raise ConflictError("Revocation requires the current memory revision")
        if prior["lifecycle"] == "revoked":
            raise ConflictError("Memory is already revoked")
        prior.update(lifecycle="revoked", revision=prior["revision"] + 1, revocation_reason=data["reason"])
    elif kind == "checkpoint":
        _fields(data, {"project_id", "state_hash"})
        digest = sha256(canonical(project).encode("utf-8")).hexdigest()
        if data["state_hash"] != digest:
            raise ValidationError("Checkpoint state hash mismatch")
    else:
        raise ValidationError("Unknown event type")


class ContinuityKernel:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise IntegrityError("Kernel database is missing; initialize a new store explicitly")

    @classmethod
    def create(cls, path: str | Path) -> "ContinuityKernel":
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb"):
                pass
        except FileExistsError as exc:
            raise ConflictError("Refusing to overwrite an existing kernel database") from exc
        db = sqlite3.connect(path)
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL)")
            db.executemany("INSERT INTO meta VALUES (?, ?)", [("schema_version", "0.1"), ("event_count", "0"), ("head_hash", "GENESIS")])
            db.commit()
        finally:
            db.close()
        return cls(path)

    @contextmanager
    def _transaction(self, write=False):
        connection = None
        try:
            uri = self.path.as_uri() + ("?mode=rw" if write else "?mode=ro")
            connection = sqlite3.connect(uri, uri=True, timeout=10, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            state, meta = self._replay(connection)
            yield connection, state, meta
            connection.commit()
        except (sqlite3.DatabaseError, OSError) as exc:
            raise IntegrityError("Kernel database is unavailable or invalid") from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _replay(db):
        state, previous, count = {}, "GENESIS", 0
        try:
            meta = dict(db.execute("SELECT key, value FROM meta").fetchall())
            if set(meta) != {"schema_version", "event_count", "head_hash"} or meta["schema_version"] != "0.1":
                raise IntegrityError("Unsupported or incomplete kernel metadata")
            for row in db.execute("SELECT seq,kind,payload,previous_hash,hash FROM events ORDER BY seq"):
                count += 1
                if row["seq"] != count or row["previous_hash"] != previous:
                    raise IntegrityError("Journal sequence or previous hash mismatch")
                if row["hash"] != event_hash(count, row["kind"], row["payload"], previous):
                    raise IntegrityError("Journal event digest mismatch")
                payload = json.loads(row["payload"])
                _fields(payload, {"schema", "timestamp", "policy_version", "policy_sha256", "data"})
                if canonical(payload) != row["payload"] or payload["schema"] != "eaon.kernel.event.v1":
                    raise IntegrityError("Invalid event serialization")
                stamp = datetime.fromisoformat(payload["timestamp"])
                if stamp.tzinfo is None or payload["policy_version"] != POLICY["version"] or payload["policy_sha256"] != POLICY_HASH:
                    raise IntegrityError("Event time or policy binding is invalid")
                _apply(state, row["kind"], payload["data"])
                previous = row["hash"]
            if meta["event_count"] != str(count) or meta["head_hash"] != previous:
                raise IntegrityError("Journal was truncated or metadata does not match its head")
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            raise IntegrityError("Journal has malformed data or an invalid state transition") from exc
        return state, meta

    def _append(self, kind: str, data: dict) -> dict:
        with self._transaction(write=True) as (db, state, meta):
            _apply(state, kind, data)
            seq = int(meta["event_count"]) + 1
            payload = canonical({"schema": "eaon.kernel.event.v1", "timestamp": datetime.now(timezone.utc).isoformat(),
                                 "policy_version": POLICY["version"], "policy_sha256": POLICY_HASH, "data": data})
            digest = event_hash(seq, kind, payload, meta["head_hash"])
            db.execute("INSERT INTO events VALUES (?,?,?,?,?)", (seq, kind, payload, meta["head_hash"], digest))
            db.execute("UPDATE meta SET value=? WHERE key='event_count'", (str(seq),))
            db.execute("UPDATE meta SET value=? WHERE key='head_hash'", (digest,))
            return {"project_id": data["project_id"], "head": digest, "event_count": seq}

    def create_project(self, project_id, title, max_tasks=8, owner_id="local"):
        return self._append("project.created", {"project_id": project_id, "title": title, "max_tasks": max_tasks, "owner_id": owner_id})

    def set_goal(self, project_id, goal_id, text):
        return self._append("goal.started", {"project_id": project_id, "goal_id": goal_id, "text": text})

    def close_goal(self, project_id):
        return self._append("goal.closed", {"project_id": project_id})

    def add_task(self, project_id, task_id, text):
        return self._append("task.added", {"project_id": project_id, "task_id": task_id, "text": text})

    def complete_task(self, project_id, task_id):
        return self._append("task.completed", {"project_id": project_id, "task_id": task_id})

    def record_memory(self, project_id, key, text, status="hypothesis", sources=(), expected_revision=None):
        if type(sources) is not tuple or any(not isinstance(item, SourceRef) for item in sources):
            raise ValidationError("sources must be a tuple of SourceRef")
        return self._append("memory.recorded", {"project_id": project_id, "key": key, "text": text,
                           "status": status, "sources": [item.to_dict() for item in sources], "expected_revision": expected_revision})

    def recover(self, project_id):
        with self._transaction() as (_, state, meta):
            if project_id not in state:
                raise ValidationError("Unknown project")
            project = deepcopy(state[project_id])
            project["next_task"] = next((item for item in project["tasks"] if item["status"] == "pending"), None)
            return {**project, "journal_head": meta["head_hash"], "event_count": int(meta["event_count"])}

    def revoke_memory(self, project_id, key, expected_revision, reason):
        return self._append("memory.revoked", {"project_id": project_id, "key": key,
                            "expected_revision": expected_revision, "reason": reason})

    def context_card(self, project_id):
        """Reasoning view excludes revoked records; recover remains an inspector."""
        card = self.recover(project_id)
        card["memories"] = {key: value for key, value in card["memories"].items() if value["lifecycle"] == "active"}
        return card

    def checkpoint(self, project_id):
        # State may change between these transactions: the append's replay then
        # rejects the stale checkpoint rather than recording an inconsistent one.
        with self._transaction() as (_, state, __):
            if project_id not in state:
                raise ValidationError("Unknown project")
            digest = sha256(canonical(state[project_id]).encode("utf-8")).hexdigest()
        return {**self._append("checkpoint", {"project_id": project_id, "state_hash": digest}), "state_hash": digest}

    def verify(self, expected_head=None):
        with self._transaction() as (_, __, meta):
            if expected_head is not None and expected_head != meta["head_hash"]:
                raise IntegrityError("Journal head differs from the externally supplied expected head")
            return {"ok": True, "head": meta["head_hash"], "event_count": int(meta["event_count"]), "policy_version": POLICY["version"]}
