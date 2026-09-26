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

    @classmethod
    def create(cls, *, request_id: str, source: str, intent: str, model: str,
               mode: str, ok: bool, error: str | None, total_ms: float,
               inference_ms: float, stt_ms: float | None) -> "TurnEvent":
        allowed_errors = {
            "unknown_model_id", "invalid_prompt", "model_missing", "ollama_unavailable",
            "ollama_http_error", "ollama_invalid_response", "empty_model_response",
            "llama3_unavailable", "mistral_unavailable",
        }
        return cls(
            request_id=request_id, source=source, intent=intent, model=model,
            mode=mode, ok=ok,
            error_code=error if error in allowed_errors else ("execution_error" if error else None),
            total_ms=round(total_ms, 2), inference_ms=round(inference_ms, 2),
            stt_ms=round(stt_ms, 2) if stt_ms is not None else None,
            timestamp=datetime.now(timezone.utc).isoformat(),
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
