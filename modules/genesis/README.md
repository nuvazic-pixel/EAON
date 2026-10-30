# EAON Genesis v0.2 SELF

EAON is a local-first orchestration core for a personal cognitive digital twin.
This MVP is deliberately small: it classifies an input, runs it through a
Reality Debugger, retrieves relevant local memory, produces a council-style
response, and saves the run with provenance.

It does not claim consciousness. It is a structured memory and reasoning loop.

## What is inside

- `eaon/memory.py` - append-only JSONL memory with a SHA-256 hash chain.
- `eaon/router.py` - deterministic input classification.
- `eaon/reality_debugger.py` - FACT / ASSUMPTION / RISK / TEST extraction.
- `eaon/agents.py` - local council roles: Architect, Skeptic, Implementer, Judge.
- `eaon/orchestrator.py` - the SELF loop tying everything together.
- `eaon/cli.py` - command line entry point.
- `tests/` - focused tests for the core behavior.

## Quick start

From this folder:

```bash
python -m eaon.cli think "I want EAON to remember my AI ideas and turn them into next actions."
```

Use a custom memory file:

```bash
python -m eaon.cli --memory ./data/memory.jsonl think "EAON should detect assumptions before I act."
```

Recall memory:

```bash
python -m eaon.cli --memory ./data/memory.jsonl recall "assumptions"
```

Show recent records:

```bash
python -m eaon.cli --memory ./data/memory.jsonl snapshot
```

Run tests:

```bash
python -m unittest discover -s tests
```

## First principle

EAON should become the layer that routes thought into action:

```text
Input -> Router -> Memory -> Reality Debugger -> Council -> Next Step -> Memory
```

The first useful version is not an avatar and not a dashboard. It is a reliable
loop that remembers, checks, and proposes one concrete next step.

## Memory integrity

Every read, search, snapshot and append checks the complete hash chain before
using the loaded records. The SELF loop stops before the council runs if the
journal is invalid. It does not silently drop damaged records or append to a
broken chain. Missing and empty journals remain valid starting states.

The CLI exits with status 1 and a `memory_integrity_failed` error for a damaged
journal; `verify` also reports malformed records without a traceback. The journal
is left unchanged so it can be inspected or restored from a known-good backup.
Python callers can catch `eaon.memory.MemoryIntegrityError`.

The check covers the same in-memory snapshot returned to the caller, rather than
verifying one read and consuming a second read. This is still a single-writer
prototype: there is no cross-process write lock or external trusted checkpoint.
The hash chain detects inconsistent edits; it does not authenticate an attacker
who rewrites the whole chain or detect deletion of a valid suffix.
