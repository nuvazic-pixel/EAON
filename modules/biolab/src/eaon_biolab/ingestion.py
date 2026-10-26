"""Synthetic observations and JSONL ingestion with explicit validation."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .validation import BioDataValidator


class SyntheticBioIngestion:
    def __init__(self, subject_id: str = "synthetic-001"):
        self.subject_id = subject_id

    def generate_batch(self, count: int = 100,
                       start_time: str = "2026-01-01T10:00:00Z",
                       sampling_frequency_seconds: int = 60,
                       metric: str = "heart_rate", unit: str = "bpm") -> list[dict[str, Any]]:
        if count < 0 or sampling_frequency_seconds <= 0:
            raise ValueError("count must be nonnegative and frequency positive")
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("start_time requires a timezone")
        return [
            {
                "observation_id": f"obs-{i:04d}",
                "subject_id": self.subject_id,
                "timestamp": (start + timedelta(seconds=i * sampling_frequency_seconds))
                    .isoformat().replace("+00:00", "Z"),
                "metric": metric,
                "value": float(72 + i % 5 - 2),
                "unit": unit,
                "source": "synthetic",
                "quality_flag": "valid",
            }
            for i in range(count)
        ]


def load_jsonl(path: str | Path, validator: BioDataValidator) -> tuple[list[dict], list[dict]]:
    accepted, rejected = [], []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                observation = json.loads(line)
                errors = validator.validate_observation(observation)
            except json.JSONDecodeError:
                observation, errors = None, ["Invalid JSON"]
            if errors:
                rejected.append({"line": line_number, "errors": errors, "raw": line.rstrip("\n")})
            else:
                accepted.append(observation)
    return accepted, rejected
