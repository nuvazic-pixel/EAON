"""Conservative trace-to-workflow prototype; it never executes real tools.

Only literal equality conditions and fixed mock responses are supported.
Free-text SOP descriptions, traces and responses are never evaluated as code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
import math
import re
from types import MappingProxyType


MAX_STEPS = 16
MAX_FACTS = 64


class WorkflowError(ValueError):
    """Stable rejection code with no raw tool exception or source content."""


class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"
    MISSING_REQUIRED_EVIDENCE = "MISSING_REQUIRED_EVIDENCE"
    UNREACHABLE_GOAL = "UNREACHABLE_GOAL"
    TOOL_FAILURE = "TOOL_FAILURE"


def _text(value, label, limit=2000):
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise WorkflowError("invalid_" + label)


def _id(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,79}", value):
        raise WorkflowError("invalid_identifier")


def _digest(value):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise WorkflowError("invalid_digest")


def _scalar(value):
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is str and len(value) <= 2000:
        return
    raise WorkflowError("invalid_fact_value")


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value):
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Fact:
    name: str
    value: str | int | float | bool | None

    def __post_init__(self):
        _id(self.name)
        _scalar(self.value)


@dataclass(frozen=True)
class Requirement:
    """A literal fact needed by the approved procedure, never an expression."""
    name: str
    expected: str | int | float | bool | None

    def __post_init__(self):
        _id(self.name)
        _scalar(self.expected)


def _items(items, kind, *, nonempty=False):
    if type(items) is not tuple or len(items) > MAX_FACTS or any(type(item) is not kind for item in items):
        raise WorkflowError("invalid_fact_contract")
    if nonempty and not items:
        raise WorkflowError("empty_success_conditions")
    if len({item.name for item in items}) != len(items):
        raise WorkflowError("duplicate_or_conflicting_fact")


@dataclass(frozen=True)
class Step:
    step_id: str
    action_id: str
    tool_version: str
    requires: tuple[Requirement, ...]
    produces: tuple[Fact, ...]
    expected_output: str

    def __post_init__(self):
        _id(self.step_id)
        _id(self.action_id)
        _text(self.tool_version, "tool_version", 100)
        _items(self.requires, Requirement)
        _items(self.produces, Fact)
        _text(self.expected_output, "expected_output")


@dataclass(frozen=True)
class SOP:
    procedure_id: str
    revision: str
    description: str
    steps: tuple[Step, ...]
    success_conditions: tuple[Requirement, ...]

    def __post_init__(self):
        _id(self.procedure_id)
        _text(self.revision, "sop_revision", 100)
        _text(self.description, "description")
        if type(self.steps) is not tuple or not 1 <= len(self.steps) <= MAX_STEPS or any(type(item) is not Step for item in self.steps):
            raise WorkflowError("invalid_or_unbounded_steps")
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise WorkflowError("duplicate_step")
        _items(self.success_conditions, Requirement, nonempty=True)


@dataclass(frozen=True)
class MockTool:
    """An inert response fixture, not a Python callable or real tool adapter."""
    action_id: str
    version: str
    response: str
    produces: tuple[Fact, ...] = ()

    def __post_init__(self):
        _id(self.action_id)
        _text(self.version, "tool_version", 100)
        _text(self.response, "mock_response")
        _items(self.produces, Fact)


@dataclass(frozen=True)
class TraceObservation:
    step_id: str
    action_id: str
    tool_version: str
    output: str
    produced: tuple[Fact, ...]
    outcome: Outcome = Outcome.SUCCESS

    def __post_init__(self):
        _id(self.step_id)
        _id(self.action_id)
        _text(self.tool_version, "tool_version", 100)
        _text(self.output, "observed_output")
        _items(self.produced, Fact)
        if type(self.outcome) is not Outcome:
            raise WorkflowError("invalid_outcome")


@dataclass(frozen=True)
class TraceRecord:
    trace_id: str
    sop_sha256: str
    environment_sha256: str
    initial_facts: tuple[Fact, ...]
    observations: tuple[TraceObservation, ...]
    outcome: Outcome

    def __post_init__(self):
        _id(self.trace_id)
        _digest(self.sop_sha256)
        _digest(self.environment_sha256)
        _items(self.initial_facts, Fact)
        if type(self.observations) is not tuple or len(self.observations) > MAX_STEPS or any(type(item) is not TraceObservation for item in self.observations):
            raise WorkflowError("invalid_observations")
        if type(self.outcome) is not Outcome:
            raise WorkflowError("invalid_outcome")


@dataclass(frozen=True)
class Approval:
    """Explicit caller-supplied review receipt, not an identity/signature proof."""
    reviewer: str
    sop_sha256: str
    trace_bundle_sha256: str

    def __post_init__(self):
        _text(self.reviewer, "reviewer", 200)
        _digest(self.sop_sha256)
        _digest(self.trace_bundle_sha256)


@dataclass(frozen=True)
class FinalOutput:
    value: str
    origin: str
    step_id: str
    action_id: str
    tool_version: str
    output_sha256: str


@dataclass(frozen=True)
class RunReport:
    outcome: Outcome
    reason: str
    observations: tuple[TraceObservation, ...] = ()
    final_output: FinalOutput | None = None

    @property
    def calls(self):
        return len(self.observations)

    def to_dict(self):
        return asdict(self)


class _MockFailure(RuntimeError):
    pass


class MockRegistry:
    """Only these fixed fixture objects are admissible; no dynamic imports/eval."""
    def __init__(self, tools):
        if type(tools) is not tuple or not tools or len(tools) > MAX_STEPS or any(type(tool) is not MockTool for tool in tools):
            raise WorkflowError("mock_tools_only")
        if len({tool.action_id for tool in tools}) != len(tools):
            raise WorkflowError("duplicate_mock_tool")
        self.tools = MappingProxyType({tool.action_id: tool for tool in tools})

    @property
    def sha256(self):
        return _hash([asdict(self.tools[key]) for key in sorted(self.tools)])

    def _execute_mock(self, step, *, fail=False):
        tool = self.tools[step.action_id]
        if fail:
            raise _MockFailure("simulated_tool_failure")
        return TraceObservation(step.step_id, tool.action_id, tool.version, tool.response, tool.produces)


def sop_digest(sop):
    if type(sop) is not SOP:
        raise WorkflowError("typed_sop_required")
    return _hash(asdict(sop))


def bundle_digest(traces):
    if type(traces) is not tuple or any(type(trace) is not TraceRecord for trace in traces):
        raise WorkflowError("typed_traces_required")
    return _hash([asdict(trace) for trace in traces])


def _check(requirements, facts):
    for condition in requirements:
        if condition.name not in facts:
            return Outcome.MISSING_REQUIRED_EVIDENCE, "required_fact_absent"
        actual = facts[condition.name]
        if type(actual) is not type(condition.expected) or actual != condition.expected:
            return Outcome.UNREACHABLE_GOAL, "approved_precondition_contradicted"
    return None


def _catalog_check(sop, registry):
    for step in sop.steps:
        tool = registry.tools.get(step.action_id)
        if tool is None:
            return "unsupported_mock_tool"
        if tool.version != step.tool_version:
            return "stale_tool_version"
        if tool.response != step.expected_output or tool.produces != step.produces:
            return "mock_contract_mismatch"
    return None


def _execute(sop, registry, initial_facts, *, fail_actions=frozenset()):
    # Prove declared feasibility before any call, using only approved effects.
    predicted = {fact.name: fact.value for fact in initial_facts}
    for step in sop.steps:
        refusal = _check(step.requires, predicted)
        if refusal:
            return RunReport(*refusal)
        predicted.update({fact.name: fact.value for fact in step.produces})
        if len(predicted) > MAX_FACTS:
            return RunReport(Outcome.BLOCKED_BY_POLICY, "fact_budget_exceeded")
    refusal = _check(sop.success_conditions, predicted)
    if refusal:
        return RunReport(*refusal)
    facts, observations = {fact.name: fact.value for fact in initial_facts}, []
    for step in sop.steps:
        try:
            observed = registry._execute_mock(step, fail=step.action_id in fail_actions)
        except Exception:
            # The attempt is recorded, but infrastructure never supplies an answer.
            observations.append(TraceObservation(step.step_id, step.action_id, step.tool_version,
                                                 "mock_call_failed", (), Outcome.TOOL_FAILURE))
            return RunReport(Outcome.TOOL_FAILURE, "mock_tool_failed", tuple(observations))
        observations.append(observed)
        if observed.output != step.expected_output or observed.produced != step.produces or observed.outcome is not Outcome.SUCCESS:
            return RunReport(Outcome.TOOL_FAILURE, "observed_contract_mismatch", tuple(observations))
        facts.update({fact.name: fact.value for fact in observed.produced})
    refusal = _check(sop.success_conditions, facts)
    if refusal:
        return RunReport(*refusal, tuple(observations))
    last = observations[-1]
    final = FinalOutput(last.output, "mock_handler", last.step_id, last.action_id,
                        last.tool_version, sha256(last.output.encode("utf-8")).hexdigest())
    return RunReport(Outcome.SUCCESS, "verified_mock_success_conditions", tuple(observations), final)


def record_trace(sop, registry, initial_facts, environment_sha256, trace_id):
    """Collect one synthetic trace from a typed SOP and the fixed mock catalog."""
    sop_digest(sop)
    _digest(environment_sha256)
    _items(initial_facts, Fact)
    if type(registry) is not MockRegistry:
        raise WorkflowError("mock_registry_required")
    error = _catalog_check(sop, registry)
    report = RunReport(Outcome.BLOCKED_BY_POLICY, error) if error else _execute(sop, registry, initial_facts)
    return TraceRecord(trace_id, sop_digest(sop), environment_sha256, initial_facts,
                       report.observations, report.outcome)


@dataclass(frozen=True)
class CompiledWorkflow:
    sop: SOP
    environment_sha256: str
    registry_sha256: str
    approval: Approval
    trace_count: int
    artifact_sha256: str

    def unsigned(self):
        return {"schema": "eaon.mock-workflow.v1", "sop": asdict(self.sop),
                "environment_sha256": self.environment_sha256, "registry_sha256": self.registry_sha256,
                "approval": asdict(self.approval), "trace_count": self.trace_count}

    def to_dict(self):
        return {**self.unsigned(), "artifact_sha256": self.artifact_sha256}


class WorkflowCompiler:
    def compile(self, sop, traces, registry, environment_sha256, approval):
        identity = sop_digest(sop)
        _digest(environment_sha256)
        bundle = bundle_digest(traces)
        if not 20 <= len(traces) <= 30:
            raise WorkflowError("requires_20_to_30_successful_traces")
        if len({trace.trace_id for trace in traces}) != len(traces):
            raise WorkflowError("duplicate_trace")
        if type(approval) is not Approval or approval.sop_sha256 != identity or approval.trace_bundle_sha256 != bundle:
            raise WorkflowError("explicit_matching_approval_required")
        if type(registry) is not MockRegistry:
            raise WorkflowError("mock_registry_required")
        error = _catalog_check(sop, registry)
        if error:
            raise WorkflowError(error)
        for trace in traces:
            if trace.outcome is not Outcome.SUCCESS or trace.sop_sha256 != identity or trace.environment_sha256 != environment_sha256:
                raise WorkflowError("failed_or_stale_trace")
            expected = _execute(sop, registry, trace.initial_facts)
            if expected.outcome is not Outcome.SUCCESS or trace.observations != expected.observations:
                raise WorkflowError("trace_conflict_or_unverified_success")
        unsigned = {"schema": "eaon.mock-workflow.v1", "sop": asdict(sop),
                    "environment_sha256": environment_sha256, "registry_sha256": registry.sha256,
                    "approval": asdict(approval), "trace_count": len(traces)}
        return CompiledWorkflow(sop, environment_sha256, registry.sha256, approval, len(traces), _hash(unsigned))


def run_workflow(workflow, registry, initial_facts, environment_sha256, *, fail_actions=frozenset()):
    """Run at most MAX_STEPS inert fixture handlers; terminal reports never retry."""
    if type(workflow) is not CompiledWorkflow or type(registry) is not MockRegistry:
        return RunReport(Outcome.BLOCKED_BY_POLICY, "compiled_mock_workflow_required")
    try:
        _items(initial_facts, Fact)
        _digest(environment_sha256)
        if type(fail_actions) is not frozenset or any(type(item) is not str or item not in registry.tools for item in fail_actions):
            raise WorkflowError("invalid_fault_fixture")
        if _hash(workflow.unsigned()) != workflow.artifact_sha256:
            raise WorkflowError("artifact_integrity_failed")
        if workflow.approval.sop_sha256 != sop_digest(workflow.sop) or not 20 <= workflow.trace_count <= 30:
            raise WorkflowError("unapproved_workflow")
        if workflow.environment_sha256 != environment_sha256 or workflow.registry_sha256 != registry.sha256:
            raise WorkflowError("stale_environment_or_mock_catalog")
        error = _catalog_check(workflow.sop, registry)
        if error:
            raise WorkflowError(error)
    except (WorkflowError, TypeError, ValueError, AttributeError):
        return RunReport(Outcome.BLOCKED_BY_POLICY, "invalid_stale_or_unapproved_workflow")
    return _execute(workflow.sop, registry, initial_facts, fail_actions=fail_actions)
