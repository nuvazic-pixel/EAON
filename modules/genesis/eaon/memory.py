from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Iterable

from eaon.models import MemoryRecord


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+", re.UNICODE)


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


class MemoryIntegrityError(ValueError):
    """The journal cannot be trusted for reading or appending."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("Memory integrity check failed: " + "; ".join(self.errors))


class MemoryStore:
    """Append-only JSONL memory store with a simple hash chain."""

    def __init__(self, path: str | Path = "./data/memory.jsonl") -> None:
        self.path = Path(path)

    def append(
        self,
        *,
        kind: str,
        text: str,
        tags: Iterable[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = MemoryRecord(
            kind=kind,
            text=text.strip(),
            tags=list(tags or []),
            metadata=dict(metadata or {}),
            previous_hash=self.last_hash(),
        ).signed()
        encoded = (json.dumps(record.to_dict(), ensure_ascii=False) + "\n").encode("utf-8")
        with self.path.open("a+b") as handle:
            handle.seek(0, 2)
            if handle.tell():
                handle.seek(-1, 2)
                if handle.read(1) != b"\n":
                    handle.write(b"\n")
            handle.write(encoded)
        return record

    def records(self) -> list[MemoryRecord]:
        """Return only the exact journal snapshot whose chain was verified."""
        records = self._read_records()
        errors = self._chain_errors(records)
        if errors:
            raise MemoryIntegrityError(errors)
        return records

    def _read_records(self) -> list[MemoryRecord]:
        if not self.path.exists():
            return []
        output: list[MemoryRecord] = []
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if line.strip():
                        try:
                            output.append(MemoryRecord.from_dict(json.loads(line)))
                        except (KeyError, TypeError, ValueError) as exc:
                            raise MemoryIntegrityError(
                                [f"line {line_number} invalid record"]
                            ) from exc
        except UnicodeError as exc:
            raise MemoryIntegrityError(["journal is not valid UTF-8"]) from exc
        return output

    def last_hash(self) -> str:
        records = self.records()
        if not records:
            return "GENESIS"
        return records[-1].content_hash

    def verify_chain(self) -> tuple[bool, list[str]]:
        try:
            records = self._read_records()
        except MemoryIntegrityError as exc:
            return False, exc.errors
        errors = self._chain_errors(records)
        return not errors, errors

    @staticmethod
    def _chain_errors(records: Iterable[MemoryRecord]) -> list[str]:
        errors: list[str] = []
        previous = "GENESIS"
        for index, record in enumerate(records):
            if record.previous_hash != previous:
                errors.append(f"record {index} previous_hash mismatch")
            try:
                digest = record.signed().content_hash
            except (TypeError, ValueError):
                errors.append(f"record {index} invalid payload")
            else:
                if digest != record.content_hash:
                    errors.append(f"record {index} content_hash mismatch")
            previous = record.content_hash
        return errors

    def search(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        records = self.records()
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, int, MemoryRecord]] = []
        for index, record in enumerate(records):
            haystack = " ".join([record.text, " ".join(record.tags), record.kind])
            tokens = tokenize(haystack)
            overlap = query_tokens & tokens
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            recency_boost = index / max(len(records), 1) * 0.05
            scored.append((score + recency_boost, index, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, _, record in scored[:limit]]

    def snapshot(self, limit: int = 10) -> list[MemoryRecord]:
        return self.records()[-limit:]
