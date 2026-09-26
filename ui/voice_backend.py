"""Speech-to-text and multi-turn Ollama chat for the local EAON UI."""

from __future__ import annotations

import io
import json
from pathlib import Path
import urllib.error
import urllib.request
import wave

from core.inference_gateway import InferenceGateway, ModelDispatchError

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL_NAMES = ("llama3", "mistral")
MODEL_FOLDER = "sherpa-onnx-whisper-tiny"
MODEL_PARTS = ("tiny-encoder.int8.onnx", "tiny-decoder.int8.onnx", "tiny-tokens.txt")
MAX_RECORDING_BYTES = 4_000_000
MAX_RECORDING_SECONDS = 30
MAX_PROMPT_CHARS = 4_000
SYSTEM_PROMPT = (
    "Ești EAON, un asistent local de conversație. Răspunde în limba utilizatorului, "
    "clar și concis. Poți discuta și explica, dar această interfață nu are "
    "acces la comenzi, fișiere, dispozitive sau acțiuni fizice. "
    "Nu afirma că ai executat acțiuni pe care nu le-ai executat."
)


class VoiceUIError(ValueError):
    """A user-visible, recoverable local UI error."""


def model_directory(repo_root: Path) -> Path:
    return repo_root / "models" / MODEL_FOLDER


def model_ready(directory: Path) -> bool:
    return all((directory / part).is_file() for part in MODEL_PARTS)


def decode_wav(recording: bytes):
    """Decode Streamlit's mono, PCM16, 16 kHz WAV without saving audio."""
    if not recording or len(recording) > MAX_RECORDING_BYTES:
        raise VoiceUIError("Înregistrarea este goală sau prea mare (maxim 4 MB).")
    try:
        with wave.open(io.BytesIO(recording), "rb") as source:
            if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 16_000):
                raise VoiceUIError("Microfonul trebuie să trimită WAV mono, PCM16, 16 kHz.")
            frames = source.getnframes()
            if not 0 < frames <= 16_000 * MAX_RECORDING_SECONDS:
                raise VoiceUIError("Înregistrează cel mult 30 de secunde.")
            pcm = source.readframes(frames)
            if len(pcm) != frames * 2:
                raise VoiceUIError("Înregistrarea WAV este incompletă.")
    except (wave.Error, EOFError) as exc:
        raise VoiceUIError("Înregistrarea WAV nu poate fi citită.") from exc

    import numpy as np

    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0


def create_recognizer(directory: Path, language: str = "ro"):
    """Load Sherpa's multilingual Whisper tiny from the ignored models folder."""
    if language not in ("ro", "de", "en", ""):
        raise VoiceUIError("Limba de transcriere nu este acceptată.")
    if not model_ready(directory):
        raise VoiceUIError("Lipsește modelul Sherpa. Rulează: py -3.12 scripts\\setup_voice_model.py")
    import sherpa_onnx

    return sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(directory / MODEL_PARTS[0]),
        decoder=str(directory / MODEL_PARTS[1]),
        tokens=str(directory / MODEL_PARTS[2]),
        language=language,
        task="transcribe",
    )


def transcribe(recording: bytes, recognizer) -> str:
    samples = decode_wav(recording)
    stream = recognizer.create_stream()
    stream.accept_waveform(16_000, samples)
    recognizer.decode_stream(stream)
    result = stream.result.text.strip()
    if not result:
        raise VoiceUIError("Nu am recunoscut cuvinte. Încearcă din nou mai aproape de microfon.")
    return result


def _local_json(path: str, payload: dict | None = None, *, timeout: int = 3) -> dict:
    request = urllib.request.Request(
        OLLAMA_URL + path,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    # Ignore HTTP(S)_PROXY: model traffic must remain on loopback.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("unexpected Ollama JSON")
        return result
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and isinstance(payload, dict) and isinstance(payload.get("model"), str):
            raise VoiceUIError(f"Modelul lipsește. Rulează: ollama pull {payload['model']}") from exc
        raise VoiceUIError(f"Ollama a răspuns cu eroarea HTTP {exc.code}.") from exc
    except (OSError, ValueError) as exc:
        raise VoiceUIError("Ollama nu răspunde la 127.0.0.1:11434. Pornește Ollama local.") from exc


def installed_models() -> set[str]:
    result = _local_json("/api/tags")
    return {
        item["name"].split(":", 1)[0]
        for item in result.get("models", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }


def chat_reply(prompt: str, history: list[dict], model: str) -> str:
    """Send bounded conversation to an explicitly selected Ollama model."""
    prompt = prompt.strip()
    if not prompt or len(prompt) > MAX_PROMPT_CHARS:
        raise VoiceUIError("Mesajul trebuie să aibă între 1 și 4000 de caractere.")
    # Only locally generated user/assistant turns go to Ollama; never tool calls.
    recent = [
        {"role": turn["role"], "content": turn["content"][:MAX_PROMPT_CHARS]}
        for turn in history
        if isinstance(turn, dict)
        and turn.get("role") in ("user", "assistant")
        and isinstance(turn.get("content"), str)
    ][-12:]

    def ask(selected: str) -> str:
        result = _local_json(
            "/api/chat",
            {"model": selected, "stream": False, "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                *recent,
                {"role": "user", "content": prompt},
            ]},
            timeout=120,
        )
        message = result.get("message", {})
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise VoiceUIError("Ollama nu a trimis un răspuns text.")
        return message["content"].strip()

    gateway = InferenceGateway({name: lambda _, chosen=name: ask(chosen) for name in MODEL_NAMES})
    try:
        return gateway.dispatch(model, prompt)
    except ModelDispatchError as exc:
        if str(exc) == "empty_model_response":
            raise VoiceUIError("Ollama a trimis un răspuns gol. Încearcă din nou.") from exc
        raise VoiceUIError(f"Modelul selectat nu este disponibil: {model!r}.") from exc
