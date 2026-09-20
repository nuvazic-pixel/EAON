from __future__ import annotations

import csv
import json
import platform
import time
import uuid
from pathlib import Path

from .journal import StateJournal
from .metrics import summarize, word_error_rate

STAGES = ("wake", "vad", "stt", "router", "llm", "tts")


def run_benchmark(manifest: Path, output: Path, adapter_factory) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    journal = StateJournal(output / "state-journal.jsonl")
    results = []
    with manifest.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    for item in records:
        session = str(uuid.uuid4())
        audio = (manifest.parent / item["audio_path"]).resolve()
        expected = item["wake_expected"].strip().lower() in {"1", "true", "yes"}
        adapter = adapter_factory(item["language"])
        started = time.perf_counter()
        result = adapter.run(audio, item["reference_text"], expected)
        for stage in STAGES:
            journal.transition(session, stage, "pending", "completed",
                               result.latencies_ms.get(stage, 0), model=result.model,
                               language=item["language"], sample_id=item["sample_id"])
        row = {
            "sample_id": item["sample_id"], "language": item["language"],
            "condition": item.get("condition", ""), "wake_expected": expected,
            "wake_detected": result.wake_detected, "reference": item["reference_text"],
            "transcript": result.transcript,
            "wer": round(word_error_rate(item["reference_text"], result.transcript), 4),
            "latencies_ms": result.latencies_ms,
            "wall_ms": round((time.perf_counter() - started) * 1000, 3),
        }
        results.append(row)
        journal.append("Observation", f"voice_session/{session}", {
            "sample_id": item["sample_id"], "wake_expected": expected,
            "wake_detected": result.wake_detected, "wer": row["wer"],
            "raw_audio": "excluded", "transcript_retention": "benchmark-only",
        })
    report = {"schema": "eaon.c3-report/v1", "system": {
        "platform": platform.platform(), "python": platform.python_version(),
        "adapter": getattr(adapter_factory("en"), "name", "unknown")},
        "summary": summarize(results), "samples": results}
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
