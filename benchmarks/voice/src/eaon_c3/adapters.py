from __future__ import annotations

import json
import random
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PipelineResult:
    wake_detected: bool
    transcript: str
    latencies_ms: dict[str, float]
    model: str


class MockAdapter:
    """Deterministic smoke-test backend; it is not a performance benchmark."""
    name = "mock-v1"

    def run(self, audio: Path, reference: str, wake_expected: bool) -> PipelineResult:
        rng = random.Random(str(audio))
        return PipelineResult(wake_expected, reference, {
            "wake": rng.uniform(4, 9), "vad": rng.uniform(2, 6),
            "stt": rng.uniform(60, 140), "router": rng.uniform(.2, 1.5),
            "llm": rng.uniform(120, 300), "tts": rng.uniform(40, 100),
        }, self.name)


class CommandAdapter:
    """Runs a local adapter executable and accepts one JSON result on stdout.

    Tokens {audio}, {language}, {reference}, and {wake_expected} are replaced
    without invoking a shell. This is the stable boundary for Sherpa-ONNX.
    """
    name = "command"

    def __init__(self, command: str, language: str):
        self.command, self.language = command, language

    def run(self, audio: Path, reference: str, wake_expected: bool) -> PipelineResult:
        replacements = {"audio": str(audio), "language": self.language,
                        "reference": reference, "wake_expected": str(wake_expected).lower()}
        args = [part.format(**replacements) for part in shlex.split(self.command, posix=False)]
        completed = subprocess.run(args, check=True, text=True, capture_output=True)
        value = json.loads(completed.stdout)
        required = {"wake_detected", "transcript", "latencies_ms"}
        missing = required - value.keys()
        if missing:
            raise ValueError(f"adapter result missing: {sorted(missing)}")
        return PipelineResult(bool(value["wake_detected"]), value["transcript"],
                              value["latencies_ms"], value.get("model", "sherpa-onnx"))
