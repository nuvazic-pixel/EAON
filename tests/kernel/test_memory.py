from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
import json
from types import SimpleNamespace

import pytest

from eaon_kernel import ContinuityKernel, EvidenceCandidate, SourceRef, ValidationError
from eaon_kernel.memory import KernelMemoryProvider, MemoryProviderRegistry, MemoryScope
from eaon_kernel.synapse import SynapseEvidenceProvider


def candidate(name="s", owner="alice", collection="c", body="local evidence", **kwargs):
    return EvidenceCandidate(SourceRef(name, "fixture://document#" + name, body, sha256(body.encode()).hexdigest()),
                             "fixture", owner, collection, **kwargs)


def registry(items, locality="local"):
    r = MemoryProviderRegistry()
    r.register("evidence", SimpleNamespace(query=lambda query, scope: items), locality=locality)
    return r


def test_admission_precedes_ranking_and_no_cross_owner_exposure():
    items = [candidate("wrong-owner", owner="bob", score=999), candidate("wrong-collection", collection="other", score=999),
             candidate("revoked", revoked=True), candidate("expired", expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()),
             candidate("allowed")]
    result = registry(items).query("evidence", "local", MemoryScope("alice", "p", collection_id="c"))
    assert [v["source"]["source_id"] for v in result["candidates"]] == ["allowed"]
    assert result["authority"] == "candidate_only"


def test_missing_required_evidence_or_budget_is_not_authorization():
    r = registry([candidate("a", body="required evidence larger than budget")])
    result = r.query("evidence", "evidence", MemoryScope("alice", "p", collection_id="c"), budget_chars=5, required_source_ids=("a", "b"))
    assert result["status"] == "unknown_required_fact"
    assert not result["all_required_evidence_present"]
    assert result["evidence_confidence"]["score"] == 0


def test_remote_privacy_gate_runs_before_provider():
    def never(*args):
        raise AssertionError("Provider must not receive the query")
    r = MemoryProviderRegistry()
    r.register("evidence", SimpleNamespace(query=never), locality="remote")
    with pytest.raises(ValidationError):
        r.query("evidence", "private", MemoryScope("alice", "p"))


def test_intent_route_is_explicit_and_separate_from_model_routing():
    r = registry([candidate()])
    assert r.query_for_intent("document_question", "local", MemoryScope("alice", "p", collection_id="c"))["authority"] == "candidate_only"
    with pytest.raises(ValidationError):
        r.query_for_intent("invented", "local", MemoryScope("alice", "p"))


def test_five_categories_owner_scope_and_persistent_revoke(tmp_path):
    kernel = ContinuityKernel.create(tmp_path / "state.db")
    kernel.create_project("p", "Owned project", owner_id="alice")
    r = MemoryProviderRegistry()
    for kind in ("profile", "episodic", "task", "skill", "evidence"):
        r.register(kind, KernelMemoryProvider(kernel, kind, "alice"))
    scope = MemoryScope("alice", "p")
    source = candidate().source
    r.store("evidence", scope, "k", "Sourced hypothesis", sources=(source,))
    assert len(r.query("evidence", "local", scope)["candidates"]) == 1
    assert not r.snapshot("skill", scope)
    r.revoke("evidence", scope, "k", 1, "Retrieval withdrawn")
    assert not r.query("evidence", "local", scope)["candidates"]
    with pytest.raises(ValidationError):
        r.snapshot("evidence", MemoryScope("bob", "p"))
    wrong = KernelMemoryProvider(kernel, "evidence", "bob")
    with pytest.raises(ValidationError):
        wrong.snapshot(MemoryScope("bob", "p"))


def payload():
    body = "The synthetic integration stays local."
    return {"schema_version": "eaon.evidence.v1", "query": "local", "owner_id": "alice", "collection_id": "c",
            "cache": "bypassed", "authority": "candidate_only", "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "results": [{"chunk_id": "1", "document_id": "d", "text": body, "sha256": sha256(body.encode()).hexdigest(), "score": 0.9}]}


def test_synapse_protocol_has_no_ask_or_write_and_no_token_in_evidence():
    requests = []
    def transport(req, **kwargs):
        requests.append(req)
        return BytesIO(json.dumps(payload()).encode())
    provider = SynapseEvidenceProvider("http://127.0.0.1:8000", "synthetic-token", "alice", transport=transport)
    items = provider.query("local", MemoryScope("alice", "p", collection_id="c"))
    assert requests[0].method == "GET" and "/chat/evidence?" in requests[0].full_url
    assert requests[0].get_header("Authorization") == "Bearer synthetic-token"
    assert "synthetic-token" not in json.dumps(items[0].to_dict())
    assert items[0].source.sha256 == payload()["results"][0]["sha256"]


@pytest.mark.parametrize("mutation", ["owner", "collection", "cache", "digest", "stale"])
def test_synapse_mismatch_fails_closed(mutation):
    data = payload()
    if mutation == "owner": data["owner_id"] = "bob"
    elif mutation == "collection": data["collection_id"] = "other"
    elif mutation == "cache": data["cache"] = "hit"
    elif mutation == "digest": data["results"][0]["sha256"] = "0" * 64
    else: data["retrieved_at"] = "2020-01-01T00:00:00+00:00"
    provider = SynapseEvidenceProvider("http://127.0.0.1", "synthetic", "alice", transport=lambda *a, **k: BytesIO(json.dumps(data).encode()))
    with pytest.raises(ValidationError):
        provider.query("local", MemoryScope("alice", "p", collection_id="c"))


@pytest.mark.parametrize("url", ["http://example.com", "https://example.com", "http://user:pass@localhost", "http://localhost?token=secret"])
def test_synapse_remote_and_credential_urls_rejected(url):
    with pytest.raises(ValidationError):
        SynapseEvidenceProvider(url, "synthetic", "alice")
