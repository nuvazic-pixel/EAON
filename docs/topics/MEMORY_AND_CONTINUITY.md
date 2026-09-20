# Memory, SELF and continuity

## Recovered implementations

| Store | Current contents | Boundary |
|---|---|---|
| Genesis JSONL | Input/synthesis/manual records, IDs, UTC timestamps, tags, metadata, previous/content hashes | Keyword recall, explicit chain verification, no concurrent-writer protection |
| Local-first SQLite | Sources, exact evidence claims, retrieval and runs | Separate schema; optional local model synthesis |
| Cognitive Twin PostgreSQL | Events/head, evidence, graph nodes/edges, hypotheses/feedback, self snapshots | Domain-label exclusion; no authenticated multi-user service |
| Voice State Journal | Typed `Transition` and `Observation` events with hashes | Benchmark output; full transcripts stay in the separate report |
| BHIDT experiment | Manifest, checkpoint, events, recomputation report | Scientific toy-engine evidence, not personal memory |

No automatic synchronization or schema migration connects these stores.

## Genesis SELF v0.2

`classify → retrieve memory → Reality Debugger → council response → append input
and synthesis` is implemented. Roles are Architect, Skeptic, Implementer and Judge.
They generate deterministic templates. A “next step” is text, not tool execution.

The Reality Debugger classifies assertion/assumption/risk/test markers. Its `FACT`
label is an assertion category, not independent fact verification. Search uses
token overlap and a small recency boost; semantic retrieval is not implemented.

The earlier local-first rewrite has a different responsibility: ingest real local
sources, retain exact evidence, deduplicate by content hash and fall back to quoted
evidence when no model is available. Its [audit](../../modules/local_first/AUDIT.md)
explains why mock tools and invented metadata in Paper Integration v2.1 were rejected.

## Personal Cognitive Twin

The accepted scope is personal cognition: concepts, patterns, beliefs, decisions,
uncertainty and evolution. Raw employer/project/health/family records are not needed
in a public code repository. Generic infrastructure skills can remain separate
domain capabilities without being ingested as a personal biography.

The PostgreSQL prototype includes hypothesis confidence, alternative explanations,
user feedback and Temporal Self snapshots. The policy rejects `work`, `professional`
and `employment` labels by default. It is not a content classifier. The recovered
schema/graph and browser prototype are different artifacts, not one database.

Weekly memory work reported manually entered `events.jsonl` objects with personal
context, triggers, concepts and reasoning. Their private contents are not included.
The public seed script uses explicit synthetic examples.

## Continuity specification — accepted, not implemented

The September 18 requirement is practical continuity across sessions, not an AGI
claim. The assistant must distinguish:

| State | Meaning | Response behavior |
|---|---|---|
| Confirmed memory | Traceable stored record with source and time | State what the record supports |
| Inferred hypothesis | Derived interpretation, not directly established | Label inference and its evidence |
| Unknown / needs retrieval | Missing, conflicting or unavailable context | Retrieve or state the gap |

Required persistent structures: append-only event journal, JSON project state
cards, compact Markdown/JSON summaries, append-only decision log and session
checkpoints. SQLite is a proposed index/projection, not a replacement for provenance.

Required loop: observe, retrieve, form bounded working context, reason, plan,
act through a permitted tool, verify, write a checkpoint.

Retrieval is deterministic first (active project, latest checkpoint, unresolved
decisions), semantic second. Every retrieved item needs source/time, uncertainty,
contradiction checks and the minimum relevant content.

Executive state has one active goal and a bounded queue. Task switching, failure,
uncertainty, completed actions and next steps must survive restart. Missing context
must not be filled with a plausible narrative.

Proposed Phase 2 paths were `eaon_kernel/{journal,store,projects,continuity,contracts}.py`.
The retrieved earlier run stopped after Phase 1 inspection of Genesis and five
passing tests. Those kernel files were not recovered; this consolidation does not
claim to implement them.

## Next acceptance cases

1. Session A saves a decision; session B recovers exactly its record and source.
2. Unknown information stays unknown; an inference cannot overwrite a fact.
3. A correction appends a superseding record without deleting the original.
4. Contradictory records are surfaced with provenance.
5. Corrupt memory cannot enter a tool-authorizing context.
6. Restart restores one active goal and the bounded pending queue.
7. Private state remains outside Git and cloud routes require a deliberate boundary.

These are integration acceptance criteria, not tests already passing today.
