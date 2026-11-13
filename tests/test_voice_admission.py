from unittest.mock import patch
from core.orchestrator import Orchestrator
from core.project_context import ProjectContext
from core.telemetry import TelemetryRecorder
from core.voice_state import TranscriptDraft, commit_transcript
from eaon_kernel import ContinuityKernel


def test_partial_voice_is_blocked_before_retrieval_model_or_external_paths(tmp_path):
    kernel = ContinuityKernel.create(tmp_path / "voice.db")
    kernel.create_project("p", "voice fixture")
    context = ProjectContext(kernel.path, "p")
    orch = Orchestrator(local_only=True, context_session=context, telemetry=TelemetryRecorder(tmp_path / "events.jsonl"))
    draft = TranscriptDraft("security attack", 2)
    with patch.object(context, "prepare") as retrieval, patch("core.ollama_client._request") as model, \
         patch.object(orch, "_post_process") as external:
        _, report = orch.run(draft.prefetch_query, source="voice", voice_commit=draft)
    assert not report.ok and report.error == "voice_uncommitted"
    assert report.output_text is None and report.final_output_origin is None
    retrieval.assert_not_called()
    model.assert_not_called()
    external.assert_not_called()


def test_committed_text_binding_is_checked_and_valid_commit_can_reach_model(tmp_path):
    orch = Orchestrator(local_only=True, telemetry=TelemetryRecorder(tmp_path / "events.jsonl"))
    committed = commit_transcript(TranscriptDraft("Salut", 1, final=True), reviewed_text="Salut corectat",
                                 user_confirmed=True, activation="explicit_submit", arguments_stable=True)
    with patch("core.ollama_client._request", return_value={"message": {"content": "Actual fixture response"}}) as model:
        _, invalid = orch.run("Different input", source="voice", voice_commit=committed)
        assert not invalid.ok and invalid.error == "voice_uncommitted"
        model.assert_not_called()
        _, valid = orch.run_voice(committed)
    assert valid.ok and valid.final_output_origin["origin"] == "ollama:llama3"
    assert model.call_args.args[1]["messages"][-1]["content"] == "Salut corectat"
