from __future__ import annotations

from dataclasses import dataclass, asdict
import math
from typing import Any

from .provenance import provenance_for


@dataclass(frozen=True)
class FloatPolicy:
    abs_tol: float = 1e-12
    rel_tol: float = 1e-10

    def to_dict(self):
        return asdict(self)


def _errors(a: float, b: float) -> tuple[float, float]:
    abs_error = abs(a - b)
    scale = max(abs(a), abs(b))
    rel_error = 0.0 if scale == 0.0 else abs_error / scale
    return abs_error, rel_error


def _provenance_or_none(field: str):
    try:
        return provenance_for(field)
    except KeyError:
        return None


def compare_snapshots(
    recorded: list[dict],
    recomputed: list[dict],
    *,
    policy: FloatPolicy | None = None,
    recorded_event_seqs: list[int] | None = None,
) -> dict:
    """
    Status semantics:
      MATCH       all exact fields match and numeric fields are within tolerance
      DRIFT       structure/discrete state matches, numeric field exceeds tolerance
      DIVERGENCE  structural/discrete behavior differs, including snapshot count
    """
    policy = policy or FloatPolicy()

    if len(recorded) != len(recomputed):
        return {
            "status": "DIVERGENCE",
            "snapshot_count_recorded": len(recorded),
            "snapshot_count_recomputed": len(recomputed),
            "snapshots_compared": min(len(recorded), len(recomputed)),
            "float_policy": policy.to_dict(),
            "max_abs_error": None,
            "max_rel_error": None,
            "first_divergence": {
                "kind": "snapshot_count_mismatch",
                "recorded": len(recorded),
                "recomputed": len(recomputed),
            },
            "numeric_mismatches": 0,
            "structural_mismatches": 1,
        }

    max_abs = 0.0
    max_rel = 0.0
    numeric_mismatches = 0
    structural_mismatches = 0
    first_numeric = None
    first_structural = None

    for index, (left, right) in enumerate(zip(recorded, recomputed)):
        seq = recorded_event_seqs[index] if recorded_event_seqs else None

        left_keys = set(left)
        right_keys = set(right)
        if left_keys != right_keys:
            structural_mismatches += 1
            if first_structural is None:
                first_structural = {
                    "kind": "field_set_mismatch",
                    "snapshot_index": index,
                    "seq": seq,
                    "tau": left.get("tau"),
                    "recorded_only": sorted(left_keys - right_keys),
                    "recomputed_only": sorted(right_keys - left_keys),
                }
            continue

        for field in sorted(left_keys):
            a, b = left[field], right[field]

            # bool must be handled before int, because bool is a subclass of int.
            if isinstance(a, bool) or isinstance(b, bool):
                if a != b:
                    structural_mismatches += 1
                    if first_structural is None:
                        first_structural = {
                            "kind": "discrete_field_mismatch",
                            "snapshot_index": index,
                            "seq": seq,
                            "tau": left.get("tau"),
                            "field": field,
                            "recorded": a,
                            "recomputed": b,
                            "provenance": _provenance_or_none(field),
                        }
                continue

            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                af, bf = float(a), float(b)
                if not (math.isfinite(af) and math.isfinite(bf)):
                    if af != bf:
                        structural_mismatches += 1
                        if first_structural is None:
                            first_structural = {
                                "kind": "nonfinite_numeric_mismatch",
                                "snapshot_index": index,
                                "seq": seq,
                                "tau": left.get("tau"),
                                "field": field,
                                "recorded": a,
                                "recomputed": b,
                            }
                    continue

                abs_error, rel_error = _errors(af, bf)
                max_abs = max(max_abs, abs_error)
                max_rel = max(max_rel, rel_error)

                if not math.isclose(af, bf, rel_tol=policy.rel_tol, abs_tol=policy.abs_tol):
                    numeric_mismatches += 1
                    if first_numeric is None:
                        first_numeric = {
                            "kind": "numeric_tolerance_exceeded",
                            "snapshot_index": index,
                            "seq": seq,
                            "tau": left.get("tau"),
                            "field": field,
                            "recorded": a,
                            "recomputed": b,
                            "abs_error": abs_error,
                            "rel_error": rel_error,
                            "abs_tol": policy.abs_tol,
                            "rel_tol": policy.rel_tol,
                            "provenance": _provenance_or_none(field),
                        }
                continue

            if a != b:
                structural_mismatches += 1
                if first_structural is None:
                    first_structural = {
                        "kind": "discrete_field_mismatch",
                        "snapshot_index": index,
                        "seq": seq,
                        "tau": left.get("tau"),
                        "field": field,
                        "recorded": a,
                        "recomputed": b,
                        "provenance": _provenance_or_none(field),
                    }

    if structural_mismatches:
        status = "DIVERGENCE"
        first = first_structural
    elif numeric_mismatches:
        status = "DRIFT"
        first = first_numeric
    else:
        status = "MATCH"
        first = None

    return {
        "status": status,
        "snapshot_count_recorded": len(recorded),
        "snapshot_count_recomputed": len(recomputed),
        "snapshots_compared": len(recorded),
        "float_policy": policy.to_dict(),
        "max_abs_error": max_abs,
        "max_rel_error": max_rel,
        "first_divergence": first,
        "numeric_mismatches": numeric_mismatches,
        "structural_mismatches": structural_mismatches,
    }
