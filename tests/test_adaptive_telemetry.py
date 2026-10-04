import json

from core.adaptive_telemetry import (
    AdaptiveTrace,
    append_trace,
    estimate_standard_cost_usd,
)


def test_luna_cost_estimate():
    cost = estimate_standard_cost_usd("gpt-6-luna", 1_000_000, 1_000_000)
    assert cost == 0.60


def test_sol_cost_estimate():
    cost = estimate_standard_cost_usd("gpt-6-sol", 1_000_000, 1_000_000)
    assert cost == 12.0


def test_cached_tokens_use_cached_rate():
    cost = estimate_standard_cost_usd(
        "gpt-6-sol", input_tokens=1_000_000, output_tokens=0, cached_input_tokens=500_000
    )
    assert cost == 1.1


def test_append_trace_writes_jsonl(tmp_path):
    target = tmp_path / "adaptive.jsonl"
    trace = AdaptiveTrace(
        task_id="T001",
        tier="luna",
        model="gpt-6-luna",
        complexity=0.2,
        privacy_level="cloud_ok",
        reason="baseline",
        latency_ms=10.0,
        input_tokens=12,
        output_tokens=4,
    )
    append_trace(trace, str(target))
    row = json.loads(target.read_text(encoding="utf-8").strip())
    assert row["task_id"] == "T001"
    assert row["model"] == "gpt-6-luna"
    assert row["timestamp_unix"] > 0
