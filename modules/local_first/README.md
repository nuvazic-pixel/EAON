# EAON Local-First — v0.1

EAON (**Edge AI Orchestrator Node**) is a small, inspectable prototype for private,
evidence-grounded AI orchestration. It runs without a cloud API. A local Ollama
model improves synthesis when available; a deterministic extractive path keeps the
system useful when it is not.

This is the first working spine for the larger system:

`local sources → atomic claims → SQLite memory → routing → answer → Reality Debugger → audit trail`

It deliberately does **not** claim consciousness, silently browse the web, invent
paper metadata, or treat model output as truth.

## What works now

- local `.txt`, `.md`, and optional `.pdf` ingestion;
- SHA-256 source deduplication;
- conservative claim extraction with exact source evidence;
- persistent, inspectable SQLite memory;
- retrieval based on local evidence;
- optional generation through a local Ollama model;
- deterministic fallback without an LLM;
- Reality Debugger warnings for weak, contradictory, or single-source evidence;
- run history and full JSON export;
- tests that exercise ingestion, deduplication, retrieval, fallback, and export.

## Quick start (Windows / PowerShell)

```powershell
cd eaon-local-first
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .

eaon ingest examples/seed.md
eaon ask "Does a local-first architecture protect private context?"
eaon status
eaon export eaon-backup.json
```

The same commands work on Linux/macOS after activation with
`source .venv/bin/activate`.

### Optional local LLM

Install Ollama separately, then pull a model:

```powershell
ollama pull qwen3:8b
eaon --model qwen3:8b ask "Does evidence tracking improve auditability?"
```

No Ollama connection is required. If Ollama or the selected model is absent, EAON
returns the matching local evidence instead of failing or calling a cloud service.

### Optional PDF support

```powershell
pip install -e ".[pdf]"
eaon ingest path/to/paper.pdf
```

Scanned PDFs need OCR first; this prototype reads embedded text only.

## Output contract

Every `ask` result contains:

- `answer`: local synthesis or extracted evidence;
- `route`: backend selected and the reason;
- `reality_check`: verdict, confidence-like coverage score, and warnings;
- `evidence`: the claims and source IDs used;
- `run_id`: link to the local audit record.

The Reality Debugger score measures evidence coverage inside EAON. It is **not** a
probability that a statement is objectively true.

## Test it

```powershell
python -m unittest discover -s tests -v
```

`pytest -q` also works after `pip install -e ".[dev]"`.

Or run the zero-install smoke test after `pip install -e .`:

```powershell
eaon --db data/demo.db ingest examples/seed.md
eaon --db data/demo.db ask "Does evidence tracking improve auditability?"
```

## Architecture boundaries

This v0.1 makes the privacy boundary explicit:

- data and run history stay in the SQLite file selected with `--db`;
- Ollama is contacted only at `127.0.0.1` by default;
- there is no OpenAI SDK, API key, telemetry, web fetch, or hidden upload;
- export is explicit and user-triggered.

The original v2.1 paper prototype was not used as-is because its tools were mocks,
its fallback generated generic pseudo-insights, its benchmark measured execution
rather than answer quality, and part of its learning path referenced a missing
method. The useful concepts—paper evidence, memory, routing, evaluation, and audit—
are retained here with working local implementations.

## Next build slices

1. **Memory & evolution:** explicit memory types, temporal changes, corrections,
   retention rules, and import with conflict handling.
2. **Cognitive patterns:** decisions, recurring concepts, energy drains, and
   cross-domain links without turning the twin into a work biography.
3. **Knowledge graph:** claim relationships, source resolution, contradiction and
   gap hunters, then the cross-domain scout.
4. **Scientific validation:** fixed historical corpus, time cutoff, hidden later
   discoveries, scored reconstruction, and a real baseline.
5. **Reality Debugger:** skeptic role whose job is to break a hypothesis, followed
   by novelty audit and bounded experiment proposals.

The next sensible 30–60 minute deliverable is slice 1: add typed memories and a
visible correction/evolution timeline on top of the existing SQLite schema.
