"""Project-state admission before the experimental, inert mock workflow runner."""
from eaon_kernel import IntegrityError, ValidationError
from eaon_workflows import Outcome, RunReport, run_workflow
from .voice_state import CommittedTranscript, VoiceStateError


def run_project_workflow(kernel, project_id, workflow, registry, facts, environment_sha256, *, voice_commit=None):
    if voice_commit is not None:
        try:
            if type(voice_commit) is not CommittedTranscript:
                raise VoiceStateError("voice_uncommitted")
            voice_commit.validate()
        except VoiceStateError:
            return RunReport(Outcome.BLOCKED_BY_POLICY, "voice_uncommitted")
    try:
        card = kernel.context_card(project_id)
        if card.get("blocked_memories"):
            return RunReport(Outcome.BLOCKED_BY_POLICY, "state_contaminated")
    except (IntegrityError, ValidationError, OSError):
        return RunReport(Outcome.BLOCKED_BY_POLICY, "project_state_unverifiable")
    # No effectful tool implementation is accepted by run_workflow.
    result = run_workflow(workflow, registry, facts, environment_sha256)
    try:
        if kernel.verify()["head"] != card["journal_head"]:
            return RunReport(Outcome.BLOCKED_BY_POLICY, "project_changed_during_mock_run", result.observations)
    except (IntegrityError, OSError):
        return RunReport(Outcome.BLOCKED_BY_POLICY, "project_changed_during_mock_run", result.observations)
    return result
