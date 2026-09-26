"""Install only the three Sherpa files needed for local Whisper tiny ASR.

No recordings or model files are checked into Git. The archive comes from the
official sherpa-onnx release and is downloaded on the user's own machine.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODEL = "sherpa-onnx-whisper-tiny"
PARTS = ("tiny-encoder.int8.onnx", "tiny-decoder.int8.onnx", "tiny-tokens.txt")
URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-whisper-tiny.tar.bz2"
)
MAX_FILE_BYTES = 350_000_000


def extract_required(archive, destination: Path) -> None:
    """Stream verified member names, avoiding arbitrary paths or tar links."""
    seen = set()
    with tarfile.open(fileobj=archive, mode="r|bz2") as members:
        for member in members:
            if member.name not in {f"{MODEL}/{part}" for part in PARTS}:
                continue
            part = member.name.removeprefix(f"{MODEL}/")
            if not member.isfile() or member.size <= 0 or member.size > MAX_FILE_BYTES or part in seen:
                raise ValueError(f"Invalid or duplicate model file: {member.name}")
            source = members.extractfile(member)
            if source is None:
                raise ValueError(f"Cannot read model file: {member.name}")
            with source, (destination / part).open("wb") as target:
                copied = shutil.copyfileobj(source, target)
            if (destination / part).stat().st_size != member.size:
                raise ValueError(f"Incomplete model file: {member.name}")
            seen.add(part)
    if seen != set(PARTS):
        raise ValueError(f"Missing model files: {', '.join(sorted(set(PARTS) - seen))}")


def install(*, root: Path = ROOT) -> Path:
    models = root / "models"
    target = models / MODEL
    if all((target / name).is_file() for name in PARTS):
        return target
    if target.exists():
        raise ValueError(f"Incomplete model directory: {target}. Remove it and retry.")
    models.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eaon-voice-", dir=models) as temporary:
        staging = Path(temporary)
        print(f"Downloading Sherpa model from {URL}", flush=True)
        with urllib.request.urlopen(URL, timeout=120) as response:
            extract_required(response, staging)
        os.replace(staging, target)
    print(f"Sherpa model ready: {target}", flush=True)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download the multilingual Sherpa Whisper tiny model")
    parser.parse_args()
    try:
        install()
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, f"Model setup failed: {exc}\n")
