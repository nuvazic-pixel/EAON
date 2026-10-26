"""Strict, dependency-free loader for the fixed EXP-BIO-001 YAML subset."""
from pathlib import Path
import re

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "experiment.yaml"
FIELDS = {"experiment_id", "target_metric", "expected_unit", "sampling_frequency_seconds"}
RULES = {"min_value", "max_value", "allow_missing", "strict_timestamps"}


def load_config(path: str | Path = CONFIG_PATH) -> dict:
    raw = Path(path).read_text(encoding="utf-8")
    result = {}
    section = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.strip() == "validation_rules:":
            if section is not None:
                raise ValueError("duplicate rules section")
            result["validation_rules"] = {}
            section = "validation_rules"
            continue
        match = re.fullmatch(r'(  )?([a-z_]+):\s*(?:"([^"]*)"|([0-9]+|true|false))\s*', line)
        if not match:
            raise ValueError(f"Unsupported YAML syntax: {line}")
        indent, key, quoted, scalar = match.groups()
        target = result["validation_rules"] if indent else result
        allowed = RULES if indent else FIELDS
        if key not in allowed or key in target or (indent and section is None):
            raise ValueError(f"Unexpected or duplicate key: {key}")
        value = quoted if quoted is not None else (scalar == "true" if scalar in ("true", "false") else int(scalar))
        target[key] = value
    if set(result) != FIELDS | {"validation_rules"} or set(result["validation_rules"]) != RULES:
        raise ValueError("Incomplete configuration")
    if (result["sampling_frequency_seconds"] <= 0
            or result["validation_rules"]["min_value"] >= result["validation_rules"]["max_value"]
            or result["validation_rules"]["allow_missing"] is not False
            or result["validation_rules"]["strict_timestamps"] is not True):
        raise ValueError("Invalid M0 validation policy")
    return result
