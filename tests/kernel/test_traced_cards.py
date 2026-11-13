"""Reachable counterevidence must quarantine, then explicitly resolve state."""
from dataclasses import replace
from hashlib import sha256
import json
import sqlite3
from unittest.mock import patch

import pytest

from core.orchestrator import Orchestrator
from core.project_context import ProjectContext, ProjectContextError
from core.telemetry import TelemetryRecorder
from eaon_kernel import ConflictError, ContinuityKernel, IntegrityError, SourceRef, ValidationError
from eaon_kernel.cards import FactClaim, MemoryCard
from eaon_kernel.kernel import LEGACY_POLICY, POLICY, POLICY_HASHES, canonical, event_hash


def card(value="available", *, subject="fixture-resource", predicate="state"):
    body = "Synthetic raw trace: resource state is " + value + "."
    source = SourceRef("trace-" + value, "fixture://raw-trace/" + value, body, sha256(body.encode()).hexdigest())
    return MemoryCard("Resource state is " + value, source, (0, len(body)), "succeeded",
                      "synthetic-human-review", FactClaim(subject, predicate, value))


@pytest.fixture
def store(tmp_path):
    kernel = ContinuityKernel.create(tmp_path / "traced.db")
    kernel.create_project("p", "Synthetic reachability project")
    return kernel


def quarantine(kernel, key="evidence:resource"):
    kernel.record_memory_card("p", key, card("available"), status="confirmed")
    kernel.report_counterevidence("p", key, card("absent"), expected_revision=1,
                                  fault_origin="synthetic-original-trace")


@pytest.mark.parametrize("field", ["source_trace", "evidence_span", "outcome", "derived_by", "revocation_state"])
def test_trace_provenance_fields_are_required(field):
    payload = card().to_dict()
    del payload[field]
    with pytest.raises(ValidationError):
        MemoryCard.from_dict(payload)


@pytest.mark.parametrize("span", [(-1, 1), (0, 0), (0, 100000), (True, 2), [0, 1]])
def test_evidence_span_must_address_nonempty_captured_trace_characters(span):
    with pytest.raises(ValidationError):
        replace(card(), evidence_span=span)


def test_source_hash_and_caller_identity_are_validated_before_append(store):
    before = store.verify()
    payload = card().to_dict()
    payload["source_trace"]["sha256"] = "0" * 64
    with pytest.raises(ValidationError):
        MemoryCard.from_dict(payload)
    with pytest.raises(ValidationError):
        replace(card(), derived_by="")
    with pytest.raises(ValidationError):
        store.record_memory_card("p", "evidence:bad", payload)
    assert store.verify() == before


def test_procedural_memories_require_traced_cards_under_current_policy(store):
    before = store.verify()
    with pytest.raises(ValidationError):
        store.record_memory("p", "skill:unsafe-procedure", "Use this procedure", sources=(card().source_trace,))
    assert store.verify() == before
    store.record_memory_card("p", "skill:approved-fixture", card(), status="hypothesis")
    memory = store.recover("p")["memories"]["skill:approved-fixture"]
    assert memory["card"]["source_trace"] == card().source_trace.to_dict()
    assert memory["card"]["evidence_span"] == list(card().evidence_span)


def test_typed_conflict_is_quarantined_and_blocks_inference_without_tools(store, tmp_path):
    quarantine(store)
    memory = ContinuityKernel(store.path).recover("p")["memories"]["evidence:resource"]
    assert memory["lifecycle"] == "quarantined" and memory["revision"] == 2
    assert memory["card"]["revocation_state"] == "quarantined"
    incident = memory["incident"]
    assert incident["fault_origin"] == "synthetic-original-trace"
    assert incident["contradicting_evidence"]["claim"]["value"] == "absent"
    assert incident["state_contaminated"] and not incident["state_restored"]
    assert incident["control_triggered"] == "quarantine_and_block_context"
    assert incident["final_output_origin"] == "kernel:memory.contradicted"
    context = ProjectContext(store.path, "p")
    with pytest.raises(ProjectContextError, match="^context_state_contaminated$"):
        context.prepare("Can I use the resource?")
    orchestrator = Orchestrator(local_only=True, context_session=context,
                                telemetry=TelemetryRecorder(tmp_path / "telemetry.jsonl"))
    with patch("core.ollama_client._request") as model, \
         patch.object(orchestrator, "_enrich_intel") as intel, \
         patch.object(orchestrator, "_post_process") as tool_path:
        _, report = orchestrator.run("Can I use the resource?", source="text")
    assert not report.ok and report.error == "context_state_contaminated"
    assert report.output_text is None
    model.assert_not_called()
    intel.assert_not_called()
    tool_path.assert_not_called()


@pytest.mark.parametrize("counter", [card("available"), card("absent", subject="other-resource"), card("absent", predicate="other-state")])
def test_counterevidence_requires_same_typed_claim_with_different_value(store, counter):
    store.record_memory_card("p", "evidence:resource", card(), status="confirmed")
    before = store.verify()
    with pytest.raises(ValidationError):
        store.report_counterevidence("p", "evidence:resource", counter, 1, "synthetic-fault")
    assert store.verify() == before


def test_normal_updates_cannot_remove_a_card_or_bypass_contamination(store):
    store.record_memory_card("p", "evidence:resource", card(), status="confirmed")
    before = store.verify()
    with pytest.raises((ConflictError, ValidationError)):
        store.record_memory("p", "evidence:resource", "Replace traced card with plain text", expected_revision=1)
    assert store.verify() == before
    store.report_counterevidence("p", "evidence:resource", card("absent"), 1, "synthetic-fault")
    before = store.verify()
    with pytest.raises((ConflictError, ValidationError)):
        store.record_memory("p", "evidence:resource", "Ignore counterevidence", expected_revision=2)
    with pytest.raises((ConflictError, ValidationError)):
        store.record_memory_card("p", "evidence:resource", card(), expected_revision=2)
    assert store.verify() == before
    assert store.recover("p")["memories"]["evidence:resource"]["lifecycle"] == "quarantined"


def test_restoration_requires_counterclaim_and_persists_explicit_state_restored(store):
    quarantine(store)
    before = store.verify()
    with pytest.raises(ValidationError):
        store.restore_memory_card("p", "evidence:resource", card("available"), 2, "Still wrong")
    assert store.verify() == before
    store.restore_memory_card("p", "evidence:resource", card("absent"), 2,
                              "Human reviewed the synthetic countertrace", status="confirmed")
    recovered = ContinuityKernel(store.path).recover("p")
    memory = recovered["memories"]["evidence:resource"]
    assert memory["revision"] == 3 and memory["lifecycle"] == "active"
    assert memory["card"]["claim"]["value"] == "absent"
    assert not memory["incident"]["state_contaminated"]
    assert memory["incident"]["state_restored"] is True
    assert memory["incident"]["final_output_origin"] == "kernel:memory.restored"
    assert not store.context_card("p")["blocked_memories"]
    assert '"value":"absent"' in ProjectContext(store.path, "p").prepare("resource").serialized
    with sqlite3.connect(store.path) as db:
        kind, raw = db.execute("SELECT kind,payload FROM events ORDER BY seq DESC LIMIT 1").fetchone()
    assert kind == "memory.restored" and json.loads(raw)["policy_version"] == POLICY["version"]


def test_explicit_revocation_clears_contamination_without_restoring_wrong_claim(store):
    quarantine(store)
    store.revoke_memory("p", "evidence:resource", 2, "Drop the contaminated memory")
    memory = ContinuityKernel(store.path).recover("p")["memories"]["evidence:resource"]
    assert memory["lifecycle"] == memory["card"]["revocation_state"] == "revoked"
    assert memory["incident"]["state_restored"] and not memory["incident"]["state_contaminated"]
    assert memory["incident"]["resolution"] == "explicit_revocation"
    snapshot = ProjectContext(store.path, "p").prepare("resource")
    assert "evidence:resource" not in json.loads(snapshot.serialized)["project"]["memories"]


def test_valid_outer_event_hash_cannot_hide_corrupted_card_trace(store):
    store.record_memory_card("p", "evidence:resource", card(), status="confirmed")
    with sqlite3.connect(store.path) as db:
        seq, kind, raw, previous = db.execute("SELECT seq,kind,payload,previous_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        payload = json.loads(raw)
        payload["data"]["card"]["source_trace"]["sha256"] = "0" * 64
        raw = canonical(payload)
        digest = event_hash(seq, kind, raw, previous)
        db.execute("UPDATE events SET payload=?,hash=? WHERE seq=?", (raw, digest, seq))
        db.execute("UPDATE meta SET value=? WHERE key='head_hash'", (digest,))
    with pytest.raises(IntegrityError):
        store.verify()


def test_legacy_policy_checkpoint_is_read_then_v2_appends_without_rewriting_history(store):
    store.set_goal("p", "g", "Legacy goal")
    store.record_memory("p", "preference", "Keep project local", status="hypothesis")
    store.add_task("p", "t", "Legacy next task")
    store.checkpoint("p")
    # Simulate the previously published v1 writer: same plain-state transitions,
    # old policy envelope/hash binding, and its historical checkpoint state hash.
    with sqlite3.connect(store.path) as db:
        rows = db.execute("SELECT seq,kind,payload FROM events ORDER BY seq").fetchall()
        previous = "GENESIS"
        for seq, kind, raw in rows:
            payload = json.loads(raw)
            payload["policy_version"] = LEGACY_POLICY["version"]
            payload["policy_sha256"] = POLICY_HASHES[LEGACY_POLICY["version"]]
            raw = canonical(payload)
            digest = event_hash(seq, kind, raw, previous)
            db.execute("UPDATE events SET payload=?,previous_hash=?,hash=? WHERE seq=?", (raw, previous, digest, seq))
            previous = digest
        db.execute("UPDATE meta SET value=? WHERE key='head_hash'", (previous,))
        historical = db.execute("SELECT * FROM events ORDER BY seq").fetchall()
    reopened = ContinuityKernel(store.path)
    assert reopened.verify()["ok"]
    assert reopened.recover("p")["next_task"]["id"] == "t"
    reopened.record_memory_card("p", "skill:traced-procedure", card(), status="hypothesis")
    reopened.checkpoint("p")
    assert ContinuityKernel(store.path).verify()["ok"]
    with sqlite3.connect(store.path) as db:
        retained = db.execute("SELECT * FROM events WHERE seq<=? ORDER BY seq", (len(historical),)).fetchall()
        versions = [json.loads(raw)["policy_version"] for (raw,) in db.execute("SELECT payload FROM events ORDER BY seq")]
    assert retained == historical
    assert versions[:len(historical)] == [LEGACY_POLICY["version"]] * len(historical)
    assert versions[len(historical):] == [POLICY["version"], POLICY["version"]]


def test_valid_hash_cannot_downgrade_policy_after_a_v2_event(store):
    store.record_memory("p", "plain", "New plain observation")
    with sqlite3.connect(store.path) as db:
        seq, kind, raw, previous = db.execute("SELECT seq,kind,payload,previous_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        payload = json.loads(raw)
        payload["policy_version"] = LEGACY_POLICY["version"]
        payload["policy_sha256"] = POLICY_HASHES[LEGACY_POLICY["version"]]
        raw = canonical(payload)
        digest = event_hash(seq, kind, raw, previous)
        db.execute("UPDATE events SET payload=?,hash=? WHERE seq=?", (raw, digest, seq))
        db.execute("UPDATE meta SET value=? WHERE key='head_hash'", (digest,))
    with pytest.raises(IntegrityError):
        store.verify()
