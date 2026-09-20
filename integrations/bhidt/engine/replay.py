from __future__ import annotations

import json
from pathlib import Path


def load_events(journal_path: str | Path) -> list[dict]:
    path = Path(journal_path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def replay_snapshots(journal_path: str | Path) -> list[dict]:
    return [
        event["payload"]["snapshot"]
        for event in load_events(journal_path)
        if event["event_type"] == "SNAPSHOT"
    ]


def transition_event(journal_path: str | Path) -> dict:
    transitions = [
        event
        for event in load_events(journal_path)
        if event["event_type"] == "PAGE_TRANSITION"
    ]
    if not transitions:
        raise LookupError("No PAGE_TRANSITION event found")
    return transitions[0]


def replay_around_transition(
    journal_path: str | Path,
    *,
    before: int = 10,
    after: int = 10,
) -> dict:
    snapshots = replay_snapshots(journal_path)
    transition = transition_event(journal_path)
    transition_tau = transition["payload"]["transition"]["current_tau"]

    center = min(
        range(len(snapshots)),
        key=lambda i: abs(snapshots[i]["tau"] - transition_tau),
    )
    lo = max(0, center - before)
    hi = min(len(snapshots), center + after + 1)

    return {
        "transition_event": transition,
        "center_snapshot_index": center,
        "window_start_index": lo,
        "window_end_index_exclusive": hi,
        "snapshots": snapshots[lo:hi],
    }
