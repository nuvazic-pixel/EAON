# EAON — Edge AI Orchestration Node

Local-first orchestration, evidence-backed memory, Reality Debugger and reproducible
verification. EAON is the umbrella for these experiments and their next integration.

**Consolidated on 20 September 2026.** This repository collects the existing INTEL
runtime, the Knowledge Gap branch, recovered prototype source and project decisions
previously spread across conversations. The modules run independently; they are
not yet one fully integrated assistant.

[Starea proiectului în română](docs/PROJECT_STATUS_RO.md) ·
[Verified status](docs/PROJECT_STATUS.md) · [History](docs/HISTORY.md) ·
[Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md)

## Start with the SELF loop

Python 3.11+; Genesis needs only the standard library:

```bash
git clone https://github.com/nuvazic-pixel/EAON.git
cd EAON
python scripts/run_module.py genesis think "I want EAON to remember ideas and check assumptions."
python scripts/run_module.py genesis recall "ideas"
python scripts/run_module.py genesis verify
```

This classifies input, retrieves local memory, labels assumptions/risks/tests,
creates a deterministic council-style response and appends hash-linked JSONL records.
It does not call an LLM or execute its suggested next action. The default journal is
`modules/genesis/data/memory.jsonl`, excluded from Git.

## Recovered components

| Component | Location | What exists |
|---|---|---|
| INTEL orchestration 2.0 | [core](core/), [adapters](adapters/) | Keyword intent, Ollama calls, threat enrichment, risk modes, optional Slack/Jira |
| Knowledge Gap + ingestion 0.1 | [knowledge](knowledge/), [ingestion](ingestion/) | Provenance records, structural gaps, OpenAlex adapter, SQLite store |
| Genesis SELF 0.2 | [modules/genesis](modules/genesis/) | JSONL memory, retrieval, Reality Debugger, deterministic council, CLI |
| Local-first 0.1 | [modules/local_first](modules/local_first/) | Local documents → source evidence → SQLite → extractive/Ollama response |
| Skills 0.1 | [modules/skills](modules/skills/) | Five skill definitions, keyword routing, selected context loading |
| Cognitive Twin Genesis 0.1 | [modules/cognitive_twin](modules/cognitive_twin/) | FastAPI/PostgreSQL graph, evidence, hypotheses, feedback, snapshots |
| Voice C3/A1/B2 | [benchmarks/voice](benchmarks/voice/) | RO/DE/EN scoring, wake metrics, stage latencies, State Journal |
| MetaBench 0.1 | [benchmarks/metabench](benchmarks/metabench/) | Seeded cognitive tasks, mock/Ollama adapters, JSON/HTML reports |
| BHIDT verification 0.4 | [integrations/bhidt](integrations/bhidt/) | Recompute vs journal, fingerprint, four verdicts, EAON evidence adapter |
| EAON-Red | [research/eaon_red](research/eaon_red/) | Offline security-benchmark search source; SDK not bundled |
| Cognitive graph schema | [schemas/cognitive_graph_v0_1.json](schemas/cognitive_graph_v0_1.json) | Reusable schema without the populated personal profile |

Versions belong to their original components. INTEL `2.0`, SELF `0.2`, local-first
`0.1` and BHIDT `0.4` are not a single linear EAON release sequence.

## Other entry points

```bash
# Local documents and SQLite; probes local Ollama by default
python scripts/run_module.py local-first ingest examples/seed.md
python scripts/run_module.py local-first ask "Does evidence tracking improve auditability?"

# Skill selection demo; no model invocation
python scripts/run_module.py skills

# Synthetic voice harness, not a microphone/ASR measurement
python scripts/run_module.py voice run --manifest examples/manifest.csv --output runs/smoke --adapter mock
python scripts/run_module.py voice verify runs/smoke/state-journal.jsonl
```

The launcher selects a separate process, import root and working directory for each
package. Relative input/output paths resolve inside that module. Several historical
packages are named `eaon`; do not install them together in one environment.
See [reproduction instructions](docs/REPRODUCING.md) for dependencies and other modules.

## Verification

Use Python 3.12+ for the complete captured verification environment:

```bash
python -m venv .venv
# Activate .venv for your operating system, then:
python -m pip install -r requirements-verify.txt
python scripts/verify_workspace.py
```

**40 existing tests passed across seven isolated suites.** See the
[verification report](docs/VERIFICATION.md) for exact checks and limits.
Mock tests do not establish live speech accuracy, model quality, database deployment
or real-world safety.

## Project direction

The next integration is a continuity kernel: confirmed memory, hypotheses and
unknowns; project state cards; one active goal; bounded tasks; retrieval before
reasoning; verification and checkpoint after action.

The [voice/interlock protocol](docs/topics/VOICE_AND_SAFETY.md),
[memory design](docs/topics/MEMORY_AND_CONTINUITY.md),
[integration register](docs/topics/INTEGRATIONS.md) and
[research layer](docs/topics/RESEARCH.md) preserve the agreed updates and their
implementation status. No consciousness, AGI, multiverse detection or universal
scientific-discovery capability is claimed.

## Provenance and privacy

[Recovery notes](docs/RECOVERY.md) describe sources, unavailable pieces, privacy
edits and preserved Git history. The [artifact manifest](docs/recovery/artifacts.json)
records archive and source-file hashes. Private memories, recordings, credentials,
populated personal graphs and generated caches are excluded.

The April baseline used **Emergent Autonomous Orchestration Network**. Its
[historical README](docs/legacy/README_INTEL_2_0.md) is retained; the current project
name is **Edge AI Orchestration Node**.
