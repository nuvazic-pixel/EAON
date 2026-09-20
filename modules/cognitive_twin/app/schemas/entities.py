from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class EventCreate(BaseModel):
    timestamp: datetime = Field(default_factory=now_utc)
    source: str = "manual"
    event_type: str
    domain: str = "personal"
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence: int
    timestamp: datetime
    subject_id: str
    source: str
    event_type: str
    domain: str
    content: str
    event_metadata: dict[str, Any]
    previous_hash: str
    content_hash: str
    immutable: bool


class EvidenceCreate(BaseModel):
    event_id: str
    excerpt: str
    evidence_type: str = "direct"
    strength: float = Field(default=1.0, ge=0.0, le=1.0)


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    excerpt: str
    evidence_type: str
    strength: float
    created_at: datetime


class NodeCreate(BaseModel):
    node_type: str
    label: str
    description: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    node_type: str
    label: str
    description: str | None
    confidence: float
    status: str
    valid_from: datetime
    valid_to: datetime | None
    node_metadata: dict[str, Any]


class EdgeCreate(BaseModel):
    source_node_id: str
    relation: str
    target_node_id: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EdgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    source_node_id: str
    relation: str
    target_node_id: str
    confidence: float
    evidence_id: str | None
    valid_from: datetime
    valid_to: datetime | None
    edge_metadata: dict[str, Any]


class HypothesisCreate(BaseModel):
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    alternative_interpretation: str | None = None
    status: str = "unconfirmed"
    evidence_ids: list[str] = Field(default_factory=list)


class HypothesisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    statement: str
    confidence: float
    alternative_interpretation: str | None
    status: str
    user_feedback: str | None
    created_at: datetime
    updated_at: datetime


class HypothesisFeedback(BaseModel):
    feedback: str = Field(pattern="^(confirmed|rejected|uncertain)$")


class SnapshotCreate(BaseModel):
    timestamp: datetime = Field(default_factory=now_utc)
    snapshot: dict[str, Any]
    generated_from_event_sequence: int | None = None


class SnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_id: str
    timestamp: datetime
    snapshot: dict[str, Any]
    generated_from_event_sequence: int | None
