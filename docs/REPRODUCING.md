# Reproduce the recovered modules

Run commands from the repository root unless otherwise stated. Genesis,
local-first, Skills and the mock voice harness are dependency-light Python 3.11+
prototypes. The complete verification environment below is **Python 3.12+**
(the captured NumPy dependency requires it); it was tested on Python 3.12.14.

## Full verification environment

```bash
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in PowerShell or
`source .venv/bin/activate` on Linux/macOS, then:

```bash
python -m pip install -r requirements-verify.txt
python scripts/verify_workspace.py
```

The runner launches each suite with a separate `PYTHONPATH`. Do not run an
unqualified `pytest` across the whole checkout: historical packages intentionally
keep duplicate module and test names. Do not install all `eaon` packages into one
environment. Per-module README commands assume that module's own folder/environment.

## Genesis SELF

```bash
python scripts/run_module.py genesis --memory ./data/demo.jsonl think "I think EAON needs a source. Verify the claim." --json
python scripts/run_module.py genesis --memory ./data/demo.jsonl recall "EAON" --json
python scripts/run_module.py genesis --memory ./data/demo.jsonl verify --json
```

`./data/demo.jsonl` resolves under `modules/genesis/`. Separate invocations read the
same journal. This is local recall, not the full planned continuity kernel.

## Local-first documents

```bash
python scripts/run_module.py local-first --db data/demo.db ingest examples/seed.md
python scripts/run_module.py local-first --db data/demo.db ask "Does evidence tracking improve auditability?"
python scripts/run_module.py local-first --db data/demo.db status
```

Source paths resolve under `modules/local_first/`; use an absolute path for other
local documents. `ask` probes loopback Ollama and otherwise uses extractive evidence.
PDF support is optional; scanned documents require OCR outside this prototype.

## Voice harness

```bash
python scripts/run_module.py voice run --manifest examples/manifest.csv --output runs/smoke --adapter mock
python scripts/run_module.py voice verify runs/smoke/state-journal.jsonl
```

No microphone/WAV files are needed for this synthetic run. Use
[the later protocol](topics/VOICE_AND_SAFETY.md) before implementing a real adapter.

## MetaBench

With the verification dependencies installed:

```bash
python scripts/run_module.py metabench run --provider mock --model perfect-mock --cases 24 --seed 42 --output-dir results/smoke
```

The historical mock fixture is under `benchmarks/metabench/fixtures/`. New reports
are generated under that module's `results/`, excluded from Git. A real Ollama run
is an optional local experiment, not performed during consolidation:

```bash
python scripts/run_module.py metabench run --provider ollama --model qwen3:8b --cases 24 --seed 42
```

Use a model actually installed on the target machine. Do not compare mock latency
with real inference or compare different seeds/corpora as if they were identical.

## Skills and deterministic verification

```bash
python scripts/run_module.py skills
python scripts/run_module.py bhidt-demo
```

The BHIDT demo regenerates its dedicated `integrations/bhidt/examples/output/demo-v04`
directory; keep personal experiments elsewhere. It produces a report from 101
snapshots of a toy model. Read-only adapter functions are in `engine/eaon_adapter.py`.

## Knowledge ingestion

Root tests use local fixtures. Actual network ingestion is separate and requires
intentional API configuration:

```bash
python -m scripts.ingest_openalex --help
```

See [INGESTION_V0_1.md](INGESTION_V0_1.md) for the recovered command interface.
Ingestion does not yet populate a connected relation graph automatically.

## Cognitive Twin API

Follow [its README](../modules/cognitive_twin/README.md) from
`modules/cognitive_twin/`. Docker, PostgreSQL and the images specified there are
required. Host ports are bound to `127.0.0.1`. The seed is synthetic.

Only helper tests and API schema construction were checked here. The database,
container images, migrations and end-to-end API behavior still need a real run.

## Original INTEL CLI

The root `main.py`, `config/`, `core/`, `adapters/` and `utils/` retain their original
behavior. See the [historical README](legacy/README_INTEL_2_0.md) and
[current limitations](PROJECT_STATUS.md). `requirements.txt` is the original broader
dependency list; `requirements-verify.txt` is the captured lightweight test environment.

For a configuration-only stats check, disable external adapters in the environment:
`INTEL_ENABLED=false`, `REDIS_ENABLED=false`, `SLACK_ENABLED=false`, `JIRA_ENABLED=false`,
then run `python main.py --stats`. Normal prompt execution can call configured
services; no such live calls were used to validate this consolidation.
