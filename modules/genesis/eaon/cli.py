from __future__ import annotations

import argparse
import json
from typing import Any

from eaon.orchestrator import EAONOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EAON Genesis v0.2 SELF")
    parser.add_argument("--memory", default="./data/memory.jsonl", help="Path to local JSONL memory.")
    parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Print raw JSON.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    think = subparsers.add_parser("think", help="Run the EAON SELF loop.")
    think.add_argument("text", help="Input thought, question, decision, risk, or idea.")
    think.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Print raw JSON.")

    remember = subparsers.add_parser("remember", help="Append a manual memory.")
    remember.add_argument("text")
    remember.add_argument("--kind", default="note")
    remember.add_argument("--tag", action="append", default=[])
    remember.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Print raw JSON.")

    recall = subparsers.add_parser("recall", help="Search memory.")
    recall.add_argument("query")
    recall.add_argument("--limit", type=int, default=5)
    recall.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Print raw JSON.")

    snapshot = subparsers.add_parser("snapshot", help="Show recent memory records.")
    snapshot.add_argument("--limit", type=int, default=10)
    snapshot.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Print raw JSON.")

    verify = subparsers.add_parser("verify", help="Verify memory hash chain.")
    verify.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Print raw JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    orchestrator = EAONOrchestrator(args.memory)
    raw_json = bool(getattr(args, "json", False))

    if args.command == "think":
        result = orchestrator.think(args.text)
        print_result(result, raw_json=raw_json)
        return 0

    if args.command == "remember":
        result = orchestrator.remember(args.text, kind=args.kind, tags=args.tag or ["manual"])
        print_result(result, raw_json=raw_json)
        return 0

    if args.command == "recall":
        result = orchestrator.recall(args.query, limit=args.limit)
        print_result(result, raw_json=raw_json)
        return 0

    if args.command == "snapshot":
        result = orchestrator.snapshot(limit=args.limit)
        print_result(result, raw_json=raw_json)
        return 0

    if args.command == "verify":
        result = orchestrator.verify_memory()
        print_result(result, raw_json=raw_json)
        return 0 if result["ok"] else 1

    raise ValueError(f"Unknown command: {args.command}")


def print_result(result: Any, *, raw_json: bool) -> None:
    if raw_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if isinstance(result, dict) and "council" in result:
        council = result["council"]
        route = result["route"]
        print(f"EAON route: {route['label']} ({route['score']:.2f})")
        print()
        print("Architect:")
        print(council["architect"])
        print()
        print("Skeptic:")
        print(council["skeptic"])
        print()
        print("Implementer:")
        print(council["implementer"])
        print()
        print("Judge:")
        print(council["judge"])
        print()
        print("Next step:")
        print(council["next_step"])
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
