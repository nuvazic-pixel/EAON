"""Exercise the real CLI argument-to-context-to-local-model path."""
from io import StringIO
from unittest.mock import patch

import main
from core.telemetry import TelemetryRecorder
from eaon_kernel import ContinuityKernel


def test_cli_delivers_verified_context_without_adapters_or_journal_writes(tmp_path):
    kernel = ContinuityKernel.create(tmp_path / "fixture.db")
    kernel.create_project("p", "CLI fixture")
    kernel.record_memory("p", "unknown", "Measurement pending", status="unknown")
    before = kernel.verify()
    argv = ["main.py", "--project-db", str(kernel.path), "--project-id", "p", "--prompt", "Salut"]
    with patch("sys.argv", argv), patch("main.setup_logging"), patch("sys.stdout", new_callable=StringIO) as output, \
         patch("core.orchestrator.TelemetryRecorder", return_value=TelemetryRecorder(tmp_path / "telemetry.jsonl")), \
         patch("core.orchestrator.Orchestrator._enrich_intel") as intel, \
         patch("core.orchestrator.Orchestrator._post_process") as notifications, \
         patch("core.ollama_client._request", return_value={"message": {"content": "Synthetic CLI answer"}}) as model:
        assert main.main() == 0
        assert "Synthetic CLI answer" in output.getvalue()
    messages = model.call_args.args[1]["messages"]
    assert '"status":"unknown"' in messages[-2]["content"]
    assert messages[-1]["content"] == "Salut"
    intel.assert_not_called()
    notifications.assert_not_called()
    assert kernel.verify() == before


def test_cli_missing_store_fails_without_inference_or_path_in_error(tmp_path):
    private_path = tmp_path / "PRIVATE_STORE_NAME.db"
    argv = ["main.py", "--project-db", str(private_path), "--project-id", "p", "--prompt", "Salut"]
    with patch("sys.argv", argv), patch("main.setup_logging"), \
         patch("sys.stderr", new_callable=StringIO) as error, patch("core.ollama_client._request") as model:
        assert main.main() == 1
        assert "context_integrity_failed" in error.getvalue()
        assert "PRIVATE_STORE_NAME" not in error.getvalue()
    model.assert_not_called()
    assert not private_path.exists()


def test_memory_delivery_never_claims_citation_or_benefit(tmp_path):
    from core.orchestrator import Orchestrator
    from core.project_context import ProjectContext
    kernel = ContinuityKernel.create(tmp_path / "fixture.db")
    kernel.create_project("p", "Memory-use fixture")
    orchestrator = Orchestrator(local_only=True, context_session=ProjectContext(kernel.path, "p"),
                                telemetry=TelemetryRecorder(tmp_path / "telemetry.jsonl"))
    with patch("core.ollama_client._request", return_value={"message": {"content": "Synthetic answer"}}):
        _, report = orchestrator.run("Salut")
    audit = report.context_summary["memory_use"]
    assert audit["memory_delivered"] is True
    assert all(audit[key] is None for key in ("memory_cited", "memory_changed_decision", "memory_effect", "memory_redundant"))
    with patch("core.ollama_client._request", side_effect=RuntimeError("private transport detail")):
        _, failed = orchestrator.run("Salut")
    assert failed.context_summary["memory_use"]["memory_delivered"] is None
