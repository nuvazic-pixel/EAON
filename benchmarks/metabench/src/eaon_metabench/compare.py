from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_KEYS = {
    "overall_score",
    "accuracy",
    "calibration_score",
    "abstention_f1",
    "recovery_adaptation_score",
    "parse_rate",
    "median_latency_ms",
}


def load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "metadata" not in payload or "summary" not in payload:
        raise ValueError(f"{path} is not an EAON MetaBench report.")
    missing = REQUIRED_KEYS.difference(payload["summary"])
    if missing:
        raise ValueError(f"{path} is missing summary fields: {sorted(missing)}")
    return payload
