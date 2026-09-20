from __future__ import annotations

from pathlib import Path
import platform
import sys

from physics.constants import G, C, HBAR, K_B, PI

from .journal import canonical_json, sha256_text
from .version import (
    ENGINE_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    MODEL_VERSIONS,
    CONSTANTS_VERSION,
    SERIALIZATION_VERSION,
)


FINGERPRINT_REQUIRED_FIELDS = (
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


def constants_payload() -> dict:
    return {
        "G": G,
        "C": C,
        "HBAR": HBAR,
        "K_B": K_B,
        "PI": PI,
    }


def constants_hash() -> str:
    return sha256_text(canonical_json(constants_payload()))


def project_code_hash(project_root: str | Path | None = None) -> str:
    """
    Hash the executable model source, excluding tests/examples/runtime outputs.
    Relative paths are included so renames are visible.
    """
    root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    files = []
    for directory in ("engine", "physics", "information"):
        base = root / directory
        files.extend(
            p for p in base.rglob("*.py")
            if "__pycache__" not in p.parts
        )

    payload_parts = []
    for path in sorted(files, key=lambda p: str(p.relative_to(root))):
        rel = path.relative_to(root).as_posix()
        payload_parts.append(rel)
        payload_parts.append(path.read_text(encoding="utf-8"))

    return sha256_text("\n---FILE---\n".join(payload_parts))


def environment_fingerprint() -> dict:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "float_radix": sys.float_info.radix,
        "float_mant_dig": sys.float_info.mant_dig,
        "float_max_exp": sys.float_info.max_exp,
    }


def build_reproducibility_fingerprint(
    *,
    config_hash: str,
    model: str,
    initial_snapshot: dict,
    expected_snapshot_count: int,
    project_root: str | Path | None = None,
) -> dict:
    if model not in MODEL_VERSIONS:
        raise ValueError(f"No model version registered for {model}")

    return {
        "engine_version": ENGINE_VERSION,
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "model": model,
        "model_version": MODEL_VERSIONS[model],
        "constants_version": CONSTANTS_VERSION,
        "constants_hash": constants_hash(),
        "config_hash": config_hash,
        "initial_state_hash": sha256_text(canonical_json(initial_snapshot)),
        "code_hash": project_code_hash(project_root),
        "expected_snapshot_count": expected_snapshot_count,
        "serialization_version": SERIALIZATION_VERSION,
        "environment": environment_fingerprint(),
    }


def validate_fingerprint_shape(fingerprint: dict) -> list[str]:
    return [key for key in FINGERPRINT_REQUIRED_FIELDS if key not in fingerprint]
