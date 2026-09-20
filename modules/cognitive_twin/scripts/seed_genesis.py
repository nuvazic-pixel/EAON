"""Seed two synthetic Cognitive Twin examples (no personal journal data).

Run:
  docker compose exec api python scripts/seed_genesis.py
"""
from datetime import datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Event
from app.schemas.entities import EventCreate
from app.services.journal import append_event

SEEDS = [
    EventCreate(
        timestamp=datetime.fromisoformat("2026-09-05T10:20:00+02:00"),
        source="synthetic_example",
        event_type="idea",
        domain="cognitive",
        content=(
            "Synthetic example: connect a saved idea to its evidence and one "
            "small validation step."
        ),
        metadata={"synthetic": True, "tags": ["digital_twin", "evidence"]},
    ),
    EventCreate(
        timestamp=datetime.fromisoformat("2026-09-05T11:00:00+02:00"),
        source="synthetic_example",
        event_type="decision",
        domain="cognitive",
        content=(
            "Synthetic example: keep personal cognitive observations separate "
            "from professional records."
        ),
        metadata={"synthetic": True, "tags": ["architecture", "scope", "personal_twin"]},
    ),
]


def main():
    with SessionLocal() as db:
        existing_contents = set(db.scalars(select(Event.content)).all())
        inserted = 0
        for seed in SEEDS:
            if seed.content in existing_contents:
                continue
            append_event(db, seed)
            existing_contents.add(seed.content)
            inserted += 1
        print(f"Genesis seed complete: {inserted} new event(s).")


if __name__ == "__main__":
    main()
