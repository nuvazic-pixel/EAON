from datetime import datetime, timezone

from app.services.journal import calculate_hash


def test_hash_is_deterministic_and_sensitive_to_content():
    base = dict(
        sequence=1,
        timestamp=datetime(2026, 9, 5, 8, 20, tzinfo=timezone.utc),
        subject_id="self",
        source="test",
        event_type="thought",
        domain="cognitive",
        content="Digital Twin",
        metadata={"x": 1},
        previous_hash="0" * 64,
    )
    h1 = calculate_hash(**base)
    h2 = calculate_hash(**base)
    assert h1 == h2

    changed = {**base, "content": "Digital Twin changed"}
    assert calculate_hash(**changed) != h1
