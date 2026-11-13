"""Explicit read-only project binding for a local conversation."""
from dataclasses import dataclass
import json
import os
from pathlib import Path

from eaon_kernel import ContinuityKernel, IntegrityError, ValidationError
from eaon_kernel.memory import KernelMemoryProvider, MemoryProviderRegistry, MemoryScope
from eaon_kernel.synapse import SynapseEvidenceProvider

MAX_CONTEXT_CHARS = 16000


class ProjectContextError(RuntimeError):
    """Stable public codes; never include database paths, source text or tokens."""


@dataclass(frozen=True)
class ContextSnapshot:
    serialized: str
    summary: dict


class ProjectContext:
    def __init__(self, db, project_id, *, budget_chars=MAX_CONTEXT_CHARS,
                 synapse_url=None, collection_id=None, token_env="SYNAPSE_TOKEN",
                 required_source_ids=()):
        if type(budget_chars) is not int or not 1000 <= budget_chars <= MAX_CONTEXT_CHARS:
            raise ProjectContextError("context_invalid_configuration")
        if type(project_id) is not str or not project_id.strip():
            raise ProjectContextError("context_invalid_configuration")
        if bool(synapse_url) != bool(collection_id):
            raise ProjectContextError("context_invalid_configuration")
        if type(required_source_ids) is not tuple or any(type(s) is not str or not s for s in required_source_ids):
            raise ProjectContextError("context_invalid_configuration")
        try:
            self.db = Path(db).resolve()
        except (TypeError, ValueError, OSError):
            raise ProjectContextError("context_invalid_configuration") from None
        self.project_id = project_id
        self.budget_chars, self.required_source_ids = budget_chars, required_source_ids
        self.collection_id = collection_id
        self.owner_id = None
        card = self.project_card()
        self.owner_id = card["owner_id"]
        self.registry = MemoryProviderRegistry()
        try:
            provider = (SynapseEvidenceProvider(synapse_url, os.environ.get(token_env, ""), self.owner_id)
                        if synapse_url else KernelMemoryProvider(ContinuityKernel(self.db), "evidence", self.owner_id))
            self.registry.register("evidence", provider)
        except (ValidationError, ValueError, TypeError):
            raise ProjectContextError("context_invalid_configuration") from None

    def project_card(self):
        try:
            card = ContinuityKernel(self.db).context_card(self.project_id)
            if self.owner_id is not None and card["owner_id"] != self.owner_id:
                raise ProjectContextError("context_owner_mismatch")
            return card
        except IntegrityError:
            raise ProjectContextError("context_integrity_failed") from None
        except (ValidationError, OSError, ValueError, TypeError):
            raise ProjectContextError("context_project_unavailable") from None

    def prepare(self, query):
        card = self.project_card()
        if card.get("blocked_memories"):
            raise ProjectContextError("context_state_contaminated")
        # Completed-task and goal history is inspectable in the kernel, not chat context.
        project = {key: card[key] for key in ("project_id", "title", "owner_id", "active_goal", "next_task", "memories", "journal_head", "event_count")}
        envelope = {"schema": "eaon.project-context.v1", "project": project,
                    "evidence": None, "authority": "data_only_no_actions"}
        def encode():
            return json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        # Budget the complete serialization, including JSON escaping and metadata.
        remaining = self.budget_chars - len(encode()) - 800
        if remaining < 1:
            raise ProjectContextError("context_budget_exceeded")
        try:
            evidence = self.registry.query("evidence", query,
                MemoryScope(self.owner_id, self.project_id, collection_id=self.collection_id),
                budget_chars=min(remaining, 100000), required_source_ids=self.required_source_ids)
        except (ValidationError, OSError, ValueError, TypeError):
            raise ProjectContextError("context_retrieval_failed") from None
        try:
            head = ContinuityKernel(self.db).verify()["head"]
        except (IntegrityError, OSError):
            raise ProjectContextError("context_integrity_failed") from None
        if head != card["journal_head"]:
            raise ProjectContextError("context_changed_during_retrieval")
        if evidence["status"] in {"unknown_required_fact", "contested"}:
            raise ProjectContextError("context_required_evidence_missing")
        envelope["evidence"] = evidence
        serialized = encode()
        if len(serialized) > self.budget_chars:
            # Do not slice JSON or silently discard required source evidence.
            raise ProjectContextError("context_budget_exceeded")
        return ContextSnapshot(serialized, {
            "project_id": self.project_id, "title": card["title"], "journal_head": card["journal_head"],
            "event_count": card["event_count"], "evidence_status": evidence["status"],
            "source_count": len(evidence["candidates"]), "context_chars": len(serialized),
        })
