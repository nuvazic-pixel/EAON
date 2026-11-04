"""Small, provider-neutral contracts; retrieved evidence never grants authority."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import math
from datetime import datetime


class ValidationError(ValueError):
    pass


class ConflictError(ValidationError):
    pass


class IntegrityError(RuntimeError):
    pass


def text(value: str, field: str, limit: int = 20000) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValidationError(f"{field} must be non-empty text (at most {limit} characters)")
    return value


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    uri: str
    text: str
    sha256: str

    def __post_init__(self):
        text(self.source_id, "source_id", 500)
        text(self.uri, "source URI", 2000)
        text(self.text, "captured source text", 100000)
        if self.sha256 != sha256(self.text.encode("utf-8")).hexdigest():
            raise ValidationError("Source digest does not match captured text")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceCandidate:
    source: SourceRef
    provider: str
    owner_id: str
    collection_id: str | None = None
    score: float | None = None
    revoked: bool = False
    expires_at: str | None = None
    retrieved_at: str | None = None

    def __post_init__(self):
        if not isinstance(self.source, SourceRef):
            raise ValidationError("Candidate requires a SourceRef")
        text(self.provider, "provider", 100)
        text(self.owner_id, "owner_id", 500)
        if self.collection_id is not None:
            text(self.collection_id, "collection_id", 500)
        if self.score is not None and (type(self.score) not in (int, float) or not math.isfinite(self.score)):
            raise ValidationError("Candidate score must be finite")
        if type(self.revoked) is not bool:
            raise ValidationError("revoked must be boolean")
        if self.expires_at is not None:
            stamp = datetime.fromisoformat(self.expires_at)
            if stamp.tzinfo is None:
                raise ValidationError("Evidence expiry requires a timezone")
        if self.retrieved_at is not None and datetime.fromisoformat(self.retrieved_at).tzinfo is None:
            raise ValidationError("Evidence retrieval time requires a timezone")

    def to_dict(self) -> dict:
        return asdict(self)
