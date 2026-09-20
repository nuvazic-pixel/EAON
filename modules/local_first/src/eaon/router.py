from __future__ import annotations

import json
import urllib.error
import urllib.request

from .models import RouteDecision


class LocalRouter:
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model: str = "qwen3:8b") -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model

    def decide(self) -> RouteDecision:
        try:
            with urllib.request.urlopen(f"{self.ollama_url}/api/tags", timeout=1.5) as response:
                available = {item["name"] for item in json.load(response).get("models", [])}
            if self.model in available or any(name.startswith(f"{self.model}:") for name in available):
                return RouteDecision("ollama", f"Local model {self.model} is available")
            return RouteDecision("extractive", f"Ollama is online but {self.model} is not installed")
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            return RouteDecision("extractive", "Ollama unavailable; deterministic local fallback")

    def generate(self, prompt: str, evidence: list[str]) -> tuple[str, RouteDecision]:
        route = self.decide()
        if route.backend == "extractive":
            if not evidence:
                return "Nu am suficiente dovezi locale pentru un răspuns.", route
            answer = "Dovezile locale relevante indică:\n" + "\n".join(f"- {item}" for item in evidence[:5])
            return answer, route
        payload = json.dumps({
            "model": self.model,
            "stream": False,
            "prompt": (
                "You are EAON. Answer only from the supplied evidence. Separate facts from inference. "
                "If evidence is insufficient, say so.\n\nGOAL:\n" + prompt +
                "\n\nEVIDENCE:\n" + "\n".join(f"[{i+1}] {item}" for i, item in enumerate(evidence))
            ),
        }).encode()
        request = urllib.request.Request(
            f"{self.ollama_url}/api/generate", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response).get("response", "").strip(), route
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            fallback = RouteDecision("extractive", f"Ollama failed safely: {type(exc).__name__}")
            return self.generate_extractively(evidence), fallback

    @staticmethod
    def generate_extractively(evidence: list[str]) -> str:
        if not evidence:
            return "Nu am suficiente dovezi locale pentru un răspuns."
        return "Dovezile locale relevante indică:\n" + "\n".join(f"- {item}" for item in evidence[:5])
