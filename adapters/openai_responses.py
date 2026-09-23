"""Minimal OpenAI Responses API adapter for EAON.

Uses requests to avoid adding a new runtime dependency. API keys are read
from the environment and are never persisted by this module.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional

import requests


MODEL_BY_TIER = {
    "luna": "gpt-6-luna",
    "sol": "gpt-6-sol",
}


@dataclass(frozen=True)
class OpenAIResult:
    text: str
    model: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0


class OpenAIResponsesAdapter:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 120.0,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def run(self, prompt: str, tier: str, reasoning_effort: str = "none") -> OpenAIResult:
        if tier not in MODEL_BY_TIER:
            raise ValueError(f"unsupported OpenAI tier: {tier}")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        model = MODEL_BY_TIER[tier]
        started = time.perf_counter()
        response = requests.post(
            f"{self.base_url}/responses",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": prompt,
                "reasoning": {"effort": reasoning_effort},
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        latency_ms = (time.perf_counter() - started) * 1000.0

        usage = payload.get("usage") or {}
        input_details = usage.get("input_tokens_details") or {}
        return OpenAIResult(
            text=_extract_output_text(payload),
            model=model,
            latency_ms=latency_ms,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            cached_input_tokens=int(input_details.get("cached_tokens") or 0),
        )


def _extract_output_text(payload: dict) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str):
        return direct

    parts = []
    for item in payload.get("output") or []:
        for content in item.get("content") or []:
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "".join(parts)
