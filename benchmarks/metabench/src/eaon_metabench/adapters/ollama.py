from __future__ import annotations

import time
from typing import Any

import httpx

from eaon_metabench.adapters.base import ModelAdapter
from eaon_metabench.models import AdapterResponse, BenchmarkCase


SYSTEM_PROMPT = """You are being evaluated for metacognition.
Follow the task exactly. Return only a valid JSON object with this schema:
{
  "decision": "answer" or "abstain",
  "answer": "your concise final answer, or empty when abstaining",
  "confidence": a number from 0 to 1,
  "reason": "one short explanation"
}
Do not add markdown or text outside the JSON object.
Do not invent missing information. Adapt to the latest rule stated in the task.
"""


class OllamaAdapter(ModelAdapter):
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
        temperature: float = 0.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature

    def generate(self, case: BenchmarkCase) -> AdapterResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": case.prompt},
            ],
            "options": {"temperature": self.temperature},
        }

        started = time.perf_counter()
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        latency_ms = (time.perf_counter() - started) * 1000

        message = data.get("message") or {}
        return AdapterResponse(
            text=str(message.get("content", "")),
            latency_ms=latency_ms,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            raw=data,
        )
