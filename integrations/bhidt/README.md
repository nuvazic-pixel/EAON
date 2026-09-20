# Black Hole Information Digital Twin — v0.4

BHIDT v0.4 adds **deterministic recomputation verification** on top of the
v0.3 journal/replay engine.

The goal is not merely to replay stored output. The verifier regenerates the
experiment from its recorded configuration and compares fresh snapshots against
the journal.

## Verification states

### `MATCH`
All discrete fields agree and all numeric values are within the configured
floating-point tolerances.

### `DRIFT`
The experiment remains structurally equivalent, but at least one numeric field
exceeds the permitted tolerance.

### `DIVERGENCE`
Model behavior or experiment identity has changed: fingerprint mismatch,
snapshot-count mismatch, changed discrete state such as the dominant saddle, etc.

### `UNVERIFIABLE`
Verification cannot be trusted or completed: missing fingerprint, invalid
journal hash chain, missing manifest, unsupported/malformed configuration, etc.

## v0.4 architecture

```text
Config + Model + Constants + Source Code
                   |
                   v
       Reproducibility Fingerprint
                   |
                   v
           Recomputation Engine
                   |
            fresh snapshots
                   |
                   v
Recorded Journal -> Comparator
                   |
                   v
          Verification Report
 MATCH / DRIFT / DIVERGENCE / UNVERIFIABLE
                   |
                   v
          EAON Verification Adapter
```

## Single-writer invariant

One experiment directory has **one journal writer**.

```text
Physics / Information / EAON / UI
              |
              v
      Experiment Runner
      (single writer)
              |
              v
         events.jsonl
```

v0.4 does not add distributed locking. Multiple producers should eventually send
events to a single journal-owner/event-bus component instead of writing the file
concurrently.

## Reproducibility fingerprint

The manifest freezes:

- engine version
- snapshot schema version
- model + model version
- constants version + constants hash
- config hash
- initial-state hash
- executable model code hash
- expected snapshot count
- canonical serialization version
- runtime/environment metadata

Environment metadata is recorded for diagnosis. It is not itself a hard failure;
numeric differences are judged by the explicit float policy.

## Floating-point policy

Default comparator policy:

```text
abs_tol = 1e-12
rel_tol = 1e-10
```

These are **verification defaults for this toy engine**, not physics-derived
uncertainties. Each mismatch reports:

- recorded value
- recomputed value
- absolute error
- relative error
- configured thresholds
- first affected snapshot / journal sequence
- provenance when registered

## Scientific scope

The physical and information models are unchanged from the earlier prototype:

```text
M(tau)/M0 = (1-tau)^(1/3)
S_H(tau)  = 1 - (1-tau)^(2/3)
S_I(tau)  =     (1-tau)^(2/3)
S_rad     = min(S_H, S_I)
```

The Page transition near `tau = 0.6464466094` is a property of this normalized
toy model. It is not a universal physical Page-time prediction.

## EAON Verification Adapter

Deterministic evidence APIs now include:

```python
verify_experiment()
why_diverged()
compare_recorded_vs_recomputed()
show_provenance(field, seq)
explain_transition()
show_assumptions(model)
```

The adapter returns structured evidence. Natural-language explanation belongs
above this layer so EAON does not invent the underlying state.

## Run

```bash
python -m unittest discover -s tests -v
python examples/verification_demo_v04.py
```

The demo generates a `verification-report.json` alongside the experiment.
