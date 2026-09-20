from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import CommandAdapter, MockAdapter
from .journal import verify
from .runner import run_benchmark


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="eaon-c3")
    commands = parser.add_subparsers(dest="action", required=True)
    run = commands.add_parser("run", help="run a manifest")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--adapter", choices=("mock", "command"), default="mock")
    run.add_argument("--command", help="adapter command template")
    check = commands.add_parser("verify", help="verify journal hash chain")
    check.add_argument("journal", type=Path)
    args = parser.parse_args(argv)
    if args.action == "verify":
        valid, records, error = verify(args.journal)
        print(json.dumps({"valid": valid, "records": records, "error": error}))
        return 0 if valid else 2
    if args.adapter == "command" and not args.command:
        parser.error("--command is required for the command adapter")
    factory = ((lambda language: MockAdapter()) if args.adapter == "mock" else
               (lambda language: CommandAdapter(args.command, language)))
    report = run_benchmark(args.manifest, args.output, factory)
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
