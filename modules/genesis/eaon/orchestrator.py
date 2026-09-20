from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from eaon.agents import Council
from eaon.memory import MemoryStore
from eaon.reality_debugger import RealityDebugger
from eaon.router import Router


class EAONOrchestrator:
    def __init__(self, memory_path: str | Path = "./data/memory.jsonl") -> None:
        self.memory = MemoryStore(memory_path)
        self.router = Router()
        self.debugger = RealityDebugger()
        self.council = Council()

    def think(self, user_input: str) -> dict[str, Any]:
        run_id = f"run_{uuid4().hex}"
        route = self.router.classify(user_input)
        memories = self.memory.search(user_input, limit=5)
        debug_report = self.debugger.analyze(user_input)
        council = self.council.respond(
            user_input=user_input,
            route=route,
            debug_report=debug_report,
            memories=memories,
        )

        input_record = self.memory.append(
            kind="input",
            text=user_input,
            tags=["eaon", route.label],
            metadata={"run_id": run_id, "route": route.__dict__},
        )
        output_record = self.memory.append(
            kind="synthesis",
            text=council.judge + " Next step: " + council.next_step,
            tags=["eaon", "synthesis", route.label],
            metadata={
                "run_id": run_id,
                "route": route.__dict__,
                "debug_report": debug_report.to_dict(),
                "council": council.to_dict(),
                "source_memory_ids": [record.id for record in memories],
            },
        )

        return {
            "run_id": run_id,
            "route": route.__dict__,
            "debug_report": debug_report.to_dict(),
            "memories": [record.to_dict() for record in memories],
            "council": council.to_dict(),
            "saved_records": [input_record.to_dict(), output_record.to_dict()],
        }

    def remember(self, text: str, *, kind: str = "note", tags: list[str] | None = None) -> dict[str, Any]:
        record = self.memory.append(kind=kind, text=text, tags=tags or ["manual"])
        return record.to_dict()

    def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.memory.search(query, limit=limit)]

    def snapshot(self, limit: int = 10) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.memory.snapshot(limit=limit)]

    def verify_memory(self) -> dict[str, Any]:
        ok, errors = self.memory.verify_chain()
        return {"ok": ok, "errors": errors}

    @staticmethod
    def as_json(data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)
