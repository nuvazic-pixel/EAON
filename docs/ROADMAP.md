# EAON roadmap after consolidation

Priority is integration of recovered working pieces, with explicit evidence gates.
This roadmap is not an assertion that the target features are implemented.

| Order | Slice | Done when |
|---|---|---|
| 1 | Continuity kernel on Genesis | Two sessions share project state, confirmed decisions, unknowns, one active goal and bounded tasks; invalid journals cannot authorize work |
| 2 | Local-first evidence adapter | SELF retrieves source-linked claims from SQLite through a typed interface, with correction/contradiction handling |
| 3 | Model/Council adapter | A measured local model can replace deterministic synthesis while evidence and permissions stay outside model control |
| 4 | Shared verification interface | BHIDT's adapter is registered read-only; reports preserve all four verdicts and source references |
| 5 | Research graph bridge | Ingested claims map into knowledge records; relations retain evidence/conditions; gap scores stay clearly heuristic |
| 6 | Voice containment | Capture/Sherpa wrapper, wake authorization, observational CAUC, strict mock executor, network boundary, journal and emergency stop are tested |
| 7 | MCP and provider routes | One documented API contract works end-to-end; local/cloud boundaries and failures are explicit |
| 8 | Observatory and UI | Calibrated sensor events and replayable scenarios appear in a mission console with uncertainty and provenance |

## First concrete continuity milestone

Retain the existing Genesis CLI and tests. Introduce `eaon_kernel/` with journal,
store, contracts, project cards and continuity functions behind an adapter. Add
explicit `confirmed` / `hypothesis` / `unknown` states. Do not silently migrate the
JSONL, SQLite and PostgreSQL stores into one another.

Demonstration: create a synthetic project and goal; append a sourced decision;
checkpoint; terminate; start a new process; recover the exact decision, outstanding
unknown and next task. Tampering, contradictory updates and missing sources must
produce visible errors or uncertainty, not plausible replacement memories.

## Existing technical debt to address before deployment

- INTEL model failure can be reported with `ok=True`; critic/confirmation flags
  are not enforced gates, and semantic routing is unfinished.
- Several modules share the `eaon` namespace; keep isolated until an intentional
  packaging migration preserves entry points.
- JSONL writers need a defined single writer/locking policy and trusted anchors.
- The Twin's domain exclusion is label-based; API authentication, content-policy
  enforcement and complete database integration testing are still missing.
- C3 command execution lacks the later interlock and a process timeout; adapter
  JSON needs stronger type validation before any real hardware trial.
- The Skills context budget is metadata, not an enforced token budget.
- Research ingestion and graph models are separate; novelty/calibration and
  historical-cutoff evaluation have not been validated.

## Preserve evidence quality

Keep mock, measured and planned results separate. Treat a passed dry-run as a test
of the harness, never permission to run real tools. Prefer a small reproducible
integration with provenance over a new layer of unconnected features.
