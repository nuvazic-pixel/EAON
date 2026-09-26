"""Launch the local EAON chat UI on loopback only."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    if sys.version_info < (3, 12):
        raise SystemExit("Use Python 3.12: py -3.12 -m venv .venv")
    try:
        import streamlit  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Install voice dependencies first: pip install -r requirements-voice.txt") from exc
    raise SystemExit(subprocess.call([
        sys.executable, "-m", "streamlit", "run", str(ROOT / "ui" / "app.py"),
        "--server.address", "127.0.0.1", "--server.port", "8501",
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none",
    ], cwd=ROOT))
