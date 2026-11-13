# Evidence-linked memory and explicit recovery

New `MemoryCard` objects retain the captured `source_trace`, character offsets
in `evidence_span`, source `outcome` (`succeeded`, `failed`, `unknown`),
`derived_by` and `revocation_state`. A trace is a bounded UTF-8 text snapshot
with URI, identifier and SHA-256. Its digest identifies bytes, not truth or the
author. `derived_by` is a declared provenance label, not an identity signature.

`FactClaim(subject, predicate, value)` is an optional explicit structured
assertion. The counterevidence control only compares claims with the same
subject/predicate and distinct string values. It does not extract claims from
arbitrary language, prove entailment, or decide which source is correct.

```python
from hashlib import sha256
from eaon_kernel import ContinuityKernel, SourceRef
from eaon_kernel.cards import FactClaim, MemoryCard

def evidence(value):
    raw = "Synthetic trace: resource is " + value
    source = SourceRef(value, "fixture://" + value, raw,
                       sha256(raw.encode("utf-8")).hexdigest())
    return MemoryCard(raw, source, (0, len(raw)), "succeeded",
                      "explicit-reviewer", FactClaim("resource", "status", value))

# Use a new path; create refuses to overwrite an existing store.
kernel = ContinuityKernel.create("data/evidence-demo.db")
kernel.create_project("demo", "Evidence reachability")
kernel.record_memory_card("demo", "evidence:resource", evidence("available"))
kernel.report_counterevidence("demo", "evidence:resource", evidence("absent"),
                              expected_revision=1, fault_origin="synthetic-origin")
# Context and the project workflow bridge now block before inference/mock calls.
kernel.restore_memory_card("demo", "evidence:resource", evidence("absent"),
                           expected_revision=2, reason="Explicit review accepted the countertrace")
```

Quarantine persists the fault origin, captured counterevidence, contamination
flag, triggered control, restoration flag and actual kernel-handler origin.
The old record remains in the event history. Ordinary memory/card updates
cannot bypass quarantine. Explicit restoration requires a replacement card
resolving the recorded typed counterclaim; explicit revocation removes the
contaminated record from active state. Both require the current revision.

The local UI can explicitly revoke quarantined cards. Detailed traced-card
creation/restoration uses the Python API or explicit JSON files:

```sh
python -m eaon_kernel --db data/state.db card demo evidence:key card.json
python -m eaon_kernel --db data/state.db counterevidence demo evidence:key counter.json --expected-revision 1 --fault-origin reviewed-trace
python -m eaon_kernel --db data/state.db restore-card demo evidence:key corrected.json --expected-revision 2 --reason "Reviewed correction"
```

The JSON shape is `MemoryCard.to_dict()`: nested SourceRef, two-element span
array, declared outcome/derivation/revocation state and optional typed claim.
The basic UI editor handles ordinary notes/preferences; new `skill:` entries
and updates to traced cards require this richer contract. Neither kind of
memory grants tool authority. Counterfactual Anchor-style usefulness admission
is not implemented.

## Journal compatibility

Policy v2 reads the already-published v1 events and checkpoint hashes without
rewriting them. New events bind v2's policy hash. A prior v1-only application
cannot read new v2 events: retain a verified backup when upgrading, and use the
new reader for the updated store. No automatic migration or file replacement
occurs. Whole-store rollback/rewrite still needs a separately trusted head or
backup receipt; hashes in attacker-replaced files do not authenticate themselves.

`python scripts/demo_evidence_reachability.py` runs a synthetic false-claim,
counterevidence and recovery case. `core.workflow_bridge.run_project_workflow`
checks journal/quarantine and committed voice state before the fixed mock
runner. This remains an inert prototype, not an effectful tool executor.
