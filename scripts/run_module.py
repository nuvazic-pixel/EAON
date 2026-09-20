"""Launch a recovered EAON module in a separate Python process.

Run from any directory: python scripts/run_module.py genesis think "An idea"
Each historical package keeps its own import root and working directory.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "genesis": ("modules/genesis", ".", ["-m", "eaon.cli"]),
    "local-first": ("modules/local_first", "src", ["-m", "eaon.cli"]),
    "voice": ("benchmarks/voice", "src", ["-m", "eaon_c3"]),
    "metabench": ("benchmarks/metabench", "src", ["-m", "eaon_metabench.cli"]),
    "skills": ("modules/skills", ".", ["examples/run_router.py"]),
    "bhidt-demo": ("integrations/bhidt", ".", ["examples/verification_demo_v04.py"]),
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print("Usage: python scripts/run_module.py MODULE [arguments...]")
        print("Modules: " + ", ".join(MODULES))
        print("Relative data/output paths are resolved inside that module.")
        return 0
    if sys.argv[1] not in MODULES:
        print(f"Unknown module: {sys.argv[1]}", file=sys.stderr)
        return 2
    folder, import_root, command = MODULES[sys.argv[1]]
    cwd = ROOT / folder
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd / import_root)
    return subprocess.call([sys.executable, *command, *sys.argv[2:]], cwd=cwd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
