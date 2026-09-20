"""Run the existing EAON test suites with isolated import paths.

Install requirements-verify.txt first. This does not start model servers,
microphones, containers, external intelligence APIs, or notification adapters.
Local-first's existing test may probe the loopback Ollama endpoint.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUITES = (
    ("Knowledge ingestion", ".", "."),
    ("Genesis SELF", "modules/genesis", "."),
    ("Local-first memory", "modules/local_first", "src"),
    ("Voice harness", "benchmarks/voice", "src"),
    ("MetaBench", "benchmarks/metabench", "src"),
    ("Cognitive Twin helpers", "modules/cognitive_twin", "."),
    ("BHIDT verification", "integrations/bhidt", "."),
)


def main() -> int:
    failed = []
    for label, folder, import_root in SUITES:
        cwd = ROOT / folder
        env = os.environ.copy()
        env["PYTHONPATH"] = str(cwd / import_root)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        env.update(INTEL_ENABLED="false", REDIS_ENABLED="false",
                   SLACK_ENABLED="false", JIRA_ENABLED="false")
        print(f"\n{label}", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests"],
            cwd=cwd, env=env, timeout=120,
        )
        if result.returncode:
            failed.append(label)
    print("\nINTEL CLI startup", flush=True)
    env = os.environ.copy()
    env.update(INTEL_ENABLED="false", REDIS_ENABLED="false",
               SLACK_ENABLED="false", JIRA_ENABLED="false", PYTHONPATH=str(ROOT))
    startup = subprocess.run([sys.executable, "main.py", "--stats"],
                             cwd=ROOT, env=env, timeout=30)
    if startup.returncode:
        failed.append("INTEL CLI startup")
    if failed:
        print("Failed suites: " + ", ".join(failed), file=sys.stderr)
        return 1
    print("\nAll existing test suites passed. Hardware and live services were not tested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
