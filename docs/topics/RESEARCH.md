# Research, evaluation and deterministic evidence

## World Knowledge Gap Engine

The recovered branch implements provenance records and deterministic structural
detectors. Its original [architecture](../WORLD_KNOWLEDGE_GAP_ENGINE.md) separates
reality/chronology, discovery history and epistemic dependencies. Publication order
must not be treated as causal order.

Existing gap patterns: explicit contradiction, unsupported assumption, missing
two-hop bridge, unsupported high-confidence cross-domain relation and invalid time
range. `UNTESTED_PREDICTION` and `SOURCE_COVERAGE` are model categories, not completed
detectors. A candidate gap is absence in the represented graph, not proof of a gap
in all human knowledge. Heuristic confidence/novelty/impact/testability are not
empirically calibrated probabilities.

The [ingestion v0.1](../INGESTION_V0_1.md) source normalizes OpenAlex metadata/abstracts,
extracts candidate sentences and persists works/claims in SQLite. It does not yet
perform atomic subject/relation/object extraction, evidence auditing, entity
resolution or automatic relation building. Crossref/Semantic Scholar were proposed
additional adapters, not recovered code.

The next designed research path is structured claim extraction → relation builder
→ provenance/condition validation → gap candidates → skeptic → novelty search →
falsifiable experiment proposal. Mathematical claims can eventually use symbolic
verification/theorem provers; none is integrated here.

Retrospective validation was proposed with literature through 2010 and later
discoveries from 2011–2020, initially in two domains. Discussions ranged from a
100–1,000-paper pilot to 10,000–50,000 papers. These are proposed scales, not corpus
sizes already ingested. Measure precision@K, false novelty, coverage and calibration.
An additional evaluation risk is a model already trained on future discoveries;
a document cutoff alone does not remove that leakage.

## MetaBench MVP

The recovered suite generates reproducible cases for insufficient information,
contradictions, rule changes and error repair. It scores accuracy, confidence
calibration, abstention, recovery/adaptation, parse compliance and latency/tokens.

The original aggregate weights are 45% accuracy, 25% calibration, 15% abstention
and 15% recovery/adaptation. Keep component metrics visible; the aggregate is an
engineering score, not a measure of consciousness or general intelligence.

The retained July 13 fixture uses `perfect-mock`, seed 42 and 24 oracle-derived cases.
Its perfect scores and 1 ms synthetic latency are expected harness behavior.
The recovered Ollama adapter has not been benchmarked on the user's hardware here.
Persisting measured model profiles and using them for routing remains the next design.

## BHIDT v0.4 and EAON Verification Adapter

The actual recovered [source](../../integrations/bhidt/) includes the toy physics/
information engine, journal/replay, deterministic recomputation, comparator,
fingerprint and `EAONVerificationAdapter`. This updates the older conversation
snapshot where v0.4 was still a proposal.

| Verdict | Meaning |
|---|---|
| `MATCH` | Discrete fields agree; numeric differences are within the configured policy |
| `DRIFT` | Structure agrees but numeric tolerance is exceeded |
| `DIVERGENCE` | Fingerprint/identity/structure/discrete behavior differs |
| `UNVERIFIABLE` | Missing/malformed inputs or invalid journal prevent trusted verification |

The adapter exposes `verify_experiment`, `why_diverged`,
`compare_recorded_vs_recomputed`, `show_provenance`, `explain_transition`,
`show_assumptions`. It returns evidence structures rather than invented explanations.
Default tolerances are `abs_tol=1e-12`, `rel_tol=1e-10` for this toy engine, not
physical uncertainty estimates. Environment metadata is diagnostic; fingerprints
freeze model/config/constants/code/schema identity.

The Page transition in the demonstration is a property of the normalized toy model.
Reproducing it is a software-verification result, not a universal physical prediction.
The adapter is independently runnable; integration into the main EAON tool registry
and shared journal remains pending.

## EAON-Red

Recovered [source and scope](../../research/eaon_red/) implement trace-aware template
mutation, Go-Explore archive selection, snapshot/restore branches and replayable
prompt chains for the original authorized offline security benchmark. No live
system attack or SDK evaluation was performed in consolidation.

## Related external projects

FTQC Architecture Digital Twin v0.1/v0.2 exists as separate deliverables. Quantum
gates, surface-code assumptions, magic-state factories, routing, persistent in-flight
reservations and later finite-buffer/backpressure discussions belong to that
simulation track. Their detailed milestones were not revalidated by EAON's tests.
They do not establish a physical quantum processor or an EAON adapter.

GenCAD's reported Proof-to-Geometry flow is raw intent → SourceEvidenceGuard →
EngineeringSpec → CADReleaseGate → released parameters → CadQuery. Its source/tests
were not imported or revalidated here. The useful future EAON contract is to pass
only released engineering parameters to geometry generation and preserve the proof
report alongside the artifact.
