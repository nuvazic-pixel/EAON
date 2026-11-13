# Experimental mock workflow compiler

`eaon_workflows` is a conservative prototype inspired by the November 13
ReTrace proposal. It accepts a typed stable SOP and 20–30 reviewed successful
synthetic traces. It does not induce code, conditions or tool arguments from
free text, integrate an LLM, or execute real tools.

Each step declares an action ID, tool version, literal equality prerequisites,
produced facts and expected output. Success requires explicit final conditions.
An `Approval` receipt binds the exact SOP and trace-bundle digests; it is a
caller-supplied review record, not authentication or a cryptographic signature.
The compiler rejects trace conflicts/failures, duplicate trace IDs, unsupported
actions, stale environments and observations that do not reproduce the fixed
mock contract. The compiled artifact binds SOP, approval, tool catalog and
environment identity.

`run_workflow()` runs at most 16 fixed inert mock fixture handlers. The registry
accepts `MockTool` data only, never callables, imports, scripts or external tool
adapters. No file, network or subprocess execution hook is supplied. Known
contradictory prerequisites produce `UNREACHABLE_GOAL` relative to that approved
procedure; absent facts produce `MISSING_REQUIRED_EVIDENCE`. Neither conclusion
claims global infeasibility in the real world. Stale/tampered artifacts produce
`BLOCKED_BY_POLICY`. A fixture fault produces `TOOL_FAILURE` and stops without
retrying or fabricating final answer text. `SUCCESS` requires the observed mock
outputs/effects and final literal conditions to match.

A successful final output identifies its actual `mock_handler`, action, step,
tool version and output digest. Refusal/failure reports have no final output.
The demonstration uses an explicitly named synthetic review receipt and records
24 two-step traces, then compares their action/output observations with 24
compiled replays. Identical synthetic traces do not demonstrate coverage of
production exceptions; there is no LLM-agent baseline or measured savings.

```sh
python scripts/demo_workflow.py
python -m pytest tests/workflows -q
```

This package remains separate from chat, memory admission, voice authorization
and any real executor. Adding a real adapter would require a separate reviewed
execution boundary with target admission, capability checks and verified state
effects. Hashes provide content identity, not approval authenticity or provenance
of a real production trace.
