from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Iterable

from eaon.models import MemoryRecord


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+", re.UNICODE)


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


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
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        return record

    def records(self) -> list[MemoryRecord]:
        if not self.path.exists():
            return []
        output: list[MemoryRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    output.append(MemoryRecord.from_dict(json.loads(line)))
        return output

    def last_hash(self) -> str:
        records = self.records()
        if not records:
            return "GENESIS"
        return records[-1].content_hash

    def verify_chain(self) -> tuple[bool, list[str]]:
        records = self.records()
        errors: list[str] = []
        previous = "GENESIS"
        for index, record in enumerate(records):
            if record.previous_hash != previous:
                errors.append(f"record {index} previous_hash mismatch")
            if record.signed().content_hash != record.content_hash:
                errors.append(f"record {index} content_hash mismatch")
            previous = record.content_hash
        return (not errors, errors)

    def search(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, int, MemoryRecord]] = []
        records = self.records()
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
