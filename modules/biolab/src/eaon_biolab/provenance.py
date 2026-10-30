"""Deterministic hashes and an audit envelope; no external store writes."""
import hashlib
import json
from pathlib import Path


def canonical_bytes(data) -> bytes:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_audit(config_path: str | Path, observations: list[dict], rejected: int) -> dict:
    # Store-neutral evidence envelope; EAON store adapter will be added separately.
    return {
        "schema": "eaon.biolab.audit.v0.1",
        "experiment_id": "EXP-BIO-001",
        "source": "synthetic",
        "config_sha256": sha256(Path(config_path).read_bytes()),
        "batch_sha256": sha256(canonical_bytes(observations)),
        "count": len(observations),
        "rejected": rejected,
    }
