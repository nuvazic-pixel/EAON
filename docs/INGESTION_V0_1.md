# EAON Knowledge Ingestion v0.1

This is the first executable path from public scientific metadata into EAON's knowledge layer.

## Pipeline

```text
OpenAlex API
    -> normalized OpenAlexWork
    -> deterministic ClaimExtractor
    -> SQLite KnowledgeStore
    -> later: relation builder / contradiction detector / gap detector
```

## Why this version is intentionally small

The first objective is not to claim scientific discovery. It is to establish a reproducible, inspectable ingestion path that can be benchmarked. The heuristic claim extractor is a baseline and must not be treated as a scientific truth extractor.

## Run

Set an OpenAlex API key in the environment when required by your OpenAlex plan/configuration:

```bash
export OPENALEX_API_KEY="..."
python scripts/ingest_openalex.py "neuroimmunology" --from-year 2000 --to-year 2010 --max-works 100
```

Optional identity:

```bash
export OPENALEX_MAILTO="you@example.com"
```

The default SQLite database is written to `data/eaon_knowledge.db`.

## Definition of done for v0.1

- fetch a bounded OpenAlex result set
- reconstruct available abstracts
- normalize bibliographic metadata
- extract inspectable baseline claims
- persist works and claims without duplicates
- expose repeatable tests

## Next milestone

Replace or augment the heuristic extractor with an orchestrated structured-JSON LLM extractor, then build explicit claim-to-claim relations. The first benchmark will use a historical cutoff so the system cannot see later discoveries.
