"""Two-process/restart acceptance demo using synthetic source and state only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="eaon-continuity-demo-") as folder:
        db = Path(folder) / "continuity.db"
        source = Path(folder) / "decision.txt"
        source.write_text("Synthetic decision evidence: keep project state local.", encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC"}}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        def run(*args):
            result = subprocess.run([sys.executable, "-B", "-m", "eaon_kernel", "--db", str(db), *args],
                                    cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=20, check=True)
            return json.loads(result.stdout)
        run("init")
        run("project", "synthetic", "Continuity acceptance")
        run("goal", "synthetic", "g1", "Recover exact project state after restart")
        run("remember", "synthetic", "decision", "Keep project state local", "--status", "confirmed", "--source-file", str(source))
        run("unknown", "synthetic", "latency", "Hardware latency has not been measured")
        run("task", "synthetic", "t1", "Measure hardware latency")
        checkpoint = run("checkpoint", "synthetic")
        card = run("recover", "synthetic")
        assert card["memories"]["decision"]["text"] == "Keep project state local"
        assert card["memories"]["latency"]["status"] == "unknown"
        assert card["next_task"]["id"] == "t1"
        assert run("verify", "--expected-head", checkpoint["head"])["ok"]
        print(json.dumps({"ok": True, "separate_processes": True, "decision_recovered": True,
                          "unknown_preserved": True, "next_task": card["next_task"], "checkpoint_head": checkpoint["head"]}, indent=2))


if __name__ == "__main__":
    main()
