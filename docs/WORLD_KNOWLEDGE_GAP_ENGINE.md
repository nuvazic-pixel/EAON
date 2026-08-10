# EAON World Knowledge Gap Engine

## Mission

Build a provenance-first research layer on top of EAON that continuously maps human knowledge, detects contradictions and structural gaps, proposes falsifiable bridges, and ranks them for human or machine investigation.

The system must **never equate absence of retrieved evidence with absence of evidence in the world**. Every gap is a scored candidate, not a truth claim.

## Three parallel knowledge lenses

A single graph is not enough. EAON should maintain three linked views:

1. **Reality / chronology graph** — what is claimed to happen, in what temporal order, and under which conditions.
2. **Discovery graph** — when humans published, observed, measured, or formalized each claim.
3. **Epistemic dependency graph** — which claims support, contradict, explain, depend on, generalize, or measure which other claims.

This separation prevents historical discovery order from being confused with causal or logical order.

## Domain lattice

Start broad and allow multiple classification paths rather than a rigid tree:

- Formal sciences
  - mathematics
  - logic
  - statistics
  - theoretical computer science
- Physical sciences
  - physics
  - astronomy / cosmology
  - chemistry
  - Earth sciences
- Life sciences
  - molecular biology
  - genetics
  - evolution
  - ecology
  - neuroscience
- Mind and behavior
  - cognitive science
  - psychology
  - linguistics
- Medicine and health sciences
- Engineering and technology
- Social sciences
  - economics
  - sociology
  - political science
  - anthropology
- Humanities
  - history
  - philosophy
  - archaeology
- Cross-domain systems
  - complexity
  - information theory
  - network science
  - AI

A claim can belong to several domains and several abstraction levels.

## Core record types

- `Source`: paper, book, dataset, standard, theorem, archival record, experiment report, etc.
- `Evidence`: the exact result or passage supporting a claim plus method and strength.
- `Claim`: normalized atomic assertion with conditions, confidence, temporal validity, assumptions, and provenance.
- `Relation`: typed edge between claims.
- `Gap`: candidate contradiction, missing bridge, unsupported assumption, untested prediction, cross-domain disconnect, temporal inconsistency, or source-coverage hole.

## Pipeline

```text
Sources
  ↓
Acquisition adapters
  ↓
Deduplication + identity resolution
  ↓
Document parsing / sectioning
  ↓
Atomic claim extraction
  ↓
Entity + concept normalization
  ↓
Evidence linking
  ↓
Knowledge graphs
  ↓
Deterministic structural detectors
  ↓
LLM hypothesis agents
  ↓
Adversarial critic / falsifier agents
  ↓
Novelty + coverage search
  ↓
Gap ranking
  ↓
Human review / experiment design / retrospective validation
```

## EAON agent roles

EAON remains the orchestrator. It routes subtasks to specialized workers:

- **Collector** — discovers and fetches candidate sources.
- **Resolver** — deduplicates documents, authors, entities, concepts, versions and translations.
- **Claim Extractor** — converts prose/results into minimal claims with conditions.
- **Evidence Auditor** — verifies whether evidence actually supports the normalized claim.
- **Graph Builder** — writes typed graph edges.
- **Contradiction Hunter** — finds incompatible claims under matching conditions.
- **Bridge Hunter** — searches for A→B→C structures with an unexplained or untested A↔C bridge.
- **Cross-Domain Scout** — looks for equivalent mechanisms described using different vocabularies.
- **Historian** — separates event chronology from publication/discovery chronology.
- **Mathematical Verifier** — routes formal claims to theorem provers / symbolic tools where possible.
- **Statistician** — checks effect sizes, uncertainty, replication and statistical assumptions.
- **Skeptic** — attacks every candidate gap and hypothesis.
- **Novelty Auditor** — aggressively searches for prior art before a gap is promoted.
- **Experiment Designer** — proposes falsifiable tests only after novelty and provenance checks.

## Gap promotion gates

A candidate may move from `candidate` → `interesting` → `research-grade` only if it passes:

1. provenance coverage check;
2. terminology / synonym expansion;
3. cross-language search where relevant;
4. prior-art search;
5. retraction / correction check;
6. adversarial critic pass;
7. condition compatibility check;
8. independent model agreement or deterministic verification;
9. reproducible score and rationale.

## Initial source strategy

Do not attempt to mirror "the whole Internet". Start with large structured scholarly indexes for discovery and provenance, then attach legal/open full text where available.

Suggested adapters:

- OpenAlex — broad work/authorship/citation metadata and concepts/topics.
- Crossref — DOI-centric publication metadata, updates and retraction-related metadata.
- Semantic Scholar — citation graph and semantic scholarly metadata.
- arXiv / PubMed / Europe PMC / domain repositories — domain-specific abstracts/full text where permitted.
- Wikidata — entity normalization, not primary scientific evidence.
- Standards bodies, public datasets, theorem libraries and archival corpora via dedicated adapters.

## Storage architecture

Use different stores for different workloads:

- relational store (PostgreSQL) for canonical source/claim/evidence records and audit state;
- graph store (Neo4j/Memgraph or PostgreSQL graph extension initially) for multi-hop relations;
- vector index (pgvector/Qdrant) for semantic retrieval and terminology bridging;
- object storage for source snapshots and extracted artifacts;
- Redis only for cache/queues, not as the source of truth.

The first prototype can remain dependency-light and in-memory; storage adapters come after the data model stabilizes.

## Retrospective validation: the critical benchmark

To test whether EAON discovers rather than merely narrates:

1. choose a historical cutoff date `T`;
2. deny the engine all documents published after `T`;
3. construct its graph from knowledge available by `T`;
4. ask it to rank missing bridges and predictions;
5. compare the top-ranked candidates with discoveries published in `T+1 ... T+n`;
6. separately measure false positives and already-known results missed by novelty search.

Metrics should include precision@K, rediscovery rate, time-to-discovery advantage, provenance completeness, false novelty rate and calibration of confidence.

## First vertical slice

The code under `knowledge/` implements provenance-aware records plus deterministic detectors for:

- explicit contradictions;
- unsupported assumptions;
- missing two-hop bridges;
- unsupported high-confidence cross-domain edges;
- temporal inconsistencies.

This is deliberately not LLM-first. Models may propose claims and relations, but deterministic code decides what structural pattern was detected and preserves an auditable rationale.

## Next implementation milestones

### M1 — Corpus ingestion
- OpenAlex adapter
- Crossref DOI enrichment
- normalized source IDs
- local snapshot cache

### M2 — Claim extraction
- JSON schema for atomic claims
- conditions / population / units / qualifiers
- evidence span anchoring
- uncertainty and method extraction

### M3 — Persistent graph
- canonical IDs
- entity resolution
- typed relations
- provenance traversal

### M4 — Multi-agent research loop
- bridge proposals
- adversarial critique
- prior-art / novelty audit
- hypothesis scoring

### M5 — Retrospective benchmark
- cutoff-date corpus builder
- hidden-future evaluation
- metrics dashboard

### M6 — Domain expansion
Begin with two domains that have high-quality open corpora and measurable historical discoveries. Expand only after calibration.

## Design rule

EAON should optimize for **traceable discovery**, not impressive prose. A candidate insight without provenance, conditions, uncertainty and a falsification path is not promoted as a discovery.
