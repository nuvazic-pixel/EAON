"""Pure, deterministic observation validation. No network or persistence."""
from datetime import datetime
from math import isfinite
from typing import Any, Mapping

REQUIRED = ("observation_id", "subject_id", "timestamp", "metric",
            "value", "unit", "source", "quality_flag")


class BioDataValidator:
    def __init__(self, config: Mapping[str, Any]):
        self.config = config

    def validate_observation(self, obs: Mapping[str, Any]) -> list[str]:
        if not isinstance(obs, Mapping):
            return ["Observation must be a mapping"]
        errors = [f"Missing required field: {key}" for key in REQUIRED if key not in obs]
        if errors:
            return errors
        for key in ("observation_id", "subject_id", "metric", "unit", "source", "quality_flag"):
            if not isinstance(obs[key], str) or not obs[key].strip():
                errors.append(f"Invalid nonempty string: {key}")
        timestamp = obs["timestamp"]
        if not isinstance(timestamp, str):
            errors.append("Invalid ISO timestamp format")
        else:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if dt.tzinfo is None or dt.utcoffset() is None:
                    raise ValueError("timezone required")
            except (ValueError, OverflowError):
                errors.append("Invalid ISO timestamp format")
        if obs["metric"] != self.config["target_metric"]:
            errors.append(f"Incompatible metric: {obs['metric']}")
        if obs["unit"] != self.config["expected_unit"]:
            errors.append(f"Incompatible unit: {obs['unit']}")
        value = obs["value"]
        rules = self.config["validation_rules"]
        if (type(value) not in (int, float) or not isfinite(value)
                or not rules["min_value"] <= value <= rules["max_value"]):
            errors.append(f"Value out of configured bounds or invalid type: {value}")
        if obs["quality_flag"] != "valid":
            errors.append(f"Invalid quality flag: {obs['quality_flag']}")
        return errors
