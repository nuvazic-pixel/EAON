"""Local microphone decoding; model calls live in the central orchestrator."""

from __future__ import annotations

import io
from pathlib import Path
import wave

MODEL_FOLDER = "sherpa-onnx-whisper-tiny"
MODEL_PARTS = ("tiny-encoder.int8.onnx", "tiny-decoder.int8.onnx", "tiny-tokens.txt")
MAX_RECORDING_BYTES = 4_000_000
MAX_RECORDING_SECONDS = 30


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
