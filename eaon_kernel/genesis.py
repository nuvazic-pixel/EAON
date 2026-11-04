"""Read-only bridge for explicitly selected legacy Genesis JSONL journals."""
from hashlib import sha256
import json
from datetime import datetime
from pathlib import Path

from .contracts import EvidenceCandidate, IntegrityError, SourceRef, ValidationError
from .kernel import canonical


class GenesisEvidenceProvider:
    def __init__(self, path, owner_id="local", expected_head=None):
        self.path, self.owner_id, self.expected_head = Path(path), owner_id, expected_head

    def query(self, query, scope):
        if scope.owner_id != self.owner_id or scope.privacy != "local" or scope.collection_id is not None:
            raise ValidationError("Legacy Genesis journal requires its local owner scope")
        try:
            records, previous = [], "GENESIS"
            seen = set()
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if set(record) != {"id", "kind", "text", "tags", "metadata", "timestamp", "previous_hash", "content_hash"}:
                    raise IntegrityError("Invalid legacy record fields")
                if any(type(record[key]) is not str for key in ("id", "kind", "text", "timestamp", "previous_hash", "content_hash")):
                    raise IntegrityError("Invalid legacy text fields")
                if not record["id"].strip() or record["id"] in seen or not record["kind"].strip():
                    raise IntegrityError("Invalid or duplicate legacy identity")
                if type(record["tags"]) is not list or any(type(tag) is not str for tag in record["tags"]) or type(record["metadata"]) is not dict:
                    raise IntegrityError("Invalid legacy tags or metadata")
                if datetime.fromisoformat(record["timestamp"]).tzinfo is None:
                    raise IntegrityError("Legacy timestamp requires timezone")
                seen.add(record["id"])
                unsigned = {k: v for k, v in record.items() if k != "content_hash"}
                digest = sha256(canonical(unsigned).encode("utf-8")).hexdigest()
                if record["previous_hash"] != previous or record["content_hash"] != digest:
                    raise IntegrityError("Legacy Genesis journal integrity failed")
                previous = digest
                records.append(record)
            if self.expected_head is not None and previous != self.expected_head:
                raise IntegrityError("Legacy journal differs from expected head")
            terms = set(query.casefold().split())
            return [EvidenceCandidate(SourceRef(record["id"], self.path.resolve().as_uri() + "#" + record["id"],
                    record["text"], sha256(record["text"].encode("utf-8")).hexdigest()), "genesis", self.owner_id)
                    for record in records if terms & set(record["text"].casefold().split())]
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise IntegrityError("Legacy Genesis journal is missing or malformed") from exc
