# EAON Genesis v0.2 Architecture

## Goal

Build a local-first SELF loop that can:

1. accept a thought, problem, decision, or idea;
2. classify what kind of input it is;
3. retrieve useful memory;
4. separate facts from assumptions, risks, and tests;
5. synthesize a grounded response;
6. save the run with provenance.

## Core loop

```text
User input
  -> Router
  -> Memory search
  -> Reality Debugger
  -> Council roles
  -> Judge synthesis
  -> Append-only memory
```

## Modules

| Module | Responsibility |
| --- | --- |
| Router | Classifies input as idea, decision, risk, research, action, question, or reflection. |
| Memory | Stores JSONL records with timestamp, tags, metadata, previous hash, and content hash. |
| Reality Debugger | Extracts FACT, ASSUMPTION, RISK, and TEST items from the input. |
| Council | Produces deterministic role outputs without needing a cloud model. |
| Orchestrator | Coordinates the whole run and writes provenance. |

## Why JSONL first

The earlier Genesis direction used Docker, PostgreSQL, and pgvector. That is
the right long-term shape, but not the right first move if the goal is to keep
momentum. JSONL gives us:

- no installation blocker;
- readable memory;
- easy backup and sync;
- a direct migration path to PostgreSQL later.

## Upgrade path

| Stage | Add |
| --- | --- |
| v0.2 | Local JSONL memory, router, Reality Debugger, deterministic council. |
| v0.3 | Ollama adapter and multi-model role routing. |
| v0.4 | Vector memory, embeddings, contradiction detection. |
| v0.5 | FastAPI service and local dashboard. |
| v0.6 | Voice input/output and avatar layer. |
