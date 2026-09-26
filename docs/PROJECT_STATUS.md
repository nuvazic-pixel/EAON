# EAON implementation status

Snapshot: **2026-09-20**. Inspected sources: original `main` at `89ee79f`, Knowledge
Gap head `971fc49`, and the recovered artifacts recorded in the manifest.

Update **2026-09-26**: The voice harness has a separate mock-only
`eaon_c3.safety.DryRunSession` policy and adversarial unit tests. This does not
change the historical snapshot below: Sherpa capture, trusted wake/source
classification and verified OS network isolation are still missing.
The original INTEL orchestrator now dispatches through an exact-ID gateway;
unknown IDs, empty output and failed Ollama calls return `ok=False`. The CAUC
shadow path is not connected to this gateway.

**Recovered code** means source exists and was inspected. **Historical report**
means behavior was reported without its complete runnable evidence. **Specified**
means an agreed design/test plan. **External artifact** is a separate deliverable.
Test results are recorded independently in [VERIFICATION.md](VERIFICATION.md).

| Area | Evidence | Current behavior and limits |
|---|---|---|
| INTEL core | Original Git code | CLI, keyword intent, Ollama Llama/Mistral calls, GeoIP/reputation, risk modes, notification adapters. No live services tested. |
| Semantic routing | Partial code | `Router._route_semantic()` falls back to keywords. The orchestrator uses its own keyword detector. |
| Critic/confirmation | Configuration in INTEL | Flags exist in routing decisions; that path does not enforce a completed critic loop or approval gate. |
| Model failure | Known INTEL limitation | Model helpers return an unavailable message on failure; the outer report may still return `ok=True`. |
| Knowledge records | Branch code | `Source`, `Evidence`, `Claim`, `Relation`, `Gap`, provenance and conditions. |
| Gap detection | Branch code | Contradictions, unsupported assumptions, two-hop bridges, unsupported cross-domain links and invalid time ranges. Scores are heuristic. |
| OpenAlex ingestion | Branch code | Normalization, conservative sentence extraction, SQLite and CLI. Live corpus ingestion not rerun. |
| Full research graph | Specified | `ExtractedClaim`/SQLite is not wired to `knowledge.Claim`/`GapDetector`; relation building, entity resolution and novelty audits remain. |
| Genesis SELF | Recovered code | JSONL append/verify/search, deterministic routing, reality labels and four fixed council roles. No LLM council. |
| Local-first evidence | Recovered code | Text/Markdown/optional PDF ingestion, deduplication, source evidence, SQLite, extractive fallback and optional loopback Ollama. |
| Skills | Recovered code | Repo reader, debugger, architect, digital twin, memory summarizer. Context budgets are metadata; token limits are not enforced. |
| Cognitive Twin API | Recovered code | PostgreSQL/FastAPI journal, graph, hypotheses, feedback, snapshots. pgvector schema support is not an embedding/retrieval pipeline. |
| Personal-data policy | Partial code | Rejects listed domain labels, not workplace details hidden under another label. No API authentication layer. |
| Cognitive graph v0.1 | Recovered schema | Populated personal/professional graph and visual exports are not published. |
| Browser Genesis | External site artifact | Saved publication shows browser-local capture, tags, links, import/export. Source is not here; distinct from PostgreSQL Twin. |
| Voice baseline | Historical report | Porcupine → Whisper CPU → Piper/Ollama. Wake/STT execution and an empty transcript were reported; full voice package missing. |
| Voice C3 | Recovered code | CSV scoring, mock/command adapters, WER, wake rates, p50/p95, hash-linked transitions. Mock returns the reference transcript and synthetic timings. |
| Sherpa runtime | Specified interface | Generic command adapter exists; real wrapper, models, WAV corpus and capture runtime are missing. |
| CAUC/privacy/interlock | Specified | Observational CAUC and fail-closed dry-run interlock are later requirements, not implemented by the recovered C3 harness. |
| MetaBench | Recovered code | Procedural tasks, scoring and reports. Perfect-mock results validate the harness, not intelligence. |
| Multi-model Council API | Historical UI/report | `/council` visible in earlier API evidence; server source and v0.2 critic/revision implementation not recovered. |
| MCP bridge | Historical draft/report | Six tool interfaces and expected endpoints recorded; original server source missing. |
| Azure/LangChain/LangGraph | Specified | Optional cloud/RAG architecture, no deployed runtime or infrastructure included. |
| Continuity kernel | Specified | Prior work stopped after inspection; `eaon_kernel/`, state cards, executive queue and checkpoint orchestration are not implemented. |
| BHIDT v0.4 | Recovered code | Recompute/fingerprint/report plus EAON Verification Adapter with toy-engine dependencies; not registered in the main router. |
| EAON-Red | Recovered source | Sandboxed benchmark artifact. Real SDK compatibility/evaluation not verified. |
| EAON Verify/Codex bridge | Specified | Case memory, explainable validation, bounded developer-agent bridge; runnable source not recovered. |
| Operating layer/device mesh | Specified | Vendor-neutral model/compute fabric over existing OSs; no `eaond` daemon or mesh service recovered. |
| Sensors/Observatory | Specified | Raspberry Pi, light/temperature/acceleration/SDR, calibration and timestamps. No instrumented sensor result demonstrated. |
| Timeline/mission console/avatar | Specified or presentation assets | Scenario/UI concepts and portrait/video work, not cognitive capability evidence. |

## Shared limits

Hash chains reveal inconsistent edits relative to a trusted head. Without anchoring
or signatures they cannot establish that an entire journal was not rewritten or
truncated. JSONL stores are single-writer prototypes; integrity verification is not
a mandatory read-before-act gate everywhere.

Reality Debugger labels and coverage scores are heuristics. `FACT` means assertion
markers matched, not that independent evidence established truth.

The packages have different storage/record formats. Consolidation makes them
reviewable and runnable; shared contracts, migrations and operational hardening
remain [roadmap work](ROADMAP.md).
