"""Deterministic M1 experiment engine for synthetic time-series observations."""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any, Mapping

from .provenance import canonical_bytes, sha256
from .validation import BioDataValidator


def run_experiment(config: Mapping[str, Any], observations: list[dict]) -> dict:
    """Validate observations and return a reproducible, JSON-safe report.

    Anomalies use a population z-score threshold of 2.0. Constant series
    have no statistical outliers. Invalid observations never enter statistics.
    """
    validator = BioDataValidator(config)
    accepted: list[dict] = []
    rejected: list[dict] = []
    for index, observation in enumerate(observations):
        errors = validator.validate_observation(observation)
        if errors:
            rejected.append({"index": index, "errors": errors})
        else:
            accepted.append(observation)

    accepted.sort(key=lambda item: (
        datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")).astimezone(timezone.utc),
        item["observation_id"],
    ))
    values = [float(item["value"]) for item in accepted]
    average = mean(values) if values else None
    deviation = pstdev(values) if values else None
    anomalies = [
        {"observation_id": item["observation_id"], "timestamp": item["timestamp"],
         "value": item["value"], "z_score": round(abs((float(item["value"]) - average) / deviation), 6)}
        for item in accepted
        if deviation is not None and deviation > 0
        and abs((float(item["value"]) - average) / deviation) > 2.0
    ]
    result = {
        "schema": "eaon.biolab.experiment.v1",
        "experiment_id": config["experiment_id"],
        "source": "synthetic",
        "metric": config["target_metric"],
        "unit": config["expected_unit"],
        "total": len(observations),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "statistics": {
            "count": len(values),
            "mean": round(average, 6) if average is not None else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "population_stddev": round(deviation, 6) if deviation is not None else None,
        },
        "anomalies": anomalies,
        "rejections": rejected,
        "input_sha256": sha256(canonical_bytes(observations)),
    }
    result["report_sha256"] = sha256(canonical_bytes(result))
    return result
