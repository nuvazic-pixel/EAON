from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class ProvenanceRecord:
    field: str
    equation_id: str
    equation: str
    assumptions: tuple[str, ...]
    source_ids: tuple[str, ...]
    model_scope: str
    validation_status: str

    def to_dict(self):
        d = asdict(self)
        d["assumptions"] = list(self.assumptions)
        d["source_ids"] = list(self.source_ids)
        return d

SOURCE_REGISTRY = {
    "HAWKING_1975": {
        "title": "Particle Creation by Black Holes",
        "author": "S. W. Hawking",
        "year": 1975,
        "role": "Hawking radiation / black-hole temperature foundation"
    },
    "BEKENSTEIN_HAWKING_AREA_LAW": {
        "title": "Bekenstein-Hawking area law",
        "role": "Black-hole entropy proportional to horizon area"
    },
    "ISLAND_QES_PRESCRIPTION": {
        "title": "Island / quantum extremal surface prescription",
        "role": "Fine-grained radiation entropy via generalized-entropy competition"
    },
    "TOY_V02": {
        "title": "Black Hole Information Digital Twin toy model v0.2",
        "role": "Normalized branch functions used only for the conceptual engine"
    }
}

PROVENANCE = {
    "schwarzschild_radius_m": ProvenanceRecord(
        "schwarzschild_radius_m", "SCHW-RS", "r_s = 2 G M / c^2",
        ("Schwarzschild black hole", "zero charge", "zero angular momentum"),
        ("BEKENSTEIN_HAWKING_AREA_LAW",), "established_gr_semiclassical", "equation_tested"),
    "hawking_temperature_K": ProvenanceRecord(
        "hawking_temperature_K", "HAWK-T", "T_H = ħ c^3 / (8 π G M k_B)",
        ("Schwarzschild black hole", "semiclassical QFT on curved spacetime"),
        ("HAWKING_1975",), "established_semiclassical", "equation_tested"),
    "bh_entropy_normalized": ProvenanceRecord(
        "bh_entropy_normalized", "BH-S", "S_BH = k_B c^3 A / (4 G ħ); normalized by S_BH(M0)",
        ("Bekenstein-Hawking area law", "Schwarzschild horizon area A=4πr_s^2"),
        ("BEKENSTEIN_HAWKING_AREA_LAW",), "established_semiclassical", "equation_tested"),
    "mass_normalized": ProvenanceRecord(
        "mass_normalized", "EVAP-M", "M(τ)/M0 = (1-τ)^(1/3)",
        ("toy evaporation law dM/dt ∝ -1/M^2", "no accretion", "fixed effective species", "no spin or charge"),
        ("TOY_V02",), "toy_semiclassical", "scaling_tested"),
    "hawking_branch_entropy": ProvenanceRecord(
        "hawking_branch_entropy", "TOY-H", "S_H(τ) = 1 - (1-τ)^(2/3)",
        ("normalized toy branch", "chosen to track lost BH entropy fraction"),
        ("TOY_V02",), "toy_information_model", "monotonicity_tested"),
    "island_branch_entropy": ProvenanceRecord(
        "island_branch_entropy", "TOY-I", "S_I(τ) = (1-τ)^(2/3)",
        ("normalized toy branch", "conceptual proxy for the competing generalized-entropy saddle"),
        ("ISLAND_QES_PRESCRIPTION", "TOY_V02"), "toy_information_model", "monotonicity_tested"),
    "radiation_entropy": ProvenanceRecord(
        "radiation_entropy", "QES-MIN", "S_rad = min(S_H, S_I) for ISLAND_QES",
        ("two-branch toy generalized-entropy competition",),
        ("ISLAND_QES_PRESCRIPTION", "TOY_V02"), "toy_qes_prescription", "branch_transition_tested"),
    "page_time": ProvenanceRecord(
        "page_time", "PAGE-X", "solve S_H(τ_page) = S_I(τ_page)",
        ("Page transition identified with branch crossing in this toy model",),
        ("ISLAND_QES_PRESCRIPTION", "TOY_V02"), "model_derived_not_universal", "bisection_tested")
}

def provenance_for(field: str):
    if field not in PROVENANCE:
        raise KeyError(f"No provenance registered for {field}")
    return PROVENANCE[field].to_dict()
