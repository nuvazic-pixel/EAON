from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
from typing import Any


ZERO_HASH = "0" * 64


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ExperimentJournal:
    """
    Append-only JSONL journal with a SHA-256 hash chain.

    The hash chain is tamper-evident, not physically immutable:
    editing old records changes the verification result.
    """

    def __init__(self, path: str | Path, experiment_id: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.experiment_id = experiment_id

    def read_events(self) -> list[dict]:
        if not self.path.exists():
            return []
        events = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events

    def _tail(self) -> tuple[int, str]:
        events = self.read_events()
        if not events:
            return -1, ZERO_HASH
        last = events[-1]
        return int(last["seq"]), str(last["hash"])

    def append(self, event_type: str, payload: dict, *, timestamp: str | None = None) -> dict:
        last_seq, prev_hash = self._tail()

        body = {
            "journal_schema": "0.4",
            "experiment_id": self.experiment_id,
            "seq": last_seq + 1,
            "timestamp": timestamp or utc_now_iso(),
            "event_type": event_type,
            "payload": payload,
            "prev_hash": prev_hash,
        }
        record_hash = sha256_text(canonical_json(body))
        record = body | {"hash": record_hash}

        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(canonical_json(record) + "\n")
        return record

    def verify_chain(self) -> dict:
        previous_hash = ZERO_HASH
        expected_seq = 0
        events = self.read_events()

        for idx, record in enumerate(events):
            if record.get("seq") != expected_seq:
                return {
                    "valid": False,
                    "error": "sequence_mismatch",
                    "event_index": idx,
                    "expected_seq": expected_seq,
                    "actual_seq": record.get("seq"),
                }

            if record.get("prev_hash") != previous_hash:
                return {
                    "valid": False,
                    "error": "previous_hash_mismatch",
                    "event_index": idx,
                }

            supplied_hash = record.get("hash")
            body = {k: v for k, v in record.items() if k != "hash"}
            calculated_hash = sha256_text(canonical_json(body))
            if supplied_hash != calculated_hash:
                return {
                    "valid": False,
                    "error": "record_hash_mismatch",
                    "event_index": idx,
                }

            previous_hash = supplied_hash
            expected_seq += 1

        return {
            "valid": True,
            "events": len(events),
            "head_hash": previous_hash,
        }
