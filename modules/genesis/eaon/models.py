from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryRecord:
    kind: str
    text: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"mem_{uuid4().hex}")
    timestamp: str = field(default_factory=utc_now_iso)
    previous_hash: str = "GENESIS"
    content_hash: str = ""

    def unsigned_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("content_hash", None)
        return payload

    def signed(self) -> "MemoryRecord":
        digest = sha256_text(stable_json(self.unsigned_payload()))
        return MemoryRecord(
            id=self.id,
            timestamp=self.timestamp,
            kind=self.kind,
            text=self.text,
            tags=list(self.tags),
            metadata=dict(self.metadata),
            previous_hash=self.previous_hash,
            content_hash=digest,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryRecord":
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            kind=data["kind"],
            text=data["text"],
            tags=list(data.get("tags", [])),
            metadata=dict(data.get("metadata", {})),
            previous_hash=data.get("previous_hash", "GENESIS"),
            content_hash=data.get("content_hash", ""),
        )


@dataclass(frozen=True)
class RouteResult:
    label: str
    score: float
    reasons: list[str]


@dataclass(frozen=True)
class DebugItem:
    kind: str
    text: str
    confidence: float


@dataclass(frozen=True)
class DebugReport:
    items: list[DebugItem]

    def by_kind(self, kind: str) -> list[DebugItem]:
        return [item for item in self.items if item.kind == kind]

    def to_dict(self) -> dict[str, Any]:
        return {"items": [asdict(item) for item in self.items]}


@dataclass(frozen=True)
class CouncilResponse:
    architect: str
    skeptic: str
    implementer: str
    judge: str
    next_step: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
