from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
EVENT_TYPES = {"Transition", "Observation", "Relation", "StateCheckpoint"}


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class StateJournal:
    """Append-only JSONL event journal with a per-file SHA-256 hash chain."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._head = self._read_head()

    def _read_head(self) -> str:
        if not self.path.exists():
            return GENESIS
        head = GENESIS
        with self.path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    head = json.loads(line)["hash"]
        return head

    def append(self, event_type: str, entity: str, payload: dict[str, Any]) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported event type: {event_type}")
        with self._lock:
            record = {
                "schema": "eaon.state-journal/v1",
                "event_id": str(uuid.uuid4()),
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "type": event_type,
                "entity": entity,
                "payload": payload,
                "previous_hash": self._head,
            }
            record["hash"] = hashlib.sha256(_canonical(record)).hexdigest()
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
            self._head = record["hash"]
            return record

    def transition(self, session: str, stage: str, state_from: str, state_to: str,
                   latency_ms: float, **details: Any) -> dict[str, Any]:
        return self.append("Transition", f"voice_session/{session}", {
            "stage": stage, "from": state_from, "to": state_to,
            "latency_ms": round(latency_ms, 3), **details,
        })


def verify(path: str | Path) -> tuple[bool, int, str | None]:
    previous = GENESIS
    count = 0
    with Path(path).open(encoding="utf-8") as stream:
        for count, line in enumerate(stream, 1):
            record = json.loads(line)
            claimed = record.pop("hash", None)
            if record.get("previous_hash") != previous:
                return False, count, "previous_hash mismatch"
            actual = hashlib.sha256(_canonical(record)).hexdigest()
            if claimed != actual:
                return False, count, "record hash mismatch"
            previous = claimed
    return True, count, None
