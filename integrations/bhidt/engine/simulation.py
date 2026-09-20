from physics.evaporation import mass_at_tau
from physics.schwarzschild import (
    schwarzschild_radius,
    hawking_temperature,
    bekenstein_hawking_entropy,
)
from information.entropy import entropy_state, find_page_time
from .provenance import PROVENANCE
from .version import ENGINE_VERSION, SNAPSHOT_SCHEMA_VERSION


class BlackHoleSimulation:
    def __init__(self, M0, model="ISLAND_QES"):
        self.M0 = M0
        self.model = model
        self.S0 = bekenstein_hawking_entropy(M0)
        self.page_time = find_page_time()

    def snapshot(self, tau):
        M = mass_at_tau(self.M0, tau)
        e = entropy_state(tau, self.model)
        return {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "engine_version": ENGINE_VERSION,
            "tau": tau,
            "mass_kg": M,
            "mass_normalized": M / self.M0,
            "schwarzschild_radius_m": schwarzschild_radius(M),
            "hawking_temperature_K": hawking_temperature(M),
            "bh_entropy_normalized": bekenstein_hawking_entropy(M) / self.S0,
            "radiation_entropy": e["radiation_entropy"],
            "hawking_branch_entropy": e["hawking"],
            "island_branch_entropy": e["island"],
            "page_time": self.page_time,
            "model": self.model,
            "dominant_saddle": e["dominant_saddle"],
            "model_scope": "toy_semiclassical",
            "validation_status": "v0.4_recomputation_verification_tests",
            "provenance_fields": sorted(PROVENANCE.keys()),
        }
