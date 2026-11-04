"""Deterministic memory admission, ranking and bounded evidence slates."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import re

from .contracts import EvidenceCandidate, SourceRef, ValidationError, text

KINDS = frozenset({"profile", "episodic", "task", "skill", "evidence"})
INTENT_ROUTES = {"profile_lookup": "profile", "past_episode": "episodic", "project_state": "task",
                 "validated_procedure": "skill", "document_question": "evidence"}


@dataclass(frozen=True)
class MemoryScope:
    owner_id: str
    project_id: str
    privacy: str = "local"
    collection_id: str | None = None

    def __post_init__(self):
        text(self.owner_id, "owner_id", 500)
        text(self.project_id, "project_id", 200)
        if self.privacy not in {"local", "cloud_ok"}:
            raise ValidationError("Unknown privacy class")
        if self.collection_id is not None:
            text(self.collection_id, "collection_id", 500)


def evidence_confidence(candidates, missing=(), contradictions=0):
    """Coverage/diversity heuristic, not a calibrated truth probability."""
    if type(contradictions) is not int or contradictions < 0:
        raise ValidationError("contradictions must be a nonnegative count")
    documents = {item.source.uri.partition("#")[0] for item in candidates}
    score = 0.0 if missing or contradictions or not documents else min(len(documents), 2) / 2
    return {"version": "evidence-coverage-v1", "score": score, "calibrated_probability": False,
            "documents": len(documents), "missing_required": len(missing), "contradictions": contradictions}


class MemoryProviderRegistry:
    def __init__(self):
        self.providers = {}

    def register(self, kind, provider, *, locality="local"):
        if kind not in KINDS or kind in self.providers or locality not in {"local", "remote"}:
            raise ValidationError("Invalid or duplicate provider registration")
        self.providers[kind] = (provider, locality)

    def query_for_intent(self, intent, query, scope, **kwargs):
        if type(intent) is not str or intent not in INTENT_ROUTES:
            raise ValidationError("Memory intent has no deterministic route")
        return self.query(INTENT_ROUTES[intent], query, scope, **kwargs)

    def _provider(self, kind, scope):
        if not isinstance(scope, MemoryScope) or kind not in self.providers:
            raise ValidationError("Registered provider and explicit MemoryScope are required")
        provider, locality = self.providers[kind]
        if locality == "remote" and scope.privacy == "local":
            raise ValidationError("Privacy gate rejected a remote provider before retrieval")
        return provider

    def query(self, kind, query, scope, *, budget_chars=12000, required_source_ids=(), contradictions=0):
        text(query, "query", 2000)
        if type(budget_chars) is not int or not 1 <= budget_chars <= 100000:
            raise ValidationError("Invalid evidence character budget")
        if type(required_source_ids) is not tuple or any(type(item) is not str or not item for item in required_source_ids):
            raise ValidationError("required_source_ids must be a tuple of nonempty strings")
        candidates = self._provider(kind, scope).query(query, scope)
        eligible, seen = [], set()
        now = datetime.now(timezone.utc)
        for candidate in candidates:
            if not isinstance(candidate, EvidenceCandidate):
                raise ValidationError("Provider returned an invalid candidate")
            if candidate.owner_id != scope.owner_id or candidate.revoked:
                continue
            if scope.collection_id is not None and candidate.collection_id != scope.collection_id:
                continue
            if candidate.expires_at is not None and datetime.fromisoformat(candidate.expires_at) <= now:
                continue
            # Same identifier with a different body is an ambiguous provenance collision.
            identity = (candidate.provider, candidate.source.source_id)
            previous = next((item for item in eligible if (item.provider, item.source.source_id) == identity), None)
            if previous and previous.source.sha256 != candidate.source.sha256:
                raise ValidationError("Conflicting content for one evidence identity")
            if identity not in seen:
                eligible.append(candidate)
                seen.add(identity)
        terms = set(re.findall(r"\w+", query.casefold()))
        rank = lambda item: (-len(terms & set(re.findall(r"\w+", item.source.text.casefold()))),
                             -(item.score or 0), item.source.source_id)
        eligible.sort(key=rank)
        required = set(required_source_ids)
        ordered = [item for item in eligible if item.source.source_id in required]
        ordered += [item for item in eligible if item.source.source_id not in required]
        slate, used = [], 0
        for item in ordered:
            cost = len(item.source.text)
            if used + cost <= budget_chars:
                slate.append(item)
                used += cost
        present = {item.source.source_id for item in slate}
        missing = sorted(required - present)
        status = "contested" if contradictions else "unknown_required_fact" if missing else "retrieved" if slate else "unknown"
        return {"status": status, "candidates": [item.to_dict() for item in slate],
                "missing_source_ids": missing, "all_required_evidence_present": not missing,
                "used_chars": used, "budget_chars": budget_chars,
                "evidence_confidence": evidence_confidence(slate, missing, contradictions),
                "authority": "candidate_only"}

    def store(self, kind, scope, key, value, **kwargs):
        provider = self._provider(kind, scope)
        if not hasattr(provider, "store"):
            raise ValidationError("This provider is read-only")
        return provider.store(scope, key, value, **kwargs)

    def revoke(self, kind, scope, key, expected_revision, reason):
        provider = self._provider(kind, scope)
        if not hasattr(provider, "revoke"):
            raise ValidationError("This provider is read-only")
        return provider.revoke(scope, key, expected_revision, reason)

    def snapshot(self, kind, scope):
        provider = self._provider(kind, scope)
        if not hasattr(provider, "snapshot"):
            raise ValidationError("This provider does not expose a local snapshot")
        return provider.snapshot(scope)


class KernelMemoryProvider:
    """One explicitly owned category; no shared vector-store migration."""
    def __init__(self, kernel, kind, owner_id="local"):
        if kind not in KINDS:
            raise ValidationError("Unknown memory kind")
        self.kernel, self.kind, self.owner_id = kernel, kind, owner_id

    def _check(self, scope):
        if scope.owner_id != self.owner_id or scope.collection_id is not None:
            raise ValidationError("Local memory owner/scope mismatch")

    def snapshot(self, scope):
        self._check(scope)
        card = self.kernel.recover(scope.project_id)
        if card["owner_id"] != scope.owner_id:
            raise ValidationError("Stored project owner does not match retrieval scope")
        memories = card["memories"]
        prefix = self.kind + ":"
        return {key[len(prefix):]: value for key, value in memories.items() if key.startswith(prefix) and value["lifecycle"] == "active"}

    def store(self, scope, key, value, **kwargs):
        self.snapshot(scope)
        return self.kernel.record_memory(scope.project_id, self.kind + ":" + key, value, **kwargs)

    def revoke(self, scope, key, expected_revision, reason):
        self.snapshot(scope)
        return self.kernel.revoke_memory(scope.project_id, self.kind + ":" + key, expected_revision, reason)

    def query(self, query, scope):
        output = []
        for key, memory in self.snapshot(scope).items():
            if memory["lifecycle"] != "active" or memory["status"] == "unknown":
                continue
            for proof in memory["sources"]:
                output.append(EvidenceCandidate(SourceRef(**proof), "kernel-" + self.kind, self.owner_id))
        return output
