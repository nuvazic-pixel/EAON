# Consolidation — 30 October 2026

This is an integration of existing public experiments and reproducible checks,
not a new unified EAON runtime release.

## Source provenance

The base is `main@36f2303686067c9f4b8e13c40114a0eca55ca818`.
The following existing branch work is included without replacing the root
UI, keyword router, exact-ID gateway or Ollama transport:

| Component | Public source commit | Included paths |
|---|---|---|
| CIE epistemic contracts v0.1 | `50b95f88a727d69abcb02e2a239e472482da3d42`, also in ENCR | `modules/cie`, `tests/cie` |
| ENCR decision-only policy v0.1 | `025fcb3b81a76afa68ac988eedbdbfb7a341e64a` | `modules/governance`, `tests/governance`, demo and specification |
| BioLab M0 | `bd2c0aac02117c18c3ba8594358dd4ce3fcfaf38` | `modules/biolab` plus launcher entry |

CIE is imported once, through ENCR's existing dependency. BioLab includes the
published correction of the literal newline in the generator signature.
Its README is reconciled with the actual strict config loader.
Per-file Git blob hashes are recorded in
[the import manifest](consolidation/imports-2026-10-30.json).

## Boundaries retained

- CIE evaluates typed records and provenance supplied by callers; it does not
  establish the independent truth or authenticity of those records.
- ENCR returns a decision only. No real OS operation, capability token,
  AppContainer runtime or physical action is introduced.
- BioLab uses synthetic observations only.
- The historical packages sharing the `eaon` import name remain isolated by
  the launcher and test runner. They are not installed together.
- JSONL, SQLite and PostgreSQL stores retain their separate formats.
- EAON-Gov remains a separate package and repository. Similar naming does not
  make it the same implementation as `modules/governance`.

## Deferred work with a concrete blocker

The adaptive router at `c354964` is not imported. Its executor passes
`ModelSpec.model` to `adapter.run()`, while the OpenAI adapter expects a
logical tier from `MODEL_BY_TIER`. A real provider integration would reject
that argument before making a request. The current unit tests do not cover
that composition. Cost/latency constraints and mandatory verifier behavior also
need integration-level acceptance tests before enabling it.

Later local Council and ENCR experiments are preserved in private local source
archives. They are not automatically published or substituted for the public
v0.1 contracts. They need a separate comparison and test review.

## Reproduction

Install the verification requirements in a dedicated environment, then run:

```sh
python scripts/verify_workspace.py
python scripts/run_module.py biolab smoke --count 100
python scripts/demo_encr.py
```

The verifier reports each suite and missing dependencies explicitly.
Mock and offline unit tests do not establish real model, microphone,
PostgreSQL, network containment or hardware behavior.

## Next integration acceptance

The continuity kernel remains a separate milestone. Before connecting an
executor, a synthetic two-session demonstration must preserve a sourced
decision, an explicit unknown and one next task across restart. Missing sources
must produce uncertainty; invalid journal integrity must stop use of the
affected memory. Migrations between stores must be explicit and reversible.
