# Recovery scope and provenance

Consolidated 2026-09-19–20 for the owner's request to find EAON topics, collect
existing work and publish directly to `nuvazic-pixel/EAON`.

## Sources inspected

| Source | What was used |
|---|---|
| Git main `89ee79f` | Original INTEL files and README |
| Git `feature/knowledge-gap-engine`, `971fc49` | All 11 additional files and 11 original feature commits |
| `EAON_Genesis_v0.2_SELF.zip` | SELF source, examples, docs and tests |
| `EAON-local-first-v0.1.zip` | Local evidence source, tests and original Paper Integration audit |
| `EAON-C3-A1-B2.zip` | Voice harness, manifest and journal/metrics tests |
| `eaon-metabench-mvp.zip` | Benchmark source/tests and explicitly synthetic historical fixture |
| `eaon_skills_v01.zip` | Context routing, five skill packages, project-only summary files |
| `cognitive-twin-genesis-v0.1.zip` | API/database source, deployment files, tests; private seeds replaced |
| `cognitive_twin_v0_1.zip` | Reusable schema; populated profile excluded |
| `black-hole-info-twin-v0.4.zip` | EAON adapter, toy-engine dependencies and tests |
| `attack.py` | EAON-Red offline benchmark source |
| `markdown.md eingefügt` | Complete recovered Knowledge Gap discussion; reconciled against actual Git code |
| `Cognitive Twin Genesis.txt` | Saved browser-site publication, not its live source repository |
| Retrieved EAON conversations | Dated decisions/status for voice, Council, MCP, Azure, OS, continuity, observatory, verification and related modules |

[artifacts.json](recovery/artifacts.json) records original archive/file hashes,
per-file source hashes, destination paths and any published-file differences.
Archives are unpacked into reviewable source, rather than committed as opaque ZIPs.

## Publication edits

- Omitted Python caches and generated runtime outputs.
- Normalized trailing whitespace/final newlines in imported text where needed;
  Python syntax trees were unchanged, and original hashes remain in the manifest.
- Kept MetaBench's original oracle/mock reports under `fixtures/`, explicitly
  separated from measured model results.
- Replaced the Cognitive Twin's two private seed events with synthetic examples.
- Bound its Docker host ports to loopback; the recovered API has no authentication.
- Published the cognitive graph schema without personal nodes/edges/images/HTML.
- Added workspace `.gitignore`, launcher, isolated test runner, verification
  dependencies, source manifest and consolidated documentation.
- Preserved the original INTEL README as historical documentation and replaced the
  root README with the actual current inventory.
- Fixed an existing INTEL startup failure by exporting `MODE_CONFIGS` and
  `INTENT_PRIORITY` from `config/__init__.py`; both already existed in constants
  but were imported through the package by the core. The CLI stats command now starts.

## Search coverage and missing pieces

Discovery used broad EAON/Edge AI Orchestration Node searches, title searches for
EAON/cognitive/reality/orchestration/Sherpa artifacts and targeted retrieval for
the gaps. Search returns selected relevant records, not a guaranteed exhaustive
export of every historical chat. The history covers the relevant accessible
sources found; missing code is listed explicitly instead of reconstructed and
presented as old work.

Not recovered: original Porcupine/Whisper/Piper voice package, Council server,
MCP bridge source, full Sherpa wrapper/interlock scripts, continuity Phase 2 kernel,
Azure deployment, EAON Verify runtime and physical-sensor software/logs.

The MetaBench `.tar.gz` is an alternate packaging format; the ZIP is the imported
source. UI/profile media are cataloged in [integrations](topics/INTEGRATIONS.md),
not republished with personal content. FTQC and GenCAD remain separate projects;
their mentions do not establish an implemented EAON integration.

## Evidence hierarchy

Actual source and reproduced tests take precedence over celebratory completion
messages. A saved artifact proves that code exists, not that every deployment or
hardware claim was measured. A plan remains a plan even when an earlier response
called it complete. The latest BHIDT v0.4 artifact, for example, supersedes earlier
retrieval that found only its proposed adapter.

## Git handling

The local branch fast-forwarded through Knowledge Gap's original commits before
the consolidation commit. Existing core/adapters/utils source was retained;
the config change is limited to the missing exports described above.
Direct publication uses a normal fast-forward update, not a force push. Live
notifications, models, microphones and external intelligence APIs were not invoked.
