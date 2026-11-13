"""Reachable synthetic counterevidence quarantines state before model/tool use."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.orchestrator import Orchestrator
from core.project_context import ProjectContext
from core.telemetry import TelemetryRecorder
from eaon_kernel import ContinuityKernel
from eaon_kernel.cards import FactClaim, MemoryCard
from eaon_kernel.contracts import SourceRef


def card(value):
    body = "Synthetic raw trace: fixture resource is " + value + "."
    source = SourceRef("trace-" + value, "fixture://reachability/" + value, body, sha256(body.encode()).hexdigest())
    return MemoryCard("Fixture resource is " + value, source, (0, len(body)), "succeeded",
                      "synthetic-reviewer", FactClaim("fixture-resource", "availability", value))


def main():
    with tempfile.TemporaryDirectory(prefix="eaon-counterevidence-") as folder:
        kernel = ContinuityKernel.create(Path(folder) / "fixture.db")
        kernel.create_project("p", "Synthetic evidence reachability")
        kernel.record_memory_card("p", "evidence:resource", card("available"), status="confirmed")
        # The first declared claim is deliberately false in this fixture.
        kernel.report_counterevidence("p", "evidence:resource", card("absent"), 1, "synthetic-fault-origin")
        orchestrator = Orchestrator(local_only=True, context_session=ProjectContext(kernel.path, "p"),
                                    telemetry=TelemetryRecorder(Path(folder) / "telemetry.jsonl"))
        before = kernel.verify()
        with patch("core.ollama_client._request") as model, \
             patch.object(orchestrator, "_enrich_intel") as intel, \
             patch.object(orchestrator, "_post_process") as tools:
            _, report = orchestrator.run("Use the fixture resource", source="text")
        assert not report.ok and report.error == "context_state_contaminated" and report.output_text is None
        assert model.call_count == intel.call_count == tools.call_count == 0
        assert kernel.verify() == before
        contaminated = kernel.recover("p")["memories"]["evidence:resource"]
        assert contaminated["incident"]["state_contaminated"]
        kernel.restore_memory_card("p", "evidence:resource", card("absent"), 2,
                                  "Synthetic human review accepted the countertrace", status="confirmed")
        restored = ContinuityKernel(kernel.path).recover("p")["memories"]["evidence:resource"]
        assert restored["incident"]["state_restored"] and not restored["incident"]["state_contaminated"]
        assert not kernel.context_card("p")["blocked_memories"]
        context = json.loads(ProjectContext(kernel.path, "p").prepare("resource state").serialized)
        assert context["project"]["memories"]["evidence:resource"]["card"]["claim"]["value"] == "absent"
        print(json.dumps({"ok": True, "mode": "synthetic typed-claim counterevidence",
            "quarantined": True, "blocked_model_calls": model.call_count, "blocked_tool_calls": tools.call_count,
            "blocked_final_output": report.output_text, "state_restored": restored["incident"]["state_restored"],
            "final_output_origin": restored["incident"]["final_output_origin"],
            "limits": "typed explicit claims only; no semantic contradiction detector or real tool execution"}, indent=2))


if __name__ == "__main__":
    main()
