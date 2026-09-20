import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Event, JournalHead
from app.schemas.entities import EventCreate
from app.services.policy import enforce_personal_twin_policy

GENESIS_HASH = "0" * 64


def canonical_event_payload(*, sequence: int, timestamp: datetime, subject_id: str, source: str,
                            event_type: str, domain: str, content: str, metadata: dict,
                            previous_hash: str) -> str:
    payload = {
        "sequence": sequence,
        "timestamp": timestamp.astimezone(timezone.utc).isoformat(),
        "subject_id": subject_id,
        "source": source,
        "event_type": event_type,
        "domain": domain,
        "content": content,
        "metadata": metadata,
        "previous_hash": previous_hash,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def calculate_hash(**kwargs) -> str:
    canonical = canonical_event_payload(**kwargs)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_journal_head(db: Session) -> JournalHead:
    head = db.get(JournalHead, 1)
    if head is None:
        head = JournalHead(id=1, sequence=0, last_hash=GENESIS_HASH)
        db.add(head)
        db.flush()
    return head


def append_event(db: Session, payload: EventCreate) -> Event:
    enforce_personal_twin_policy(payload.domain)
    settings = get_settings()

    # Serialize local journal writes through a single locked head row.
    head = db.scalar(select(JournalHead).where(JournalHead.id == 1).with_for_update())
    if head is None:
        head = ensure_journal_head(db)

    sequence = head.sequence + 1
    previous_hash = head.last_hash
    timestamp = payload.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    hash_kwargs = dict(
        sequence=sequence,
        timestamp=timestamp,
        subject_id=settings.twin_subject_id,
        source=payload.source,
        event_type=payload.event_type,
        domain=payload.domain,
        content=payload.content,
        metadata=payload.metadata,
        previous_hash=previous_hash,
    )
    content_hash = calculate_hash(**hash_kwargs)

    event = Event(
        sequence=sequence,
        timestamp=timestamp,
        subject_id=settings.twin_subject_id,
        source=payload.source,
        event_type=payload.event_type,
        domain=payload.domain,
        content=payload.content,
        event_metadata=payload.metadata,
        previous_hash=previous_hash,
        content_hash=content_hash,
    )
    db.add(event)
    head.sequence = sequence
    head.last_hash = content_hash
    head.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event


def verify_journal(db: Session) -> dict:
    events = list(db.scalars(select(Event).order_by(Event.sequence.asc())).all())
    previous_hash = GENESIS_HASH
    expected_sequence = 1

    for event in events:
        if event.sequence != expected_sequence:
            return {"valid": False, "reason": "sequence_gap", "at_sequence": event.sequence}
        if event.previous_hash != previous_hash:
            return {"valid": False, "reason": "previous_hash_mismatch", "at_sequence": event.sequence}

        recalculated = calculate_hash(
            sequence=event.sequence,
            timestamp=event.timestamp,
            subject_id=event.subject_id,
            source=event.source,
            event_type=event.event_type,
            domain=event.domain,
            content=event.content,
            metadata=event.event_metadata,
            previous_hash=event.previous_hash,
        )
        if recalculated != event.content_hash:
            return {"valid": False, "reason": "content_hash_mismatch", "at_sequence": event.sequence}

        previous_hash = event.content_hash
        expected_sequence += 1

    return {
        "valid": True,
        "event_count": len(events),
        "last_sequence": events[-1].sequence if events else 0,
        "last_hash": previous_hash,
    }
