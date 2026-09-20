from pathlib import Path
import json
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.eaon_adapter import EAONVerificationAdapter
from engine.experiment import ExperimentConfig, ExperimentRunner


output = Path(__file__).resolve().parent / "output" / "demo-v04"
if output.exists():
    shutil.rmtree(output)

runner = ExperimentRunner(
    output,
    ExperimentConfig(initial_mass_kg=1e12, model="ISLAND_QES", steps=101),
    experiment_id="BH-0007",
)
runner.run()

adapter = EAONVerificationAdapter(output)
report = adapter.verify_experiment()

print("BHIDT v0.4 — DETERMINISTIC VERIFICATION")
print(f"experiment_id:       {report['experiment_id']}")
print(f"status:              {report['status']}")
print(f"journal_valid:       {report['journal']['hash_chain_valid']}")
print(f"snapshots_compared:  {report['comparison']['snapshots_compared']}")
print(f"max_abs_error:       {report['comparison']['max_abs_error']:.3e}")
print(f"max_rel_error:       {report['comparison']['max_rel_error']:.3e}")
print(
    "page_transition:    "
    f"{report['page_transition']['recorded']:.12f} "
    f"-> {report['page_transition']['recomputed']:.12f}"
)
print()
print("Fingerprint:")
for key, item in report["fingerprint"]["fields"].items():
    print(f"  {key:24s} {'MATCH' if item['match'] else 'MISMATCH'}")

(output / "verification-report.json").write_text(
    json.dumps(report, indent=2, sort_keys=True),
    encoding="utf-8",
)
