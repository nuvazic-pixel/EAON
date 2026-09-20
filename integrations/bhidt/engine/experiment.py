from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import uuid

from .explain import explain_transition
from .fingerprint import build_reproducibility_fingerprint
from .journal import ExperimentJournal, canonical_json, sha256_text
from .simulation import BlackHoleSimulation
from .version import ENGINE_VERSION


@dataclass(frozen=True)
class ExperimentConfig:
    initial_mass_kg: float = 1.0e12
    model: str = "ISLAND_QES"
    steps: int = 101
    tau_start: float = 0.0
    tau_end: float = 0.999999

    def validate(self):
        if self.initial_mass_kg <= 0:
            raise ValueError("initial_mass_kg must be > 0")
        if self.steps < 2:
            raise ValueError("steps must be >= 2")
        if not (0.0 <= self.tau_start < self.tau_end < 1.0):
            raise ValueError("Require 0 <= tau_start < tau_end < 1")
        if self.model not in {"ISLAND_QES", "HAWKING_SEMICLASSICAL"}:
            raise ValueError("Unsupported model")

    def to_dict(self):
        self.validate()
        return asdict(self)

    @property
    def config_hash(self) -> str:
        return sha256_text(canonical_json(self.to_dict()))


class ExperimentRunner:
    """
    v0.4 invariant: one experiment directory has one journal writer.
    All other components must query/read the journal rather than append concurrently.
    """

    def __init__(
        self,
        experiment_dir: str | Path,
        config: ExperimentConfig,
        *,
        experiment_id: str | None = None,
    ):
        config.validate()
        self.config = config
        self.experiment_id = experiment_id or str(uuid.uuid4())
        self.experiment_dir = Path(experiment_dir)
        self.experiment_dir.mkdir(parents=True, exist_ok=True)

        self.journal_path = self.experiment_dir / "events.jsonl"
        self.manifest_path = self.experiment_dir / "manifest.json"
        self.checkpoint_path = self.experiment_dir / "checkpoint.json"

        if self.journal_path.exists() and self.journal_path.stat().st_size:
            raise FileExistsError(
                f"Journal already exists: {self.journal_path}. "
                "Single-writer invariant forbids silently reusing it."
            )

        self.journal = ExperimentJournal(self.journal_path, self.experiment_id)
        self.sim = BlackHoleSimulation(config.initial_mass_kg, config.model)

    def _taus(self) -> list[float]:
        start = self.config.tau_start
        end = self.config.tau_end
        n = self.config.steps
        return [start + (end - start) * i / (n - 1) for i in range(n)]

    def _fingerprint(self) -> dict:
        initial_snapshot = self.sim.snapshot(self.config.tau_start)
        return build_reproducibility_fingerprint(
            config_hash=self.config.config_hash,
            model=self.config.model,
            initial_snapshot=initial_snapshot,
            expected_snapshot_count=self.config.steps,
        )

    def _write_manifest(self):
        fingerprint = self._fingerprint()
        manifest = {
            "experiment_id": self.experiment_id,
            "engine_version": ENGINE_VERSION,
            "config": self.config.to_dict(),
            "config_hash": self.config.config_hash,
            "reproducibility_fingerprint": fingerprint,
            "journal": self.journal_path.name,
            "journal_policy": "append_only_tamper_evident_sha256_chain",
            "journal_writer_invariant": "single_writer_per_experiment",
        }
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _write_checkpoint(self, snapshot: dict, reason: str, journal_record: dict):
        checkpoint = {
            "experiment_id": self.experiment_id,
            "reason": reason,
            "snapshot": snapshot,
            "journal_seq": journal_record["seq"],
            "journal_hash": journal_record["hash"],
        }
        self.checkpoint_path.write_text(
            json.dumps(checkpoint, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def run(self) -> dict:
        self._write_manifest()

        self.journal.append(
            "EXPERIMENT_STARTED",
            {
                "engine_version": ENGINE_VERSION,
                "config": self.config.to_dict(),
                "config_hash": self.config.config_hash,
                "derived_page_time": self.sim.page_time,
            },
        )

        snapshots = []
        previous = None
        transition_payload = None

        for tau in self._taus():
            snapshot = self.sim.snapshot(tau)
            self.journal.append("SNAPSHOT", {"snapshot": snapshot})
            snapshots.append(snapshot)

            if previous is not None:
                explanation = explain_transition(previous, snapshot)
                if explanation["transition_detected"] and transition_payload is None:
                    transition_payload = {
                        "transition": explanation,
                        "derived_page_time": self.sim.page_time,
                        "note": (
                            "Transition was detected from a change in dominant branch; "
                            "it was not triggered by a UI threshold."
                        ),
                    }
                    transition_record = self.journal.append(
                        "PAGE_TRANSITION",
                        transition_payload,
                    )
                    self._write_checkpoint(
                        snapshot,
                        "page_transition",
                        transition_record,
                    )

            previous = snapshot

        final_record = self.journal.append(
            "EXPERIMENT_COMPLETED",
            {
                "snapshot_count": len(snapshots),
                "page_transition_detected": transition_payload is not None,
                "final_tau": snapshots[-1]["tau"],
                "final_snapshot": snapshots[-1],
            },
        )
        self._write_checkpoint(
            snapshots[-1],
            "experiment_completed",
            final_record,
        )

        verification = self.journal.verify_chain()

        return {
            "experiment_id": self.experiment_id,
            "experiment_dir": str(self.experiment_dir),
            "journal_path": str(self.journal_path),
            "manifest_path": str(self.manifest_path),
            "checkpoint_path": str(self.checkpoint_path),
            "config_hash": self.config.config_hash,
            "snapshot_count": len(snapshots),
            "page_transition_detected": transition_payload is not None,
            "derived_page_time": self.sim.page_time,
            "journal_verification": verification,
            "snapshots": snapshots,
        }
