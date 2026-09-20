from __future__ import annotations

import argparse
import json

from .core import EAON


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="eaon", description="EAON local-first prototype")
    root.add_argument("--db", default="data/eaon.db", help="SQLite memory path")
    root.add_argument("--model", default="qwen3:8b", help="Local Ollama model")
    commands = root.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="Ingest a local .txt, .md or .pdf")
    ingest.add_argument("path")
    ask = commands.add_parser("ask", help="Run evidence-grounded orchestration")
    ask.add_argument("goal")
    export = commands.add_parser("export", help="Export all local memory as JSON")
    export.add_argument("path")
    commands.add_parser("status", help="Show local status")
    return root


def main() -> None:
    args = parser().parse_args()
    eaon = EAON(args.db, args.model)
    if args.command == "ingest":
        output = eaon.ingest(args.path)
    elif args.command == "ask":
        output = eaon.run(args.goal).to_dict()
    elif args.command == "export":
        output = {"exported": str(eaon.export(args.path))}
    else:
        output = eaon.status()
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
