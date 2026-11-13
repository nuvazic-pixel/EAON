"""A failed backend cannot be converted into an agent's invented final output."""
from hashlib import sha256
import json
from unittest.mock import patch

from core.orchestrator import Orchestrator
from core.telemetry import TelemetryRecorder


def test_actual_response_has_origin_and_digest_but_failure_has_no_final_output(tmp_path):
    orch = Orchestrator(local_only=True, telemetry=TelemetryRecorder(tmp_path / "log.jsonl"))
    response = {"model": "llama3:latest", "message": {"content": " Actual answer "}},
    with patch("core.ollama_client._request", return_value=response[0]):
        _, report = orch.run("Salut")
    assert report.ok and report.output_text == "Actual answer"
    assert report.final_output_origin["origin"] == "ollama:llama3"
    assert report.final_output_origin["response_sha256"] == sha256(b"Actual answer").hexdigest()
    with patch("core.ollama_client._request", side_effect=RuntimeError("private crash detail")):
        _, failure = orch.run("Salut")
    assert not failure.ok and failure.output_text is None and failure.final_output_origin is None
    events = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert events[0]["final_output_origin"] == "ollama:llama3" and events[1]["final_output_origin"] is None
    assert "private crash detail" not in str(failure)


def test_wrong_model_identity_is_rejected_without_success_or_output(tmp_path):
    orch = Orchestrator(local_only=True, telemetry=TelemetryRecorder(tmp_path / "log.jsonl"))
    with patch("core.ollama_client._request", return_value={"model": "mistral", "message": {"content": "Wrong responder"}}):
        _, report = orch.run("Salut")
    assert not report.ok and report.error == "model_identity_mismatch"
    assert report.output_text is None and report.final_output_origin is None


def test_switch_latency_is_observed_call_time_and_cache_fields_remain_unknown(tmp_path):
    orch = Orchestrator(local_only=True, telemetry=TelemetryRecorder(tmp_path / "log.jsonl"))
    with patch("core.ollama_client._request", return_value={"message": {"content": "answer"}}):
        _, first = orch.run("Salut")
        _, second = orch.run("security attack")
        _, third = orch.run("security attack")
    assert first.routing_observation["previous_model"] is None
    assert second.routing_observation["model_switched"]
    assert second.routing_observation["switch_latency_ms"] == second.inference_time_ms
    assert not third.routing_observation["model_switched"] and third.routing_observation["switch_latency_ms"] is None
    for report in (first, second, third):
        assert all(report.routing_observation[key] is None for key in ("cache_warm", "prefix_hit", "model_residency"))
