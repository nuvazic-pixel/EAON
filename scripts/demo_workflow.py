"""ReTrace-inspired fixed mock workflow demo; no LLM or production benchmark."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eaon_workflows import (Approval, Fact, MockRegistry, MockTool, Outcome, Requirement,
                            SOP, Step, WorkflowCompiler, bundle_digest, record_trace,
                            run_workflow, sop_digest)


def main():
    environment = sha256(b"eaon-mock-workflow-demo-v1").hexdigest()
    read = Step("read-fixture", "mock.read", "1", (Requirement("resource_available", True),),
                (Fact("evidence_ready", True),), "Synthetic fixture read")
    finish = Step("finish-fixture", "mock.finish", "1", (Requirement("evidence_ready", True),),
                  (Fact("complete", True),), "Synthetic procedure complete")
    sop = SOP("synthetic-evidence-procedure", "1", "Read an approved fixed fixture and confirm completion",
              (read, finish), (Requirement("complete", True),))
    registry = MockRegistry((MockTool(read.action_id, "1", read.expected_output, read.produces),
                             MockTool(finish.action_id, "1", finish.expected_output, finish.produces)))
    facts = (Fact("resource_available", True),)
    traces = tuple(record_trace(sop, registry, facts, environment, "trace-" + str(i)) for i in range(24))
    # Synthetic explicit review receipt; not a signature or a real user's approval.
    approval = Approval("synthetic-human-review-fixture", sop_digest(sop), bundle_digest(traces))
    workflow = WorkflowCompiler().compile(sop, traces, registry, environment, approval)
    reports = [run_workflow(workflow, registry, facts, environment) for _ in traces]
    assert all(report.outcome is Outcome.SUCCESS for report in reports)
    assert all(report.observations == trace.observations for report, trace in zip(reports, traces))
    absent = run_workflow(workflow, registry, (Fact("resource_available", False),), environment)
    assert absent.outcome is Outcome.UNREACHABLE_GOAL and absent.calls == 0
    failed = run_workflow(workflow, registry, facts, environment, fail_actions=frozenset({"mock.read"}))
    assert failed.outcome is Outcome.TOOL_FAILURE and failed.calls == 1 and failed.final_output is None
    print(json.dumps({"ok": True, "mode": "fixed_mock_fixtures_only", "training_traces": len(traces),
        "trace_calls": sum(len(trace.observations) for trace in traces),
        "compiled_replay_calls": sum(report.calls for report in reports),
        "replay_matches": len(reports), "llm_calls": 0,
        "artifact_sha256": workflow.artifact_sha256,
        "unreachable_goal_calls": absent.calls, "failure_calls": failed.calls,
        "failure_final_output": failed.final_output, "final_output": reports[0].to_dict()["final_output"],
        "limits": "synthetic workflow equivalence; no LLM baseline, timing, savings or real-tool performance claim"}, indent=2))


if __name__ == "__main__":
    main()
