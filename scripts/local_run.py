"""Check EAON locally and optionally launch the original INTEL CLI.

The default path uses mocked voice data and disables external INTEL adapters.
It does not certify a microphone, Sherpa, OS network isolation or physical tools.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
VOICE = ROOT / "benchmarks" / "voice"
LOCAL_ENV = {
    "INTEL_ENABLED": "false",
    "REDIS_ENABLED": "false",
    "SLACK_ENABLED": "false",
    "JIRA_ENABLED": "false",
}


def run(args: list[str], *, cwd: Path = ROOT, import_root: Path = ROOT) -> None:
    env = os.environ.copy()
    env.update(LOCAL_ENV)
    env["PYTHONPATH"] = str(import_root)
    print("\n> " + " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], cwd=cwd, env=env, check=True)


def smoke() -> Path:
    run(["-m", "unittest", "discover", "-s", "tests", "-p", "test_gateway.py", "-q"])
    run(["-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=VOICE, import_root=VOICE / "src")
    run(["main.py", "--stats"])

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    relative_output = Path("runs") / f"local-{stamp}-{uuid.uuid4().hex[:8]}"
    run(["scripts/run_module.py", "voice", "run", "--manifest", "examples/manifest.csv",
         "--output", str(relative_output), "--adapter", "mock"])
    journal = relative_output / "state-journal.jsonl"
    run(["scripts/run_module.py", "voice", "verify", str(journal)])

    output = VOICE / relative_output
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    if report["summary"]["samples"] != 6:
        raise RuntimeError("unexpected sample count in local mock report")
    print(f"\nLocal mock PASS. Report: {output / 'report.json'}", flush=True)
    return output


def check_ollama(model: str) -> None:
    url = "http://127.0.0.1:11434/api/tags"
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=3) as response:
            data = json.load(response)
    except (OSError, ValueError) as exc:
        raise RuntimeError("Ollama is not available at 127.0.0.1:11434. "
                           "Start Ollama locally, then retry.") from exc
    installed = {item.get("name", "").split(":")[0]
                 for item in data.get("models", []) if isinstance(item, dict)}
    if model not in installed:
        raise RuntimeError(f"Ollama model '{model}' is missing. Run: ollama pull {model}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local EAON smoke and optional Ollama CLI")
    parser.add_argument("--all-tests", action="store_true",
                        help="run all isolated suites (requires requirements-verify.txt)")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--interactive", action="store_true",
                        help="run the original INTEL CLI after the smoke check")
    action.add_argument("--prompt", help="send one prompt to local Ollama after the smoke check")
    parser.add_argument("--mode", choices=("normal", "balanced", "safe", "lockdown"),
                        default="normal")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error("Python 3.11+ is required; use Python 3.12 for --all-tests")
    if args.all_tests and sys.version_info < (3, 12):
        parser.error("Python 3.12+ is required for --all-tests")
    if args.prompt is not None and not args.prompt.strip():
        parser.error("--prompt cannot be empty")
    try:
        smoke()
        if args.all_tests:
            run(["scripts/verify_workspace.py"])
        if args.interactive or args.prompt is not None:
            model = "mistral" if args.mode in {"safe", "lockdown"} else "llama3"
            check_ollama(model)
            command = ["main.py", "--mode", args.mode]
            if args.prompt is not None:
                command += ["--prompt", args.prompt]
            run(command)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"\nLocal run failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
