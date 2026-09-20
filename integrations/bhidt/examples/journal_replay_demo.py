from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.experiment import ExperimentConfig, ExperimentRunner
from engine.replay import replay_around_transition


output = Path(__file__).resolve().parent / "output" / "demo-v03"
if output.exists():
    shutil.rmtree(output)

config = ExperimentConfig(
    initial_mass_kg=1e12,
    model="ISLAND_QES",
    steps=101,
)

runner = ExperimentRunner(output, config, experiment_id="demo-v03")
result = runner.run()
window = replay_around_transition(runner.journal_path, before=2, after=2)

print("BLACK HOLE INFORMATION DIGITAL TWIN — v0.3")
print(f"experiment_id: {result['experiment_id']}")
print(f"config_hash:   {result['config_hash']}")
print(f"snapshots:     {result['snapshot_count']}")
print(f"page_time:     {result['derived_page_time']:.12f}")
print(f"journal_valid: {result['journal_verification']['valid']}")
print()
print("Replay around Page transition:")
print("tau       Hawking    Island     dominant")
for s in window["snapshots"]:
    print(
        f"{s['tau']:.6f}  "
        f"{s['hawking_branch_entropy']:.6f}   "
        f"{s['island_branch_entropy']:.6f}   "
        f"{s['dominant_saddle']}"
    )
