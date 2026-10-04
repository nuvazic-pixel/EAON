"""Telemetry primitives for EAON adaptive routing."""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


SHORT_CONTEXT_PRICES_PER_MILLION = {
    "gpt-6-luna": {"input": 0.10, "cached_input": 0.01, "output": 0.50},
    "gpt-6-sol": {"input": 2.00, "cached_input": 0.20, "output": 10.00},
}


def estimate_standard_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> Optional[float]:
    prices = SHORT_CONTEXT_PRICES_PER_MILLION.get(model)
    if not prices:
        return None
    cached = min(max(cached_input_tokens, 0), max(input_tokens, 0))
    uncached = max(input_tokens - cached, 0)
    return (
        uncached * prices["input"]
        + cached * prices["cached_input"]
        + max(output_tokens, 0) * prices["output"]
    ) / 1_000_000.0


@dataclass(frozen=True)
class AdaptiveTrace:
    task_id: str
    tier: str
    model: str
    complexity: float
    privacy_level: str
    reason: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    cost_usd: Optional[float] = None
    verified: Optional[bool] = None
    escalated: bool = False
    timestamp_unix: float = 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        if not data["timestamp_unix"]:
            data["timestamp_unix"] = time.time()
        return data


def append_trace(trace: AdaptiveTrace, path: str = "logs/adaptive.jsonl") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(trace.to_dict(), sort_keys=True) + "\n")
