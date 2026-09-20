from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.simulation import BlackHoleSimulation

sim = BlackHoleSimulation(1e12)

print("tau     M/M0    T_H[K]       S_BH   Hawking  Island   dominant")
for tau in [0.10, 0.30, sim.page_time, 0.70, 0.95]:
    s = sim.snapshot(tau)
    print(
        f'{tau:0.4f}  '
        f'{s["mass_normalized"]:0.4f}  '
        f'{s["hawking_temperature_K"]:9.3e}  '
        f'{s["bh_entropy_normalized"]:0.4f}  '
        f'{s["hawking_branch_entropy"]:0.4f}   '
        f'{s["island_branch_entropy"]:0.4f}   '
        f'{s["dominant_saddle"]}'
    )

print(f"Derived Page transition tau={sim.page_time:.12f}")
