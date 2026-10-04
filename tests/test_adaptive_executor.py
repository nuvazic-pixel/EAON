from dataclasses import dataclass

from core.adaptive import TaskEnvelope
from core.adaptive_executor import UnifiedAdaptiveExecutor


@dataclass
class FakeResult:
    text: str
    model: str
    latency_ms: float = 1.0
    input_tokens: int = 10
    output_tokens: int = 5
    cached_input_tokens: int = 0


class FakeAdapter:
    def __init__(self):
        self.calls = []

    def run(self, prompt, model):
        self.calls.append((prompt, model))
        return FakeResult(text=f"{model}:{prompt}", model=model)


def test_low_task_uses_low_model_without_network(monkeypatch):
    monkeypatch.setenv("EAON_MODEL_LOW", "fake/tiny")
    adapter = FakeAdapter()
    executor = UnifiedAdaptiveExecutor({"fake": adapter}, trace_path=None)
    result = executor.execute(TaskEnvelope("extract", complexity=0.1))
    assert result.trace.model == "tiny"
    assert adapter.calls == [("extract", "tiny")]


def test_local_privacy_uses_local_provider(monkeypatch):
    monkeypatch.setenv("EAON_MODEL_LOCAL", "fake/private")
    adapter = FakeAdapter()
    executor = UnifiedAdaptiveExecutor({"fake": adapter}, trace_path=None)
    result = executor.execute(
        TaskEnvelope("secret", complexity=0.9, privacy_level="local")
    )
    assert result.trace.model == "private"


def test_failed_low_verification_escalates_to_high(monkeypatch):
    monkeypatch.setenv("EAON_MODEL_LOW", "fake/low")
    monkeypatch.setenv("EAON_MODEL_HIGH", "fake/high")
    adapter = FakeAdapter()
    executor = UnifiedAdaptiveExecutor({"fake": adapter}, trace_path=None)

    result = executor.execute(
        TaskEnvelope("evidence", complexity=0.1, evidence_required=True),
        verifier=lambda text: text.startswith("high:"),
    )

    assert adapter.calls == [("evidence", "low"), ("evidence", "high")]
    assert result.trace.escalated is True
    assert result.trace.verified is True
    assert result.trace.model == "high"
