from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from eaon.memory import MemoryStore
from eaon.orchestrator import EAONOrchestrator
from eaon.reality_debugger import RealityDebugger
from eaon.router import Router


class EAONTests(unittest.TestCase):
    def test_memory_appends_and_verifies_hash_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp) / "memory.jsonl")
            first = store.append(kind="note", text="EAON remembers local ideas.", tags=["eaon"])
            second = store.append(kind="note", text="Reality Debugger checks assumptions.", tags=["debugger"])

            self.assertEqual(first.previous_hash, "GENESIS")
            self.assertEqual(second.previous_hash, first.content_hash)
            ok, errors = store.verify_chain()
            self.assertTrue(ok, errors)

    def test_search_returns_relevant_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp) / "memory.jsonl")
            store.append(kind="note", text="EAON uses local JSONL memory.", tags=["eaon"])
            store.append(kind="note", text="Unrelated note about lunch.", tags=["food"])

            results = store.search("local memory")
            self.assertEqual(results[0].kind, "note")
            self.assertIn("JSONL", results[0].text)

    def test_router_classifies_idea(self) -> None:
        route = Router().classify("EAON should become my orchestration architecture.")
        self.assertEqual(route.label, "idea")
        self.assertGreater(route.score, 0.5)

    def test_reality_debugger_extracts_assumption_risk_and_test(self) -> None:
        report = RealityDebugger().analyze(
            "Cred ca EAON poate functiona. Riscul este sa fie prea mare. Verific cu un test mic."
        )
        kinds = {item.kind for item in report.items}
        self.assertIn("ASSUMPTION", kinds)
        self.assertIn("RISK", kinds)
        self.assertIn("TEST", kinds)

    def test_orchestrator_runs_and_saves_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            orchestrator = EAONOrchestrator(Path(tmp) / "memory.jsonl")
            result = orchestrator.think("Build EAON as a local orchestrator and test memory.")

            self.assertIn("route", result)
            self.assertIn("council", result)
            self.assertEqual(len(result["saved_records"]), 2)
            verify = orchestrator.verify_memory()
            self.assertTrue(verify["ok"], verify["errors"])


if __name__ == "__main__":
    unittest.main()
