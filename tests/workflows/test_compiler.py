"""Deterministic workflow admission and terminal behavior on inert fixtures."""
from dataclasses import replace
from hashlib import sha256
import json

import pytest

from eaon_workflows import (
    Approval, Fact, MockRegistry, MockTool, Outcome, Requirement, SOP, Step,
    WorkflowCompiler, WorkflowError, bundle_digest, record_trace, run_workflow, sop_digest,
)

ENVIRONMENT = sha256(b"synthetic-test-environment-v1").hexdigest()


def test_project_bridge_blocks_quarantined_state_before_any_mock_handler(scenario, tmp_path):
    from core.workflow_bridge import run_project_workflow
    from eaon_kernel import ContinuityKernel, SourceRef
    from eaon_kernel.cards import FactClaim, MemoryCard
    from unittest.mock import patch
    _, registry, facts, _, _, workflow = scenario
    kernel = ContinuityKernel.create(tmp_path / "state.db")
    kernel.create_project("p", "Evidence gate")
    def card(value):
        body = "resource status=" + value
        source = SourceRef(value, "fixture://" + value, body, sha256(body.encode()).hexdigest())
        return MemoryCard(value, source, (0, len(body)), "succeeded", "test-reviewer", FactClaim("resource", "status", value))
    kernel.record_memory_card("p", "resource", card("available"))
    kernel.report_counterevidence("p", "resource", card("absent"), 1, "test-source")
    with patch.object(registry, "_execute_mock") as handler:
        blocked = run_project_workflow(kernel, "p", workflow, registry, facts, ENVIRONMENT)
    assert blocked.outcome is Outcome.BLOCKED_BY_POLICY and blocked.calls == 0 and blocked.final_output is None
    handler.assert_not_called()
    kernel.restore_memory_card("p", "resource", card("absent"), 2, "explicit correction")
    assert run_project_workflow(kernel, "p", workflow, registry, facts, ENVIRONMENT).outcome is Outcome.SUCCESS


def test_project_bridge_rejects_predictive_voice_before_mock_calls(scenario, tmp_path):
    from core.workflow_bridge import run_project_workflow
    from core.voice_state import TranscriptDraft
    from eaon_kernel import ContinuityKernel
    _, registry, facts, _, _, workflow = scenario
    kernel = ContinuityKernel.create(tmp_path / "state.db")
    kernel.create_project("p", "Voice gate")
    result = run_project_workflow(kernel, "p", workflow, registry, facts, ENVIRONMENT,
                                  voice_commit=TranscriptDraft("predictive words", 1))
    assert result.outcome is Outcome.BLOCKED_BY_POLICY and result.calls == 0 and result.final_output is None


@pytest.fixture
def scenario():
    first = Step("read-fixture", "mock.read", "1", (Requirement("resource_available", True),),
                 (Fact("evidence_ready", True),), "Synthetic evidence read")
    second = Step("complete-fixture", "mock.finish", "1", (Requirement("evidence_ready", True),),
                  (Fact("complete", True),), "Synthetic workflow complete")
    sop = SOP("fixture-procedure", "1", "Read a fixed synthetic fixture, then finish", (first, second),
              (Requirement("complete", True),))
    registry = MockRegistry((MockTool("mock.read", "1", first.expected_output, first.produces),
                             MockTool("mock.finish", "1", second.expected_output, second.produces)))
    facts = (Fact("resource_available", True),)
    traces = tuple(record_trace(sop, registry, facts, ENVIRONMENT, "trace-" + str(i)) for i in range(24))
    approval = Approval("synthetic-human-review", sop_digest(sop), bundle_digest(traces))
    workflow = WorkflowCompiler().compile(sop, traces, registry, ENVIRONMENT, approval)
    return sop, registry, facts, traces, approval, workflow


def test_24_successful_traces_compile_and_replay_with_real_mock_output_origin(scenario):
    sop, registry, facts, traces, approval, workflow = scenario
    reports = [run_workflow(workflow, registry, facts, ENVIRONMENT) for _ in traces]
    assert all(report.outcome is Outcome.SUCCESS for report in reports)
    assert sum(report.calls for report in reports) == 48
    assert all(report.observations == trace.observations for report, trace in zip(reports, traces))
    final = reports[0].final_output
    assert final.origin == "mock_handler" and final.action_id == "mock.finish"
    assert final.value == sop.steps[-1].expected_output
    assert final.output_sha256 == sha256(final.value.encode()).hexdigest()
    assert json.loads(json.dumps(workflow.to_dict()))["trace_count"] == 24


@pytest.mark.parametrize("count", [0, 19, 31])
def test_insufficient_or_excess_trace_bundle_is_not_compiled(scenario, count):
    sop, registry, facts, traces, approval, workflow = scenario
    selected = tuple(record_trace(sop, registry, facts, ENVIRONMENT, "trace-" + str(i)) for i in range(count))
    receipt = Approval("synthetic-review", sop_digest(sop), bundle_digest(selected))
    with pytest.raises(WorkflowError, match="requires_20_to_30_successful_traces"):
        WorkflowCompiler().compile(sop, selected, registry, ENVIRONMENT, receipt)


def test_approval_must_cover_exact_sop_and_trace_bundle(scenario):
    sop, registry, facts, traces, approval, workflow = scenario
    for receipt in (None, replace(approval, sop_sha256="0" * 64), replace(approval, trace_bundle_sha256="0" * 64)):
        with pytest.raises(WorkflowError, match="explicit_matching_approval_required"):
            WorkflowCompiler().compile(sop, traces, registry, ENVIRONMENT, receipt)


def test_duplicate_trace_ids_do_not_satisfy_evidence_budget(scenario):
    sop, registry, facts, traces, approval, workflow = scenario
    selected = traces[:-1] + (traces[0],)
    receipt = Approval("synthetic-review", sop_digest(sop), bundle_digest(selected))
    with pytest.raises(WorkflowError, match="duplicate_trace"):
        WorkflowCompiler().compile(sop, selected, registry, ENVIRONMENT, receipt)


@pytest.mark.parametrize("change", ["failure", "conflict", "stale-environment"])
def test_failed_conflicting_or_stale_observations_are_not_compiled(scenario, change):
    sop, registry, facts, traces, approval, workflow = scenario
    if change == "failure":
        altered = replace(traces[0], outcome=Outcome.TOOL_FAILURE)
    elif change == "conflict":
        observation = replace(traces[0].observations[-1], output="A different claimed answer")
        altered = replace(traces[0], observations=(traces[0].observations[0], observation))
    else:
        altered = replace(traces[0], environment_sha256="0" * 64)
    selected = (altered,) + traces[1:]
    receipt = Approval("synthetic-review", sop_digest(sop), bundle_digest(selected))
    with pytest.raises(WorkflowError):
        WorkflowCompiler().compile(sop, selected, registry, ENVIRONMENT, receipt)


def test_missing_evidence_and_proven_absence_have_distinct_terminal_results(scenario):
    _, registry, facts, _, _, workflow = scenario
    missing = run_workflow(workflow, registry, (), ENVIRONMENT)
    absent = run_workflow(workflow, registry, (Fact("resource_available", False),), ENVIRONMENT)
    assert missing.outcome is Outcome.MISSING_REQUIRED_EVIDENCE
    assert absent.outcome is Outcome.UNREACHABLE_GOAL
    assert missing.calls == absent.calls == 0
    assert missing.final_output is absent.final_output is None


def test_contradictory_precondition_is_rejected_before_any_fixture_call(scenario):
    _, registry, facts, _, _, workflow = scenario
    report = run_workflow(workflow, registry, (Fact("resource_available", "true"),), ENVIRONMENT)
    assert report.outcome is Outcome.UNREACHABLE_GOAL and report.calls == 0
    with pytest.raises(WorkflowError, match="duplicate_or_conflicting_fact"):
        Step("conflict", "mock.read", "1", (Requirement("same", True), Requirement("same", False)), (), "output")


def test_unknown_action_is_not_compiled_or_dispatched(scenario):
    sop, registry, facts, traces, approval, workflow = scenario
    altered = replace(sop, steps=(replace(sop.steps[0], action_id="unregistered.tool"), sop.steps[1]))
    receipt = Approval("synthetic-review", sop_digest(altered), bundle_digest(traces))
    with pytest.raises(WorkflowError, match="unsupported_mock_tool"):
        WorkflowCompiler().compile(altered, traces, registry, ENVIRONMENT, receipt)
    other = MockRegistry((registry.tools["mock.read"],))
    report = run_workflow(workflow, other, facts, ENVIRONMENT)
    assert report.outcome is Outcome.BLOCKED_BY_POLICY and report.calls == 0


@pytest.mark.parametrize("failure", ["mock.read", "mock.finish"])
def test_tool_failure_stops_once_without_synthetic_final_answer(scenario, failure):
    _, registry, facts, _, _, workflow = scenario
    report = run_workflow(workflow, registry, facts, ENVIRONMENT, fail_actions=frozenset({failure}))
    assert report.outcome is Outcome.TOOL_FAILURE
    assert report.calls == (1 if failure == "mock.read" else 2)
    assert report.observations[-1].outcome is Outcome.TOOL_FAILURE
    assert report.final_output is None


@pytest.mark.parametrize("change", ["artifact", "environment", "version"])
def test_tampered_or_stale_workflow_is_blocked_before_calls(scenario, change):
    _, registry, facts, _, _, workflow = scenario
    environment = ENVIRONMENT
    if change == "artifact":
        workflow = replace(workflow, trace_count=25)
    elif change == "environment":
        environment = "0" * 64
    else:
        registry = MockRegistry((replace(registry.tools["mock.read"], version="2"), registry.tools["mock.finish"]))
    report = run_workflow(workflow, registry, facts, environment)
    assert report.outcome is Outcome.BLOCKED_BY_POLICY and report.calls == 0
    assert report.final_output is None


def test_sop_free_text_and_response_are_never_evaluated_as_code(scenario, tmp_path):
    sop, registry, facts, traces, approval, workflow = scenario
    target = tmp_path / "untouched.txt"
    target.write_text("keep", encoding="utf-8")
    dangerous = f"__import__('pathlib').Path({str(target)!r}).unlink()"
    first = replace(sop.steps[0], expected_output=dangerous)
    altered = replace(sop, description=dangerous, steps=(first, sop.steps[1]))
    catalog = MockRegistry((replace(registry.tools["mock.read"], response=dangerous), registry.tools["mock.finish"]))
    selected = tuple(record_trace(altered, catalog, facts, ENVIRONMENT, "trace-" + str(i)) for i in range(24))
    receipt = Approval("synthetic-review", sop_digest(altered), bundle_digest(selected))
    compiled = WorkflowCompiler().compile(altered, selected, catalog, ENVIRONMENT, receipt)
    report = run_workflow(compiled, catalog, facts, ENVIRONMENT)
    assert report.outcome is Outcome.SUCCESS and target.read_text() == "keep"
    with pytest.raises(WorkflowError, match="mock_tools_only"):
        MockRegistry((lambda: target.unlink(),))


def test_workflow_is_bounded_and_has_verified_success_contract(scenario):
    sop, registry, facts, traces, approval, workflow = scenario
    with pytest.raises(WorkflowError, match="invalid_or_unbounded_steps"):
        replace(sop, steps=tuple(replace(sop.steps[0], step_id="step-" + str(i)) for i in range(17)))
    with pytest.raises(WorkflowError, match="empty_success_conditions"):
        replace(sop, success_conditions=())
