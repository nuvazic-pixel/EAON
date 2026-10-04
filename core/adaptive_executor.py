"""Unified executor for EAON adaptive routing."""

import uuid
from dataclasses import dataclass
from typing import Callable, Optional, Protocol

from core.adaptive import AdaptiveModelPolicy, TaskEnvelope
from core.adaptive_telemetry import AdaptiveTrace, append_trace, estimate_standard_cost_usd
from core.model_registry import ModelRegistry, ModelSpec


class ExecutionAdapter(Protocol):
    def run(self, prompt: str, model: str): ...


Verifier = Callable[[str], bool]


@dataclass(frozen=True)
class AdaptiveExecution:
    output_text: str
    trace: AdaptiveTrace


class UnifiedAdaptiveExecutor:
    """Policy -> registry -> adapter -> verifier/escalation -> trace."""

    def __init__(
        self,
        adapters: dict[str, ExecutionAdapter],
        policy: Optional[AdaptiveModelPolicy] = None,
        registry: Optional[ModelRegistry] = None,
        trace_path: Optional[str] = "logs/adaptive.jsonl",
    ):
        self.adapters = adapters
        self.policy = policy or AdaptiveModelPolicy()
        self.registry = registry or ModelRegistry()
        self.trace_path = trace_path

    def execute(
        self,
        envelope: TaskEnvelope,
        verifier: Optional[Verifier] = None,
        task_id: Optional[str] = None,
    ) -> AdaptiveExecution:
        route = self.policy.select(envelope)
        logical_tier = self._logical_tier(route.tier)
        spec = self.registry.resolve(logical_tier)
        result = self._call_adapter(spec, envelope.task)

        verified = None
        escalated = False
        if route.require_verification and verifier is not None:
            verified = bool(verifier(result.text))
            if not verified and logical_tier == "low":
                logical_tier = "high"
                spec = self.registry.resolve("high")
                result = self._call_adapter(spec, envelope.task)
                verified = bool(verifier(result.text))
                escalated = True

        trace = AdaptiveTrace(
            task_id=task_id or str(uuid.uuid4())[:8],
            tier=logical_tier,
            model=result.model,
            complexity=envelope.complexity,
            privacy_level=envelope.privacy_level,
            reason=route.reason,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cached_input_tokens=getattr(result, "cached_input_tokens", 0),
            cost_usd=estimate_standard_cost_usd(
                result.model,
                result.input_tokens,
                result.output_tokens,
                getattr(result, "cached_input_tokens", 0),
            ),
            verified=verified,
            escalated=escalated,
        )
        if self.trace_path:
            append_trace(trace, self.trace_path)
        return AdaptiveExecution(result.text, trace)

    def _call_adapter(self, spec: ModelSpec, prompt: str):
        adapter = self.adapters.get(spec.provider)
        if adapter is None:
            raise RuntimeError(f"no adapter registered for provider: {spec.provider}")
        return adapter.run(prompt, spec.model)

    @staticmethod
    def _logical_tier(policy_tier: str) -> str:
        return {"luna": "low", "sol": "high", "local": "local"}[policy_tier]
