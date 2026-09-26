"""One loopback-only Ollama transport for the CLI and the voice UI."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL_NAMES = ("llama3", "mistral")
MAX_PROMPT_CHARS = 4_000
SYSTEM_PROMPT = (
    "Ești EAON, un asistent local de conversație. Răspunde în limba utilizatorului, "
    "clar și concis. În acest flux poți discuta și explica; nu ai acces la "
    "comenzi, fișiere sau dispozitive. Nu pretinde că ai executat acțiuni."
)


class OllamaError(RuntimeError):
    """A stable error code for an unavailable or invalid local model response."""


def _request(path: str, payload: dict | None = None, *, timeout: int = 3) -> dict:
    request = urllib.request.Request(
        OLLAMA_URL + path,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    # No proxy may see a user's conversation, even if proxy variables are set.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("invalid response")
        return result
    except urllib.error.HTTPError as exc:
        code = "model_missing" if exc.code == 404 and path == "/api/chat" else "ollama_http_error"
        raise OllamaError(code) from exc
    except (OSError, TimeoutError) as exc:
        raise OllamaError("ollama_unavailable") from exc
    except ValueError as exc:
        raise OllamaError("ollama_invalid_response") from exc


def installed_models() -> set[str]:
    data = _request("/api/tags")
    models = data.get("models")
    if not isinstance(models, list):
        raise OllamaError("ollama_invalid_response")
    return {
        item["name"].split(":", 1)[0]
        for item in models
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }


def chat(model: str, prompt: str, history: list[dict] | None = None, *, timeout: int = 30) -> str:
    """Send bounded text history; never forward tool messages or UI metadata."""
    if model not in MODEL_NAMES:
        raise OllamaError("unknown_model_id")
    if not isinstance(prompt, str) or not 0 < len(prompt.strip()) <= MAX_PROMPT_CHARS:
        raise OllamaError("invalid_prompt")
    recent = [
        {"role": turn["role"], "content": turn["content"][:MAX_PROMPT_CHARS]}
        for turn in (history or [])
        if isinstance(turn, dict)
        and turn.get("role") in ("user", "assistant")
        and isinstance(turn.get("content"), str)
    ][-12:]
    result = _request(
        "/api/chat",
        {"model": model, "stream": False, "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *recent,
            {"role": "user", "content": prompt.strip()},
        ]},
        timeout=timeout,
    )
    message = result.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise OllamaError("ollama_invalid_response")
    if not message["content"].strip():
        raise OllamaError("empty_model_response")
    return message["content"].strip()
