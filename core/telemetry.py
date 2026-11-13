"""Local metadata-only telemetry shared by the CLI and voice UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import threading

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "telemetry.jsonl"


@dataclass(frozen=True)
class TurnEvent:
    """Fixed fields prevent raw prompts, audio, responses or history in the log."""

    request_id: str
    source: str
    intent: str
    model: str
    mode: str
    ok: bool
    error_code: str | None
    total_ms: float
    inference_ms: float
    stt_ms: float | None
    timestamp: str
    final_output_origin: str | None = None
    previous_model: str | None = None
    model_switched: bool = False
    switch_latency_ms: float | None = None
    cache_warm: bool | None = None
    prefix_hit: float | None = None
    model_residency: str | None = None

    @classmethod
    def create(cls, *, request_id: str, source: str, intent: str, model: str,
               mode: str, ok: bool, error: str | None, total_ms: float,
               inference_ms: float, stt_ms: float | None, final_output_origin=None, routing_observation=None) -> "TurnEvent":
        allowed_errors = {
            "unknown_model_id", "invalid_prompt", "model_missing", "ollama_unavailable",
            "ollama_http_error", "ollama_invalid_response", "empty_model_response",
            "llama3_unavailable", "mistral_unavailable",
            "context_invalid_configuration", "context_requires_local_mode",
            "context_integrity_failed", "context_project_unavailable", "context_owner_mismatch",
            "context_budget_exceeded", "context_retrieval_failed", "context_required_evidence_missing",
            "context_changed_during_retrieval", "context_invalid_payload",
            "context_state_contaminated",
            "model_identity_mismatch", "voice_uncommitted",
        }
        routing = routing_observation or {}
        origins = {"ollama:llama3", "ollama:mistral", "model_handler:llama3", "model_handler:mistral"}
        previous = routing.get("previous_model")
        switched = routing.get("model_switched") is True
        latency = routing.get("switch_latency_ms")
        latency = round(latency, 2) if type(latency) in (int, float) and 0 <= latency < 1e12 else None
        return cls(
            request_id=request_id, source=source, intent=intent, model=model,
            mode=mode, ok=ok,
            error_code=error if error in allowed_errors else ("execution_error" if error else None),
            total_ms=round(total_ms, 2), inference_ms=round(inference_ms, 2),
            stt_ms=round(stt_ms, 2) if stt_ms is not None else None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            final_output_origin=final_output_origin if ok and final_output_origin in origins else None,
            previous_model=previous if previous in {"llama3", "mistral"} else None,
            model_switched=switched, switch_latency_ms=latency if switched else None,
        )


class TelemetryRecorder:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()

    def record(self, event: TurnEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = (json.dumps(asdict(event), ensure_ascii=False) + "\n").encode("utf-8")
        with self._lock, self.path.open("ab") as stream:
            stream.write(line)
