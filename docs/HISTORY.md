# EAON recovered project history

This is a project record, not a verbatim chat export. Dates come from Git, artifact
metadata or retrieved messages. A thread's title date can precede later messages.
Missing execution evidence is not converted into a completion claim.

| Date / period | Subject and update | Evidence / disposition |
|---|---|---|
| 2026-02-17–19 | Local orchestrator, router/arbitration, plugins, memory, telemetry; voice baseline. | Conversation. Wake word and Whisper CPU ran; empty transcription reported. Original voice source absent. |
| 2026-03-10 | Voice output/telemetry reported working; README, diagram, 90-second demo and GitHub packaging requested. | User report and proposed structure; not the actual initial Git commit date. |
| 2026-03-15 | Jarvis-style loop: stop wake capture before recording/TTS, then resume. | Voice filenames and proposed microphone fix recovered; patch/run unavailable. |
| 2026-03-26 | Baseline considered complete by user; EAON → Codex bounded development bridge discussed. | Historical report and proposal. |
| 2026-04-01 | FINALFRONTIER/INTEL: GeoIP, reputation sources, risk scoring, normal/balanced/safe routing. | Discussion plus later Git code. Earlier “18 passed” claim lacks its original tests here. |
| 2026-04-02 | EAON Verify: case memory, explanations, company/geo validation, aggregate risk and reports. | Design proposal, distinct from the INTEL source. |
| 2026-04-10 | Initial EAON 2.0 repository commit. | [`89ee79f`](https://github.com/nuvazic-pixel/EAON/commit/89ee79f26067827f611b7b655afbc8f757db1681). Source retained. |
| 2026-04-19 | VS Code → MCP → local EAON design. | Proposed API/tool boundary. |
| 2026-05-24 | “Build EAON MCP bridge”; stdio server and six tool interfaces described. | Server source not recovered; interface assumptions recorded. |
| 2026-06-12–13 | EAON-Red: causal templates, trace-aware mutation, Go-Explore archive, replay candidates. | June 13 `attack.py` recovered in `research/eaon_red/`. |
| 2026-06-14 | Council API/Open WebUI; Architect → Skeptic → Implementer → Judge → memory. Council v0.2 critique/revision chosen. | API UI evidence and conversation; backend server absent. |
| 2026-06-15 | Skills v0.1: small static context, task-selected dynamic context. | ZIP recovered in `modules/skills/`. |
| 2026-07-02 | Azure/LangChain requested; LangGraph, RAG, MCP, FastAPI and Azure deployment proposed. | Optional cloud design, no deployment record. |
| 2026-07-13 | MetaBench: seeded tasks, abstention, contradiction/rule-shift/repair, calibration, mock/Ollama, JSON/HTML and comparison. | ZIP and historical perfect-mock fixture recovered; no real model score established. |
| 2026-08-10 | World Knowledge Gap branch: provenance records, relations, gaps and reality/discovery/epistemic views. | Four original feature commits preserved. |
| 2026-08-11 | OpenAlex normalization, abstract reconstruction, conservative claims, SQLite, CLI and tests. | Seven further commits ending at `971fc49`; source incorporated with history. |
| 2026-08-15 | EAON as operating layer over Windows/Linux/Android; vendor-neutral model/compute fabric. RO/DE/EN voice bake-off accepted. | Design, not an OS kernel/daemon release. |
| 2026-08-24 | C3/A1/B2 benchmark, SHA-256 State Journal, generic Sherpa command interface. | ZIP recovered in `benchmarks/voice/`; mock-only evidence. |
| 2026-08-26 | Cognitive Twin graph: nodes/edges, hypotheses, provenance, sensitivity, graph/visual exports. | ZIP inspected. Schema recovered; populated personal/professional profile withheld. |
| 2026-09-05 | Strictly personal Twin; PostgreSQL/pgvector + FastAPI Genesis, hypotheses, feedback and snapshots. | ZIP source recovered. Earlier Docker startup blocked; database deployment not verified here. |
| 2026-09-05 onward | Weekly Twin steps: memory/evolution, patterns, personal knowledge, privacy; first manual JSONL events reported. | Personal event contents stay private; continuity requirements retained. |
| 2026-09-09 | Browser Genesis: local capture, concept/pattern tags, cross-domain links, JSON import/export. | Saved site publication inspected; separate from PostgreSQL service. |
| 2026-09-11 | Local-first v0.1 rebuild after Paper Integration v2.1 audit: real local evidence, SQLite, truthful fallback, audit trail. | ZIP and `AUDIT.md` recovered. Old mock-heavy integration not restored as working code. |
| 2026-09-12 | “Reality Debugger” arcade HTML. | Themed game artifact, not a sensor analyzer or reasoning module. |
| 2026-09, exact day not re-established | EAON portraits and motion assets. | Filenames discovered; face/video assets not republished as runtime source. |
| 2026-09-16 | Genesis SELF v0.2 consolidates routing, reality labels, recall, deterministic council and JSONL CLI. | ZIP source recovered in `modules/genesis/`. |
| 2026-09-16–17 | EAON umbrella: Reality Debugger, Twin, Memory Vault, observatory, sensors/SDR, timeline simulator, mission console. | Architecture/roadmap; no instrumented multiverse detection or sensor validation. |
| 2026-09-17–18 | FTQC architecture twin and engineering/GenCAD as related simulation/verification directions. | Separate deliverables; EAON runtime integration not established. |
| 2026-09-18 | Continuity: identity, project state, decisions, unknowns, checkpoints, deterministic-first retrieval, one active goal, bounded queue. | Prior Phase 1 inspected Genesis and ran five tests; Phase 2 kernel proposed. |
| 2026-09-18 | Containment/audit: offline sandbox, allowlist, pre-call risk, kill switch, replay. | Proposed hardening, not implied by INTEL mode flags. |
| 2026-09-18 | Sherpa v1.13.8 plan: mock-only interlock, dBFS, 30-command RO/DE/EN smoke corpus, reporting, endurance stages. | Accepted plan; scripts/live run missing. Sync planned September 21, 09:00–09:30 German time. |
| 2026-09-18–19 | BHIDT through journal/replay to v0.4 recomputation, fingerprints, reports and EAON adapter. | Latest v0.4 ZIP recovered with dependencies. Supersedes earlier retrieval that only saw its proposal. |
| 2026-09-19–20 | Direct-to-main consolidation authorized; recovered modules, status, architecture, protocols and launcher/checks. | This consolidation; [verification evidence](VERIFICATION.md). |

## Original Knowledge Gap commits

`169e7db` package → `3c4aa34` models → `603e625` detector → `ba2f1c1` architecture
→ `0afae21` ingestion package → `ef67374` OpenAlex → `d16a9b0` extractor
→ `bc2f6ec` store → `5961bcf` CLI → `a602b5a` tests → `971fc49` docs.

These remain original commits in the consolidated branch's ancestry. No history
was force-rewritten.
