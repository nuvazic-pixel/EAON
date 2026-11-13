"""Launch only this installation's local UI with external adapters disabled."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from setup_local import MESSAGES, SetupError, local_environment, validate_environment


def launch_command(root, python, port=8501):
    return [str(python), "-I", "-m", "streamlit", "run", str(Path(root) / "ui/app.py"),
            "--server.address", "127.0.0.1", "--server.port", str(port),
            "--browser.gatherUsageStats", "false", "--server.fileWatcherType", "none"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--check-only", action="store_true", help="Validate installation only; do not start the UI")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    try:
        python = validate_environment(ROOT)
        result = subprocess.run([str(python), "-I", str(ROOT / "scripts/doctor_local.py"), "--offline"],
                                cwd=ROOT, env=local_environment(), capture_output=True, text=True, check=False)
        readiness = json.loads(result.stdout)
        if type(readiness) is not dict:
            raise ValueError("invalid_doctor_response")
        if result.returncode or not readiness.get("installation_ready"):
            print("Dependențele locale lipsesc sau nu au versiunile testate. Rulează Instaleaza-EAON.cmd.", file=sys.stderr)
            return 1
        if args.check_only:
            print(json.dumps(readiness, ensure_ascii=False, indent=2))
            return 0
        print(f"EAON pornește local la http://127.0.0.1:{args.port}. Închide această fereastră pentru oprire.", flush=True)
        print("Pentru răspunsuri, Ollama trebuie pornit cu modelele llama3 și mistral disponibile.", flush=True)
        return subprocess.run(launch_command(ROOT, python, args.port), cwd=ROOT,
                              env=local_environment(), check=False).returncode
    except SetupError as exc:
        print(MESSAGES.get(str(exc), "Mediul local nu este valid. Rulează Instaleaza-EAON.cmd."), file=sys.stderr)
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Nu pot porni mediul local. Rulează Instaleaza-EAON.cmd pentru verificare.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
