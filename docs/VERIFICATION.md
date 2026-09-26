# Consolidation verification — 2026-09-20

Environment: Python **3.12.14**, Linux, isolated virtual environment with
`requirements-verify.txt`. No model weights, GPU, microphone, containers or live
notification/intelligence services were used.

## Existing test suites

Executed through `python scripts/verify_workspace.py`, with each package in its
own process/import root:

| Suite | Tests passed | What it exercises |
|---|---:|---|
| Knowledge ingestion | 2 | Abstract reconstruction, normalization, extraction and SQLite persistence |
| Genesis SELF | 5 | Routing/reality labels, local memory, tamper detection and orchestration |
| Local-first | 2 | Ingestion/deduplication/query/fallback and export |
| Voice C3 | 2 | Journal tamper detection, WER and wake metric helpers |
| MetaBench | 8 | Parsing, scoring, generated suites and comparison |
| Cognitive Twin helpers | 3 | Hash determinism/content sensitivity and domain-label policy |
| BHIDT v0.4 | 18 | Physics toy helpers, provenance, journal/replay, fingerprints and recomputation states |
| **Total** | **40** | Existing artifact/branch tests; no hardware performance claims |

## Entrypoint and integration smoke checks

| Check | Observed result |
|---|---|
| Genesis `think` → separate `recall` process → `verify` | Stored records recovered; chain reported valid |
| Local-first `ingest` → `ask`, absent model | Retrieved source evidence and `extractive` backend |
| Voice mock manifest | Six samples, 42 journal events; chain verification passed |
| MetaBench mock, 24 cases, seed 42 | JSON/HTML generated; oracle/mock accuracy 1.0 |
| Skills launcher | Five demo tasks processed; selected contexts loaded |
| BHIDT demonstration | `MATCH`, 101 snapshots compared, max absolute/relative error 0.0 |
| Cognitive Twin OpenAPI construction | Imported app and generated schema with 11 paths, without database startup |
| EAON-Red import | `AttackAlgorithm` imported using inspection fallbacks; no benchmark execution |
| Original INTEL `main.py --stats` | Passed with external adapters disabled after the missing-export fix |

Mock transcription, mock latency and oracle benchmark scores are synthetic. BHIDT
agreement confirms software recomputation for its toy model, not a physical measurement.

## Defect found and fixed

The original root CLI could not import `MODE_CONFIGS` (and its router also needed
`INTENT_PRIORITY`) from `config`. Both constants already existed. Added those two
package exports and reran the failing `main.py --stats` command successfully. The
workspace verifier now includes that startup check.

No full-suite rerun was needed for the export-only fix: the failed startup path was
rechecked directly. Imported module implementations tested above were unchanged.

## Voice policy update — 2026-09-26

From the repository root, `PYTHONPATH=benchmarks/voice/src python -m unittest
discover -s benchmarks/voice/tests -q` passed **14** tests. The added tests cover
startup fault injection (wrong executor, connected registry, network unverified,
unarmed stop, unknown model, missing journal write), negative wake/TTS/model/tool
attempts, journal tampering and truncation, stop changes during a turn, and a
mock result failing its postcondition. The C3 mock manifest still returned six
samples; `eaon_c3 verify` accepted all **42** journal records. These results only
exercise the simulated policy and existing mock benchmark; they do not certify
outbound network isolation or live voice/hardware behavior.

Four `tests/test_gateway.py` cases also passed with external dependencies
installed into a separate scratch directory. They exercise exact model dispatch,
unknown/missing IDs, empty responses and a mocked Ollama connection failure.
No live model or network call was made.
The root `python main.py --stats` startup check also succeeded with those local
dependencies.

## Local launcher update — 2026-09-26

In a fresh Python 3.12 virtual environment, installed `requirements-local.txt` and
ran `python scripts/local_run.py`: four gateway tests, 14 voice tests, INTEL stats,
six mock samples and a valid 42-record journal passed. After installing
`requirements-verify.txt`, `python scripts/local_run.py --all-tests` passed all
seven isolated suites (**56 tests**), plus the CLI startup check. This run was on
Linux; the PowerShell commands are provided for Windows but have not been run on
Windows hardware. Neither run invoked a live model or microphone.

## Deliberately unverified

- Ollama/model quality, original Porcupine/Whisper/Piper pipeline and real Sherpa ASR.
- Microphone timing, wake-to-audio latency, false activations per hour, 8h/48h endurance.
- The full CAUC/privacy/safety-interlock live path; C3's policy tests are mock-only.
- PostgreSQL/container startup and end-to-end Cognitive Twin database/API behavior.
- Live OpenAlex corpus ingestion, knowledge-graph integration and novel discoveries.
- Slack/Jira delivery, threat-intelligence services and original missing INTEL tests.
- Original Council/MCP/Azure deployment, competition SDK, sensors and physical tools.
- GitHub Actions CI; these are local verification results.

Final packaging parsed 129 Python files, resolved all relative Markdown links,
checked artifact hashes and screened the publication file selection. Imported
whitespace normalization preserved Python syntax trees. Personal seeds/profile exports, raw journals,
recordings, model files, credentials and caches are excluded from the commit.
