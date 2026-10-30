# EAON ENCR v0.1 — deterministic policy-conflict experiment

## Scope

`ENCR` separates an untrusted planning agent from a trusted deterministic policy
checker. The planner submits **action IDs only**. The checker consults an
application-owned immutable action catalogue, policy snapshot and observed facts.
It returns **a decision, not a capability, token, authorization for a real OS call,
or an executed action**.

The experiment uses one existing CIE contract, `EvidenceGateResult`:
`GateStatus.PASS` is necessary but not sufficient for a normal proposal.
`REVIEW` and `BLOCK` prevent the proposal from being accepted. An authorized
fallback can still be chosen if the trusted state indicates a risk.

## Running locally

From the repository root:

```sh
python -m unittest discover -s tests/governance -v
python -m scripts.demo_encr
```

No network, cloud access, LLM inference, or physical storage operation is made.

## Expected scenario outcomes

- `allowed_local_backup`: `permit` / `local_snapshot`.
- `forbidden_cloud_export`: `safe_fallback` / `pause_writes`.
- `no_safe_fallback`: `escalate` / no action.

## Threat model, limits and next step

- Untrusted model text cannot grant permissions, suppress protected rules,
  select privileged fallbacks, or insert unknown action identifiers.
- The policy snapshot **must be sourced from privileged local configuration**;
  the observed facts must be established separately by trusted sensors.
- `EvidenceGateResult.PASS` is not a proof of truth or statistical independence.
- Default-deny checks do not prove that action implementations are safe.
- Trusted action effects, costs, and prerequisites are simplified demo values.
- This code does **not** currently implement distinct OS processes, a sandbox,
  signed policy artifacts, human approval workflows, journal persistence, or
  an independent execution-time policy enforcement point.
- Before connecting any real tool, put policy checks inside a separately
  permissioned executor, authenticate policy snapshots, verify observations,
  define domain-specific safe fallbacks and build exhaustive adversarial tests.
- Observability readers should stay read-only; future decision events may be
  written by a distinct, authorized, hash-linked append-only logger.
