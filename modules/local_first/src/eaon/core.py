from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .ingest import ingest_file
from .memory import LocalMemory
from .models import RunResult
from .reality_debugger import RealityDebugger
from .router import LocalRouter


class EAON:
    def __init__(self, database: str | Path = "data/eaon.db", model: str = "qwen3:8b") -> None:
        self.memory = LocalMemory(database)
        self.router = LocalRouter(model=model)
        self.debugger = RealityDebugger()

    def ingest(self, path: str | Path) -> dict:
        return ingest_file(self.memory, path)

    def run(self, goal: str) -> RunResult:
        evidence = self.memory.search_claims(goal)
        check = self.debugger.inspect(goal, evidence)
        answer, route = self.router.generate(goal, [claim.evidence for claim in evidence])
        seed = f"{goal}:{datetime.now(timezone.utc).isoformat()}"
        run_id = hashlib.sha256(seed.encode()).hexdigest()[:16]
        result = RunResult(goal, answer, route, check, evidence, run_id)
        self.memory.save_run(run_id, goal, result.to_dict())
        return result

    def export(self, destination: str | Path) -> Path:
        return self.memory.export_json(destination)

    def status(self) -> dict:
        route = self.router.decide()
        return {
            "memory": self.memory.stats(),
            "route": {"backend": route.backend, "reason": route.reason, "private": route.private},
        }
