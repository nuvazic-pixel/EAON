# EAON integrations and interface history

## Multi-model Council and Open WebUI

The June 14 conversation and API screenshot established a Council API interface:
`GET /`, `POST /council`, OpenAPI/Swagger and Open WebUI integration work. The
reported role assignment was Architect (`qwen3:8b`), Skeptic (DeepSeek), Implementer
(QwenCoder), Judge (`qwen3:8b`), then Markdown memory. Exact model variants and a
complete run transcript are not available for every role.

Council v0.2 was selected to add critique/revision before persistent memory and
a Twin Advisor. The described server was `eaon_council_server.py`; it was not
recovered. Genesis SELF's deterministic `Council` is a separate implementation.

## MCP bridge

The May 24 draft used a stdio MCP server, `EAON_API_URL=http://localhost:8000`,
dependencies `mcp`, `requests`, `pydantic`, and expected EAON endpoints
`GET /health` and `POST /orchestrate`.

| Described tool | Intended role |
|---|---|
| `eaon_health_check` | Runtime status |
| `eaon_run_task` | General orchestration |
| `eaon_code_review` | Code analysis |
| `eaon_architecture_plan` | Design proposal |
| `eaon_project_manager` | Bounded project planning |
| `eaon_geospatial_reasoner` | GIS/infrastructure analysis |

Original bridge source and compatibility endpoint implementation are missing.
Do not point it at the Cognitive Twin service expecting the same contract: that
service has `/api/v1/health` and data-management routes, not `/orchestrate`.

## Azure / LangChain / LangGraph

The July 2 requirement proposed an optional Azure path: EAON control layer,
LangChain tools/RAG, LangGraph stateful workflows, Azure model endpoints, AI Search,
FastAPI/Container Apps, MCP, Key Vault and monitoring. A proposed `POST /run` accepted
task/mode. No deployed application or infrastructure code was recovered.

The later personal continuity direction is local-first. Record cloud execution as
an optional provider with its own privacy policy; do not silently send personal
journals or documents to it. This is a design boundary, not a functioning cloud router.

## Skills and developer-agent bridge

Recovered Skills v0.1 selects one of repo_reader, debugger, architect, digital_twin,
memory_summarizer and loads its Markdown/tool text. The chosen context budget is
reported, not enforced. It is not yet integrated into Council, MCP or the main router.

The Codex bridge discussion proposed bounded repository inspection, implementation,
test and review tasks. A subprocess sketch was not a verified developer-agent service.
EAON Verify similarly proposed case memory, explanations, company/geo checks and
reports; do not confuse those plans with existing IP intelligence adapters.

## EAON as an operating layer

The accepted August direction was an AI layer over Windows/Linux/Android, not a new
OS kernel. Proposed components: `eaond`, planner/task graph/scheduler/router,
model fabric, compute fabric, typed memory, capability bus, policy, verification,
event bus, device mesh and UI/voice. Local model providers and optional cloud burst
should remain replaceable. No daemon or mesh source was recovered.

## Browser, avatar and presentation work

The saved Cognitive Twin Genesis site publication shows browser-local entries,
concept/pattern tagging, cross-domain links, counts and JSON import/export. It is
different from the FastAPI/PostgreSQL Genesis source included here. No claim is made
about its current live code or availability.

Found presentation assets: `eaon-orchestrator-portrait.png`,
`eaon-orchestrator-portrait-rested.png`, `eaon-orchestrator-motion.mp4`,
`eaon-higgsfield-motion.mp4`, `eaon-higgsfield-motion-text.mp4`.
These are cataloged, not published with personal likeness data. Earlier presentation
tasks also requested an architecture diagram, premium README and 90-second demo.

The `index.html` Reality Debugger arcade artifact uses clean-signal/noise gameplay.
Its shared name does not make it a physical anomaly detector or the reasoning module.

## Sensor layer and Reality Observatory

The proposed hardware path adds a Raspberry Pi edge node, light/temperature sensors,
accelerometer and SDR to the local model/orchestration host. Data needs device IDs,
timestamps, units, calibration, baseline/noise estimates and experiment references.
Reality Debugger should test hypotheses against those measurements.

No sensor drivers, calibrated captures, synchronization results or novel physical
detection were recovered. An anomaly is a deviation under a defined model, not proof
of a multiverse. Timeline Simulator is a scenario/what-if proposal; Mission Console
is a proposed view of state, goals, evidence and pending actions.
