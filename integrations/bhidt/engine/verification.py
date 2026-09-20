from __future__ import annotations

from pathlib import Path
import json
import math

from .comparator import FloatPolicy, compare_snapshots
from .experiment import ExperimentConfig
from .fingerprint import (
    build_reproducibility_fingerprint,
    validate_fingerprint_shape,
)
from .journal import ExperimentJournal
from .recompute import load_manifest, recompute_from_manifest
from .replay import load_events
from .simulation import BlackHoleSimulation
from .version import VERIFICATION_VERSION


CRITICAL_FINGERPRINT_KEYS = (
    "engine_version",
    "snapshot_schema_version",
    "model",
    "model_version",
    "constants_version",
    "constants_hash",
    "config_hash",
    "initial_state_hash",
    "code_hash",
    "expected_snapshot_count",
    "serialization_version",
)


def _recorded_snapshots_and_seqs(events: list[dict]) -> tuple[list[dict], list[int]]:
    snapshots, seqs = [], []
    for event in events:
        if event.get("event_type") == "SNAPSHOT":
            snapshots.append(event["payload"]["snapshot"])
            seqs.append(event["seq"])
    return snapshots, seqs


def _recorded_page_time(events: list[dict]):
    for event in events:
        if event.get("event_type") == "PAGE_TRANSITION":
            return event["payload"].get("derived_page_time")
    for event in events:
        if event.get("event_type") == "EXPERIMENT_STARTED":
            return event["payload"].get("derived_page_time")
    return None


def _fingerprint_comparison(recorded: dict, current: dict) -> dict:
    fields = {}
    mismatch = False
    for key in CRITICAL_FINGERPRINT_KEYS:
        rv = recorded.get(key)
        cv = current.get(key)
        same = rv == cv
        fields[key] = {
            "recorded": rv,
            "recomputed": cv,
            "match": same,
        }
        mismatch = mismatch or not same

    environment = {
        "recorded": recorded.get("environment"),
        "recomputed": current.get("environment"),
        "match": recorded.get("environment") == current.get("environment"),
        "gating": False,
    }
    return {
        "fields": fields,
        "environment": environment,
        "critical_match": not mismatch,
    }


def verify_experiment(
    experiment_dir: str | Path,
    *,
    policy: FloatPolicy | None = None,
) -> dict:
    experiment_dir = Path(experiment_dir)
    policy = policy or FloatPolicy()

    # Missing basic artifacts means verification cannot even start.
    try:
        manifest = load_manifest(experiment_dir)
    except Exception as exc:
        return {
            "verification_version": VERIFICATION_VERSION,
            "status": "UNVERIFIABLE",
            "reason": f"manifest_error: {exc}",
        }

    experiment_id = manifest.get("experiment_id")
    journal_path = experiment_dir / manifest.get("journal", "events.jsonl")

    if not journal_path.exists():
        return {
            "experiment_id": experiment_id,
            "verification_version": VERIFICATION_VERSION,
            "status": "UNVERIFIABLE",
            "reason": "journal_missing",
        }

    journal = ExperimentJournal(journal_path, experiment_id or "unknown")
    journal_result = journal.verify_chain()
    if not journal_result.get("valid"):
        return {
            "experiment_id": experiment_id,
            "verification_version": VERIFICATION_VERSION,
            "status": "UNVERIFIABLE",
            "reason": "journal_integrity_failed",
            "journal": journal_result,
        }

    recorded_fp = manifest.get("reproducibility_fingerprint")
    if not isinstance(recorded_fp, dict):
        return {
            "experiment_id": experiment_id,
            "verification_version": VERIFICATION_VERSION,
            "status": "UNVERIFIABLE",
            "reason": "missing_reproducibility_fingerprint",
            "journal": journal_result,
        }

    missing_fp = validate_fingerprint_shape(recorded_fp)
    if missing_fp:
        return {
            "experiment_id": experiment_id,
            "verification_version": VERIFICATION_VERSION,
            "status": "UNVERIFIABLE",
            "reason": "incomplete_reproducibility_fingerprint",
            "missing_fields": missing_fp,
            "journal": journal_result,
        }

    try:
        config = ExperimentConfig(**manifest["config"])
        config.validate()
        sim = BlackHoleSimulation(config.initial_mass_kg, config.model)
        initial_snapshot = sim.snapshot(config.tau_start)
        current_fp = build_reproducibility_fingerprint(
            config_hash=config.config_hash,
            model=config.model,
            initial_snapshot=initial_snapshot,
            expected_snapshot_count=config.steps,
        )
    except Exception as exc:
        return {
            "experiment_id": experiment_id,
            "verification_version": VERIFICATION_VERSION,
            "status": "UNVERIFIABLE",
            "reason": f"fingerprint_rebuild_failed: {exc}",
            "journal": journal_result,
        }

    fp_compare = _fingerprint_comparison(recorded_fp, current_fp)

    # A different code/model/config/constants identity is a true structural divergence,
    # even if some outputs happen to remain numerically close.
    if not fp_compare["critical_match"]:
        first_key = next(
            key for key, value in fp_compare["fields"].items()
            if not value["match"]
        )
        return {
            "experiment_id": experiment_id,
            "verification_version": VERIFICATION_VERSION,
            "status": "DIVERGENCE",
            "reason": "critical_fingerprint_mismatch",
            "first_divergence": {
                "kind": "fingerprint_mismatch",
                "field": first_key,
                **fp_compare["fields"][first_key],
            },
            "fingerprint": fp_compare,
            "journal": journal_result,
        }

    try:
        recomputed = recompute_from_manifest(experiment_dir)
        events = load_events(journal_path)
        recorded_snapshots, recorded_seqs = _recorded_snapshots_and_seqs(events)
    except Exception as exc:
        return {
            "experiment_id": experiment_id,
            "verification_version": VERIFICATION_VERSION,
            "status": "UNVERIFIABLE",
            "reason": f"recomputation_failed: {exc}",
            "fingerprint": fp_compare,
            "journal": journal_result,
        }

    comparison = compare_snapshots(
        recorded_snapshots,
        recomputed["snapshots"],
        policy=policy,
        recorded_event_seqs=recorded_seqs,
    )

    recorded_page = _recorded_page_time(events)
    recomputed_page = recomputed["derived_page_time"]
    if recorded_page is None:
        page = {
            "recorded": None,
            "recomputed": recomputed_page,
            "match": False,
            "reason": "recorded_page_time_missing",
        }
        page_status = "UNVERIFIABLE"
    else:
        page_abs = abs(float(recorded_page) - float(recomputed_page))
        page_rel = 0.0 if max(abs(recorded_page), abs(recomputed_page)) == 0 else (
            page_abs / max(abs(recorded_page), abs(recomputed_page))
        )
        page_match = math.isclose(
            float(recorded_page),
            float(recomputed_page),
            rel_tol=policy.rel_tol,
            abs_tol=policy.abs_tol,
        )
        page = {
            "recorded": recorded_page,
            "recomputed": recomputed_page,
            "abs_error": page_abs,
            "rel_error": page_rel,
            "match": page_match,
        }
        page_status = "MATCH" if page_match else "DRIFT"

    if page_status == "UNVERIFIABLE":
        status = "UNVERIFIABLE"
    elif comparison["status"] == "DIVERGENCE":
        status = "DIVERGENCE"
    elif comparison["status"] == "DRIFT" or page_status == "DRIFT":
        status = "DRIFT"
    else:
        status = "MATCH"

    return {
        "experiment_id": experiment_id,
        "verification_version": VERIFICATION_VERSION,
        "status": status,
        "fingerprint": fp_compare,
        "environment": fp_compare["environment"],
        "comparison": comparison,
        "page_transition": page,
        "journal": {
            "hash_chain_valid": True,
            "events_verified": journal_result.get("events"),
            "head_hash": journal_result.get("head_hash"),
        },
    }
