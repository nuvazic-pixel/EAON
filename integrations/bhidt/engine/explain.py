from .provenance import provenance_for, SOURCE_REGISTRY

def explain_field(snapshot: dict, field: str) -> dict:
    if field not in snapshot:
        raise KeyError(f"Snapshot has no field {field}")
    p = provenance_for(field)
    return {
        "field": field,
        "value": snapshot[field],
        "equation_id": p["equation_id"],
        "equation": p["equation"],
        "assumptions": p["assumptions"],
        "model_scope": p["model_scope"],
        "validation_status": p["validation_status"],
        "sources": [SOURCE_REGISTRY[s] | {"source_id": s} for s in p["source_ids"]]
    }

def explain_transition(previous: dict, current: dict) -> dict:
    changed = previous["dominant_saddle"] != current["dominant_saddle"]
    payload = {
        "transition_detected": changed,
        "from": previous["dominant_saddle"],
        "to": current["dominant_saddle"],
        "previous_tau": previous["tau"],
        "current_tau": current["tau"],
        "previous_hawking": previous["hawking_branch_entropy"],
        "previous_island": previous["island_branch_entropy"],
        "current_hawking": current["hawking_branch_entropy"],
        "current_island": current["island_branch_entropy"],
        "reason": None
    }
    if changed:
        payload["reason"] = (
            "The dominant generalized-entropy branch changed because the ordering "
            "of the toy Hawking and Island/QES branches reversed."
        )
    return payload
