"""Explicit local commands; no automatic migration of existing stores."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from . import ContinuityKernel, IntegrityError, SourceRef, ValidationError


def main(argv=None):
    parser = argparse.ArgumentParser(description="EAON continuity kernel v0.1")
    parser.add_argument("--db", required=True, help="Explicit SQLite continuity database path")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    project = commands.add_parser("project")
    project.add_argument("project_id")
    project.add_argument("title")
    project.add_argument("--max-tasks", type=int, default=8)
    project.add_argument("--owner", default="local")
    goal = commands.add_parser("goal")
    goal.add_argument("project_id")
    goal.add_argument("goal_id", nargs="?")
    goal.add_argument("text", nargs="?")
    goal.add_argument("--close", action="store_true")
    task = commands.add_parser("task")
    task.add_argument("project_id")
    task.add_argument("task_id")
    task.add_argument("text", nargs="?")
    task.add_argument("--complete", action="store_true")
    for name in ("remember", "unknown"):
        memory = commands.add_parser(name)
        memory.add_argument("project_id")
        memory.add_argument("key")
        memory.add_argument("text")
        memory.add_argument("--expected-revision", type=int)
        memory.add_argument("--kind", choices=("profile", "episodic", "task", "skill", "evidence"))
        if name == "remember":
            memory.add_argument("--status", choices=("hypothesis", "confirmed"), default="hypothesis")
            memory.add_argument("--source-file", type=Path, action="append", default=[])
    for name in ("recover", "checkpoint"):
        commands.add_parser(name).add_argument("project_id")
    verify = commands.add_parser("verify")
    verify.add_argument("--expected-head")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("project_id")
    revoke.add_argument("key")
    revoke.add_argument("reason")
    revoke.add_argument("--expected-revision", type=int, required=True)
    context = commands.add_parser("context")
    context.add_argument("project_id")
    context.add_argument("query")
    context.add_argument("--synapse-url")
    context.add_argument("--collection-id")
    context.add_argument("--token-env", default="SYNAPSE_TOKEN")
    context.add_argument("--budget-chars", type=int, default=12000)
    context.add_argument("--require-source", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        kernel = ContinuityKernel.create(args.db) if args.command == "init" else ContinuityKernel(args.db)
        if args.command == "init":
            result = kernel.verify()
        elif args.command == "project":
            result = kernel.create_project(args.project_id, args.title, args.max_tasks, owner_id=args.owner)
        elif args.command == "goal":
            if not args.close and (args.goal_id is None or args.text is None):
                raise ValidationError("goal requires an ID and text, or --close")
            result = kernel.close_goal(args.project_id) if args.close else kernel.set_goal(args.project_id, args.goal_id, args.text)
        elif args.command == "task":
            if not args.complete and args.text is None:
                raise ValidationError("task requires text, or --complete")
            result = kernel.complete_task(args.project_id, args.task_id) if args.complete else kernel.add_task(args.project_id, args.task_id, args.text)
        elif args.command in {"remember", "unknown"}:
            sources = []
            for path in getattr(args, "source_file", []):
                content = path.read_text(encoding="utf-8")
                sources.append(SourceRef(str(path.resolve()), path.resolve().as_uri(), content, sha256(content.encode()).hexdigest()))
            key = args.kind + ":" + args.key if args.kind else args.key
            result = kernel.record_memory(args.project_id, key, args.text,
                       status="unknown" if args.command == "unknown" else args.status,
                       sources=tuple(sources), expected_revision=args.expected_revision)
        elif args.command == "recover":
            result = kernel.recover(args.project_id)
        elif args.command == "checkpoint":
            result = kernel.checkpoint(args.project_id)
        elif args.command == "revoke":
            result = kernel.revoke_memory(args.project_id, args.key, args.expected_revision, args.reason)
        elif args.command == "context":
            from .memory import KernelMemoryProvider, MemoryProviderRegistry, MemoryScope
            from .synapse import SynapseEvidenceProvider
            card = kernel.context_card(args.project_id)
            scope = MemoryScope(card["owner_id"], args.project_id, collection_id=args.collection_id)
            provider = (SynapseEvidenceProvider(args.synapse_url, os.environ.get(args.token_env, ""), scope.owner_id)
                        if args.synapse_url else KernelMemoryProvider(kernel, "evidence", scope.owner_id))
            registry = MemoryProviderRegistry()
            registry.register("evidence", provider)
            result = {"project": card, "evidence": registry.query("evidence", args.query, scope,
                      budget_chars=args.budget_chars, required_source_ids=tuple(args.require_source)),
                      "authorization": "none; context is data for review/reasoning"}
        else:
            result = kernel.verify(args.expected_head)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValidationError, IntegrityError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
