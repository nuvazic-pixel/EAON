from __future__ import annotations

from pathlib import Path

from .explain import explain_field
from .provenance import PROVENANCE, provenance_for
from .replay import load_events
from .verification import verify_experiment


class EAONVerificationAdapter:
    """
    Thin deterministic adapter. It returns evidence structures;
    language generation should happen above this layer.
    """

    def __init__(self, experiment_dir: str | Path):
        self.experiment_dir = Path(experiment_dir)

    def verify_experiment(self) -> dict:
        return verify_experiment(self.experiment_dir)

    def why_diverged(self) -> dict:
        report = self.verify_experiment()
        return {
            "status": report.get("status"),
            "reason": report.get("reason"),
            "first_divergence": (
                report.get("first_divergence")
                or report.get("comparison", {}).get("first_divergence")
            ),
        }

    def compare_recorded_vs_recomputed(self) -> dict:
        report = self.verify_experiment()
        return {
            "status": report.get("status"),
            "comparison": report.get("comparison"),
            "page_transition": report.get("page_transition"),
        }

    def show_provenance(self, field: str, seq: int) -> dict:
        events = load_events(self.experiment_dir / "events.jsonl")
        event = next(
            (
                e for e in events
                if e.get("seq") == seq and e.get("event_type") == "SNAPSHOT"
            ),
            None,
        )
        if event is None:
            raise LookupError(f"No SNAPSHOT event at seq={seq}")
        return explain_field(event["payload"]["snapshot"], field)

    def explain_transition(self) -> dict:
        events = load_events(self.experiment_dir / "events.jsonl")
        event = next(
            (e for e in events if e.get("event_type") == "PAGE_TRANSITION"),
            None,
        )
        if event is None:
            raise LookupError("No PAGE_TRANSITION event")
        return event["payload"]

    def show_assumptions(self, model: str) -> dict:
        if model == "ISLAND_QES":
            fields = (
                "hawking_branch_entropy",
                "island_branch_entropy",
                "radiation_entropy",
                "page_time",
            )
        elif model == "HAWKING_SEMICLASSICAL":
            fields = ("hawking_branch_entropy",)
        else:
            raise ValueError(f"Unsupported model {model}")

        return {
            "model": model,
            "fields": {
                field: provenance_for(field)["assumptions"]
                for field in fields
            },
        }
