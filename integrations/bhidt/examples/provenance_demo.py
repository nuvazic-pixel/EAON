from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.simulation import BlackHoleSimulation
from engine.explain import explain_field, explain_transition

sim = BlackHoleSimulation(1e12)
pt = sim.page_time
before = sim.snapshot(pt - 0.01)
after = sim.snapshot(pt + 0.01)

print("FIELD EXPLANATION")
print(json.dumps(explain_field(after, "hawking_temperature_K"), indent=2))
print("\nPAGE-TIME PROVENANCE")
print(json.dumps(explain_field(after, "page_time"), indent=2))
print("\nTRANSITION EXPLANATION")
print(json.dumps(explain_transition(before, after), indent=2))
