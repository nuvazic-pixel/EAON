from __future__ import annotations

import json
from pathlib import Path

from .experiment import ExperimentConfig
from .simulation import BlackHoleSimulation


def load_manifest(experiment_dir: str | Path) -> dict:
    path = Path(experiment_dir) / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def taus_from_config(config: ExperimentConfig) -> list[float]:
    start = config.tau_start
    end = config.tau_end
    n = config.steps
    return [start + (end - start) * i / (n - 1) for i in range(n)]


def recompute_from_manifest(experiment_dir: str | Path) -> dict:
    manifest = load_manifest(experiment_dir)
    if "config" not in manifest:
        raise KeyError("Manifest has no config")

    config = ExperimentConfig(**manifest["config"])
    config.validate()

    sim = BlackHoleSimulation(config.initial_mass_kg, config.model)
    snapshots = [sim.snapshot(tau) for tau in taus_from_config(config)]

    return {
        "config": config.to_dict(),
        "config_hash": config.config_hash,
        "derived_page_time": sim.page_time,
        "snapshots": snapshots,
    }
