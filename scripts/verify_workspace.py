"""Run offline verification in separate processes and import roots.

Install the existing requirements-verify.txt in a dedicated environment first.
No dependencies, services or models are installed or started by this command.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Suite:
    key: str
    label: str
    folder: str
    import_root: str
    dependencies: tuple[str, ...] = ("pytest",)
    tests: str = "tests"
    startup: bool = False


def suites() -> tuple[Suite, ...]:
    selected = [
        Suite("verifier", "Offline verifier guards", ".", "scripts",
              tests="scripts/test_verify_workspace.py"),
        Suite("root", "Root (ingestion, gateway, UI, CIE and governance)", ".", ".",
              ("pytest", "requests", "structlog", "numpy")),
        Suite("genesis", "Genesis SELF", "modules/genesis", "."),
        Suite("local-first", "Local-first memory", "modules/local_first", "src"),
        Suite("voice", "Voice harness", "benchmarks/voice", "src"),
        Suite("metabench", "MetaBench", "benchmarks/metabench", "src"),
        Suite("twin", "Cognitive Twin helpers", "modules/cognitive_twin", ".",
              ("pytest", "pgvector", "psycopg", "sqlalchemy", "pydantic_settings")),
        Suite("bhidt", "BHIDT verification", "integrations/bhidt", "."),
    ]
    if (ROOT / "modules/biolab/tests").is_dir():
        selected.append(Suite("biolab", "BioLab M0", "modules/biolab", "src"))
    selected.append(Suite("startup", "INTEL CLI startup", ".", ".",
                          ("requests", "structlog"), startup=True))
    return tuple(selected)


def clean_environment(home: Path) -> dict[str, str]:
    """Pass OS essentials only: never inherit keys, endpoints or Python options."""
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATHEXT",
               "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "LANG", "LC_ALL"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update({
        "HOME": str(home), "USERPROFILE": str(home),
        "APPDATA": str(home / "appdata"), "LOCALAPPDATA": str(home / "localappdata"),
        "XDG_CONFIG_HOME": str(home / "config"), "XDG_CACHE_HOME": str(home / "cache"),
        "TEMP": str(home), "TMP": str(home), "TMPDIR": str(home),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHON_DOTENV_DISABLED": "1",
        "INTEL_ENABLED": "false", "REDIS_ENABLED": "false",
        "SLACK_ENABLED": "false", "JIRA_ENABLED": "false",
        "LOG_LEVEL": "ERROR", "LOG_FILE": "", "NO_COLOR": "1",
    })
    return env


def run_suite(suite: Suite, reports: Path, dependency_paths: list[Path]) -> dict:
    result_path = reports / f"{suite.key}.json"
    if result_path.exists():
        result_path.unlink()
    with tempfile.TemporaryDirectory(prefix=f"eaon-{suite.key}-") as temporary:
        command = [sys.executable, "-I", "-B", "-X", "utf8",
                   str(ROOT / "scripts/_verify_runner.py"), suite.key, str(result_path),
                   *(str(path) for path in dependency_paths)]
        try:
            completed = subprocess.run(
                command, cwd=ROOT / suite.folder,
                env=clean_environment(Path(temporary)), timeout=120,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            (reports / f"{suite.key}.log").write_text(
                completed.stdout + completed.stderr, encoding="utf-8")
            print(completed.stdout, end="", flush=True)
            print(completed.stderr, end="", file=sys.stderr, flush=True)
            result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {
                "suite": suite.key, "label": suite.label, "status": "RUNNER_ERROR",
                "detail": "Child process produced no result report.",
            }
            if completed.returncode and result["status"] == "PASS":
                result.update(status="RUNNER_ERROR", detail="Child exited nonzero after reporting PASS.")
            result["exit_code"] = completed.returncode
            return result
        except subprocess.TimeoutExpired:
            return {"suite": suite.key, "label": suite.label, "status": "TIMEOUT",
                    "detail": "Exceeded 120-second suite limit.", "exit_code": 124}


def main(argv: list[str] | None = None) -> int:
    available = {suite.key: suite for suite in suites()}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", action="append", choices=available,
                        help="run a selected suite; repeat to select several (default: all)")
    parser.add_argument("--list", action="store_true", help="list discovered suites without running them")
    parser.add_argument("--report-dir", type=Path,
                        help="keep per-suite JSON/log/JUnit reports and summary.json here")
    parser.add_argument("--dependency-path", action="append", type=Path, default=[],
                        help="explicit existing site-packages directory (no .pth execution); prefer a venv")
    args = parser.parse_args(argv)
    dependency_paths = [path.resolve() for path in args.dependency_path]
    if any(not path.is_dir() for path in dependency_paths):
        parser.error("every --dependency-path must be an existing directory")
    if args.list:
        for suite in available.values():
            print(f"{suite.key}: {suite.label} [{suite.folder}; import {suite.import_root}]")
        return 0
    selected = [available[key] for key in dict.fromkeys(args.suite or available)]
    with tempfile.TemporaryDirectory(prefix="eaon-verification-") as temporary:
        reports = (args.report_dir or Path(temporary)).resolve()
        reports.mkdir(parents=True, exist_ok=True)
        results = []
        for suite in selected:
            print(f"\n=== {suite.label} ===", flush=True)
            results.append(run_suite(suite, reports, dependency_paths))
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(), "platform": sys.platform,
            "offline": True, "results": results,
            "status": "PASS" if all(result["status"] == "PASS" for result in results) else "FAIL",
        }
        (reports / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print("\nSuite | Status | Collected | Passed | Failed | Errors | Skipped | Subtests", flush=True)
        for result in results:
            counts = result.get("counts", {})
            values = [str(counts.get(key, "-")) for key in
                      ("collected", "passed", "failed", "errors", "skipped", "subtests")]
            print(" | ".join([result["suite"], result["status"], *values]))
            if result.get("detail"):
                print(f"  {result['detail']}")
        if args.report_dir:
            print(f"Reports: {reports}")
        print(f"Overall: {summary['status']}. Hardware, model quality and live services were not tested.")
        return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
