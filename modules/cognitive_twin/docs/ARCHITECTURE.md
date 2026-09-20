# Personal Cognitive Twin — Genesis v0.1

## Mission

Build a local-first, longitudinal model of one person's cognitive evolution.

The system must distinguish:

1. **Observed events** — what was actually said/recorded.
2. **Evidence** — excerpts tied to immutable events.
3. **Graph assertions** — concepts and relationships.
4. **Hypotheses** — model inferences with confidence and alternatives.
5. **Temporal self** — snapshots, never a single timeless personality profile.

## Non-goal

This is **not** a professional/work twin, CV twin, productivity tracker, psychological diagnosis system, or personality clone.

Raw domains `work`, `professional`, and `employment` are rejected by default. A cognitive insight that originated in a workplace context must first be rewritten as a sanitized cognitive observation with workplace details removed.

## Genesis data flow

```text
SELF
  |
  v
Event ingestion
  |
  v
Append-only hash journal
  |
  +--> Evidence
  |
  +--> Nodes / Edges (cognitive graph)
  |
  +--> Hypotheses
  |
  +--> Self snapshots / timeline
```

## Trust hierarchy

```text
RAW EVENT > USER CORRECTION > EVIDENCE > GRAPH ASSERTION > HYPOTHESIS > SIMULATION
```

A hypothesis can never silently become a fact.

## Core invariants

- Raw events are immutable by application policy.
- Every journal event is chained to the previous event hash.
- Hypotheses carry confidence and may carry alternative interpretations.
- User rejection is preserved; it is not erased.
- The past is versioned, not overwritten.
- Cloud-model integration is intentionally absent from Genesis v0.1.

## Next layers

### v0.2 — SELF
Beliefs, questions, values, interests, contradiction tracking, richer Temporal Self.

### v0.3 — REFLECTION
Pattern engine, reflection agent, evidence explorer, idea resurfacing.

### v0.4 — EAON
Voice interface, context retrieval, automatic memory capture.

### v0.5 — REALITY
Reality Debugger and observation/prediction/outcome loops.

### v0.6 — SIMULATION
Decision simulations and explicit counterfactuals.
