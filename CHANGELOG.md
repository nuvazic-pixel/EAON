# Changelog

## 2026-09-20 — EAON project consolidation

- Incorporate the existing Knowledge Gap/ingestion branch with its original commits.
- Recover Genesis SELF, local-first evidence memory, Skills, Cognitive Twin API,
  voice C3, MetaBench, BHIDT v0.4/EAON adapter and EAON-Red source.
- Add a module launcher and isolated verification runner; 40 existing tests pass.
- Fix original INTEL startup by exporting its existing mode/intent constants.
- Add project history, architecture, evidence-based status, continuity and voice
  specifications, integration/research register, roadmap and recovery manifest.
- Replace private Twin seeds with synthetic examples; publish only the reusable
  cognitive graph schema; bind Twin host ports to loopback and ignore runtime data.

This is a repository consolidation, not a new unified runtime release. Component
version numbers retain their original meanings. See [verification](docs/VERIFICATION.md)
and [known limits](docs/PROJECT_STATUS.md).

## 2026-08-10–11 — Knowledge Gap branch

Provenance models, structural detectors, research architecture, OpenAlex ingestion,
candidate claim extraction, SQLite, CLI and two tests. Previously on
`feature/knowledge-gap-engine`, ending at `971fc49`.

## 2026-04-10 — INTEL baseline

Initial `89ee79f` commit: orchestration/routing, threat intelligence, cache,
configuration, logging and optional notification adapters.
