"""Private child runner for verify_workspace.py; guards apply before app imports."""
from __future__ import annotations

from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys


class OfflineViolation(RuntimeError):
    """Unexpected I/O during offline verification (not a simulated service error)."""


def install_guards() -> list[str]:
    """Reject socket use, process launches and dotenv-file reads.

    An attempt also fails the final result if application code catches the error.
    This is a Python process guard, not an OS sandbox for arbitrary native code.
    """
    violations: list[str] = []

    def audit(event: str, args: tuple) -> None:
        reason = None
        if event.startswith("socket.") and event != "socket.gethostname":
            reason = "socket I/O"
        elif event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.exec"}:
            reason = "child process launch"
        elif event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            name = Path(os.fsdecode(args[0])).name.lower()
            if name == ".env" or (name.startswith(".env.") and not name.endswith(".example")):
                reason = "dotenv file access"
        if reason:
            violations.append(reason + ": " + event)
            raise OfflineViolation(f"Offline verification blocked {reason}")

    sys.addaudithook(audit)
    return violations


class Results:
    def __init__(self) -> None:
        self.items: dict[str, str] = {}
        self.collection_errors = 0
        self.subtests = 0
        self.subtest_failures = 0

    def pytest_collection_finish(self, session) -> None:
        self.items = {item.nodeid: "not_run" for item in session.items}

    def pytest_collectreport(self, report) -> None:
        if report.failed:
            self.collection_errors += 1

    def pytest_runtest_logreport(self, report) -> None:
        if hasattr(report, "context"):
            self.subtests += 1
            self.subtest_failures += int(report.failed)
            return
        prior = self.items.get(report.nodeid, "not_run")
        if report.failed:
            self.items[report.nodeid] = "failed" if report.when == "call" else "errors"
        elif prior not in {"failed", "errors"}:
            if report.skipped:
                self.items[report.nodeid] = "skipped"
            elif report.when == "call":
                self.items[report.nodeid] = "passed"

    def counts(self) -> dict[str, int]:
        return {
            "collected": len(self.items),
            **{key: sum(value == key for value in self.items.values())
               for key in ("passed", "failed", "skipped", "not_run")},
            "errors": self.collection_errors + sum(value == "errors" for value in self.items.values()),
            "subtests": self.subtests, "subtest_failures": self.subtest_failures,
        }


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verify_workspace import ROOT, suites

    suite_key, output, *dependency_paths = sys.argv[1:]
    # Explicit dependency dirs are added as paths, never processed as site .pth files.
    sys.path.extend(dependency_paths)
    suite = next(item for item in suites() if item.key == suite_key)
    result_path = Path(output)
    result = {"suite": suite.key, "label": suite.label, "status": "RUNNER_ERROR"}
    if suite.key in {"root", "startup"}:
        # urllib3 probes IPv6 by binding a loopback socket at import. These
        # suites test mocked transports, not host IPv6 capability.
        import socket
        socket.has_ipv6 = False
        result["fixtures"] = ["urllib3 IPv6 capability probe disabled"]
    violations = install_guards()
    code = 1
    try:
        missing = [name for name in suite.dependencies if importlib.util.find_spec(name) is None]
        if missing:
            result.update(status="DEPENDENCY_ERROR", detail="Missing dependencies: " + ", ".join(missing))
            return 3
        sys.path.insert(0, str((ROOT / suite.folder / suite.import_root).resolve()))
        if suite.startup:
            sys.argv = [str(ROOT / "main.py"), "--stats"]
            try:
                runpy.run_path(str(ROOT / "main.py"), run_name="__main__")
                code = 0
            except SystemExit as exc:
                code = 0 if exc.code is None else exc.code if isinstance(exc.code, int) else 1
            result.update(status="PASS" if code == 0 else "FAIL", counts={"checks": 1})
        else:
            import pytest
            plugin = Results()
            with ExitStack() as stack:
                if suite.key == "bhidt":
                    from unittest.mock import patch
                    stack.enter_context(patch("platform.system", return_value=sys.platform))
                    stack.enter_context(patch("platform.machine", return_value="offline-test-fixture"))
                    result["fixtures"] = ["Static platform fingerprint metadata; no OS subprocess probe"]
                if suite.key == "local-first":
                    import urllib.error
                    from unittest.mock import patch
                    stack.enter_context(patch("eaon.router.urllib.request.urlopen", side_effect=
                                              urllib.error.URLError("offline fixture: Ollama unavailable")))
                    result["fixtures"] = ["Ollama unavailable (urlopen raises URLError)"]
                code = int(pytest.main([
                    "-q", "-o", "addopts=", "-o", "cache_dir=" + str(Path(os.environ["TEMP"]) / "pytest"),
                    "--confcutdir=" + str(ROOT / suite.folder),
                    suite.tests,
                ], plugins=[plugin]))
            result.update(status="PASS" if code == 0 else "FAIL", counts=plugin.counts())
        return code
    except Exception as exc:
        result.update(status="RUNNER_ERROR", detail=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if violations:
            result.update(status="OFFLINE_VIOLATION", violations=violations,
                          detail="Unexpected I/O attempt; caught exceptions do not make this a pass.")
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
