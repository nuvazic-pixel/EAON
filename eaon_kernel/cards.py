"""Evidence-linked lessons; typed claims are declarations, never inferred truth."""
from dataclasses import asdict, dataclass

from .contracts import SourceRef, ValidationError, text


@dataclass(frozen=True)
class FactClaim:
    subject: str
    predicate: str
    value: str

    def __post_init__(self):
        for name in ("subject", "predicate", "value"):
            text(getattr(self, name), name, 500)


@dataclass(frozen=True)
class MemoryCard:
    text: str
    source_trace: SourceRef
    evidence_span: tuple[int, int]
    outcome: str
    derived_by: str
    claim: FactClaim | None = None
    revocation_state: str = "active"

    def __post_init__(self):
        text(self.text, "memory card text")
        text(self.derived_by, "derived_by", 200)
        if not isinstance(self.source_trace, SourceRef):
            raise ValidationError("Memory card requires a captured source trace")
        span = self.evidence_span
        if (type(span) is not tuple or len(span) != 2 or any(type(x) is not int for x in span)
                or not 0 <= span[0] < span[1] <= len(self.source_trace.text)):
            raise ValidationError("Evidence span must index nonempty captured trace characters")
        if type(self.outcome) is not str or self.outcome not in {"succeeded", "failed", "unknown"}:
            raise ValidationError("Unknown source outcome")
        if type(self.revocation_state) is not str or self.revocation_state not in {"active", "quarantined", "revoked"}:
            raise ValidationError("Unknown card revocation state")
        if self.claim is not None and not isinstance(self.claim, FactClaim):
            raise ValidationError("Claim must be a typed FactClaim")

    def to_dict(self):
        result = asdict(self)
        result["evidence_span"] = list(self.evidence_span)
        return result

    @classmethod
    def from_dict(cls, data):
        fields = {"text", "source_trace", "evidence_span", "outcome", "derived_by", "claim", "revocation_state"}
        try:
            if type(data) is not dict or set(data) != fields:
                raise ValidationError("Invalid memory card fields")
            source = data["source_trace"]
            claim = data["claim"]
            if type(source) is not dict or set(source) != {"source_id", "uri", "text", "sha256"}:
                raise ValidationError("Invalid source trace fields")
            if claim is not None and (type(claim) is not dict or set(claim) != {"subject", "predicate", "value"}):
                raise ValidationError("Invalid claim fields")
            if type(data["evidence_span"]) is not list:
                raise ValidationError("Invalid evidence span")
            return cls(data["text"], SourceRef(**source), tuple(data["evidence_span"]), data["outcome"],
                       data["derived_by"], FactClaim(**claim) if claim is not None else None, data["revocation_state"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("Malformed memory card") from exc


def apply_card_event(project, kind, data):
    """Called inside the journal's verified transaction/replay only."""
    from copy import deepcopy
    from .contracts import ConflictError
    expected_fields = {"project_id", "key", "expected_revision", "card", "status"}
    if kind == "memory.restored":
        expected_fields.add("reason")
    elif kind == "memory.contradicted":
        expected_fields = {"project_id", "key", "expected_revision", "counterevidence", "fault_origin"}
    if set(data) != expected_fields:
        raise ValidationError("Unexpected traced memory event fields")
    key = text(data["key"], "memory key", 200)
    prior = project["memories"].get(key)
    revision = data["expected_revision"]
    if revision is not None and (type(revision) is not int or revision < 1):
        raise ValidationError("Expected revision must be positive")
    if (prior and revision != prior["revision"]) or (not prior and revision is not None):
        raise ConflictError("Traced memory update requires the current revision")
    if kind == "memory.contradicted":
        if prior is None or prior["lifecycle"] != "active" or "card" not in prior:
            raise ConflictError("Counterevidence requires an active traced card")
        old_card = MemoryCard.from_dict(prior["card"])
        counter = MemoryCard.from_dict(data["counterevidence"])
        left, right = old_card.claim, counter.claim
        if (left is None or right is None or (left.subject, left.predicate) != (right.subject, right.predicate)
                or left.value == right.value or counter.revocation_state != "active"):
            raise ValidationError("Counterevidence must explicitly contradict the same typed claim")
        text(data["fault_origin"], "fault_origin", 500)
        prior.update(lifecycle="quarantined", revision=prior["revision"] + 1)
        prior["card"]["revocation_state"] = "quarantined"
        prior["incident"] = {"fault_origin": data["fault_origin"], "contradicting_evidence": counter.to_dict(),
                             "state_contaminated": True, "control_triggered": "quarantine_and_block_context",
                             "state_restored": False, "final_output_origin": "kernel:memory.contradicted"}
        return
    card = MemoryCard.from_dict(data["card"])
    if card.revocation_state != "active" or type(data["status"]) is not str or data["status"] not in {"confirmed", "hypothesis", "unknown"}:
        raise ValidationError("New or restored cards must be active with an explicit epistemic status")
    if kind == "memory.restored":
        text(data["reason"], "restoration reason")
        if prior is None or prior["lifecycle"] != "quarantined":
            raise ConflictError("Restoration requires a quarantined memory")
        counter = MemoryCard.from_dict(prior["incident"]["contradicting_evidence"])
        if card.claim != counter.claim:
            raise ValidationError("Restoration must resolve the recorded typed counterclaim")
    elif prior and prior["lifecycle"] == "quarantined":
        raise ConflictError("Use explicit restoration or revocation for contaminated state")
    record = {"text": card.text, "status": data["status"], "sources": [card.source_trace.to_dict()],
              "lifecycle": "active", "revision": prior["revision"] + 1 if prior else 1, "card": card.to_dict()}
    if kind == "memory.restored":
        record["incident"] = {**deepcopy(prior["incident"]), "state_contaminated": False, "state_restored": True,
                              "resolution": data["reason"], "final_output_origin": "kernel:memory.restored"}
    project["memories"][key] = record
