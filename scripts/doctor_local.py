"""Read-only local readiness report. Never load .env, pull models or run inference."""
from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_PACKAGES = {"python-dotenv": "1.2.3", "requests": "2.34.2", "structlog": "26.1.0", "streamlit": "1.64.0"}
VOICE_PACKAGES = {"sherpa-onnx": "1.13.8", "numpy": "2.5.3"}
REQUIRED_MODELS = ("llama3", "mistral")
MODEL_FOLDER = "sherpa-onnx-whisper-tiny"
MODEL_PARTS = ("tiny-encoder.int8.onnx", "tiny-decoder.int8.onnx", "tiny-tokens.txt")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def dependency_report(*, voice=False):
    expected = {**DESKTOP_PACKAGES, **(VOICE_PACKAGES if voice else {})}
    results = []
    for name, required in expected.items():
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        results.append({"package": name, "required": required, "installed": installed, "ok": installed == required})
    return results


def ollama_report(*, offline=False):
    result = {"checked": not offline, "reachable": None, "required_models": list(REQUIRED_MODELS), "missing_models": None}
    if offline:
        return result
    try:
        request = Request("http://127.0.0.1:11434/api/tags", headers={"Accept": "application/json"}, method="GET")
        opener = build_opener(ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=3) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("oversized_response")
        data = json.loads(raw)
        models = data.get("models") if type(data) is dict else None
        if type(models) is not list or len(models) > 1000:
            raise ValueError("invalid_response")
        names = {item["name"] for item in models if type(item) is dict and type(item.get("name")) is str}
        result.update(reachable=True, missing_models=[model for model in REQUIRED_MODELS
                      if model not in names and model + ":latest" not in names])
    except HTTPError:
        result.update(reachable=False, error="ollama_http_error")
    except (URLError, OSError, ValueError):
        result.update(reachable=False, error="ollama_unavailable_or_invalid")
    return result


def report(*, root=ROOT, offline=False, voice=False):
    root = Path(root).resolve()
    version_ok = sys.version_info[:2] == (3, 12)
    venv_ok = sys.prefix != sys.base_prefix and Path(sys.prefix).resolve() == (root / ".venv").resolve()
    dependencies = dependency_report(voice=voice)
    installation_ready = version_ok and venv_ok and all(item["ok"] for item in dependencies)
    ollama = ollama_report(offline=offline)
    inference_ready = (installation_ready and ollama["reachable"] is True and not ollama["missing_models"]) if not offline else None
    model_ready = all((root / "models" / MODEL_FOLDER / part).is_file() for part in MODEL_PARTS)
    return {"schema": "eaon.local-readiness.v1", "python": {"required": "3.12", "actual": ".".join(map(str, sys.version_info[:3])),
            "ok": version_ok, "project_environment": venv_ok}, "dependencies": dependencies,
            "installation_ready": installation_ready, "inference_ready": inference_ready,
            "ollama": ollama, "voice": {"requested": voice, "model_files_ready": model_ready},
            "ready": installation_ready and (inference_ready is True) and (not voice or model_ready)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", "--no-network", action="store_true", help="Do not contact even local Ollama")
    parser.add_argument("--voice", action="store_true", help="Also require installed voice packages/model files")
    args = parser.parse_args(argv)
    result = report(offline=args.offline, voice=args.voice)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    passed = (result["installation_ready"] and (not args.voice or result["voice"]["model_files_ready"])) if args.offline else result["ready"]
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
