import copy
import json
import tempfile
import unittest
from pathlib import Path

from engine.comparator import FloatPolicy, compare_snapshots
from engine.eaon_adapter import EAONVerificationAdapter
from engine.experiment import ExperimentConfig, ExperimentRunner
from engine.journal import canonical_json
from engine.verification import verify_experiment


class TestVerificationV04(unittest.TestCase):
    def make_experiment(self, root: Path):
        exp_dir = root / "BH-0007"
        runner = ExperimentRunner(
            exp_dir,
            ExperimentConfig(
                initial_mass_kg=1e12,
                model="ISLAND_QES",
                steps=101,
            ),
            experiment_id="BH-0007",
        )
        result = runner.run()
        return exp_dir, result

    def test_clean_experiment_is_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            exp_dir, _ = self.make_experiment(Path(tmp))
            report = verify_experiment(exp_dir)
            self.assertEqual(report["status"], "MATCH")
            self.assertTrue(report["journal"]["hash_chain_valid"])
            self.assertEqual(report["comparison"]["snapshots_compared"], 101)
            self.assertIsNone(report["comparison"]["first_divergence"])

    def test_comparator_reports_drift_for_numeric_tolerance_failure(self):
        recorded = [{
            "tau": 0.5,
            "hawking_temperature_K": 100.0,
            "dominant_saddle": "NO_ISLAND",
        }]
        recomputed = copy.deepcopy(recorded)
        recomputed[0]["hawking_temperature_K"] = 100.0001

        result = compare_snapshots(
            recorded,
            recomputed,
            policy=FloatPolicy(abs_tol=1e-12, rel_tol=1e-10),
            recorded_event_seqs=[42],
        )
        self.assertEqual(result["status"], "DRIFT")
        self.assertEqual(result["first_divergence"]["field"], "hawking_temperature_K")
        self.assertEqual(result["first_divergence"]["seq"], 42)
        self.assertIn("provenance", result["first_divergence"])

    def test_comparator_reports_divergence_for_discrete_behavior_change(self):
        recorded = [{"tau": 0.65, "dominant_saddle": "NO_ISLAND"}]
        recomputed = [{"tau": 0.65, "dominant_saddle": "ISLAND"}]

        result = compare_snapshots(recorded, recomputed)
        self.assertEqual(result["status"], "DIVERGENCE")
        self.assertEqual(result["first_divergence"]["field"], "dominant_saddle")

    def test_fingerprint_mismatch_is_divergence(self):
        with tempfile.TemporaryDirectory() as tmp:
            exp_dir, _ = self.make_experiment(Path(tmp))
            manifest_path = exp_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["reproducibility_fingerprint"]["code_hash"] = "deadbeef"
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            report = verify_experiment(exp_dir)
            self.assertEqual(report["status"], "DIVERGENCE")
            self.assertEqual(report["first_divergence"]["field"], "code_hash")

    def test_invalid_journal_is_unverifiable(self):
        with tempfile.TemporaryDirectory() as tmp:
            exp_dir, _ = self.make_experiment(Path(tmp))
            journal_path = exp_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in journal_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            events[1]["payload"]["snapshot"]["mass_normalized"] = 123.0
            journal_path.write_text(
                "\n".join(canonical_json(e) for e in events) + "\n",
                encoding="utf-8",
            )

            report = verify_experiment(exp_dir)
            self.assertEqual(report["status"], "UNVERIFIABLE")
            self.assertEqual(report["reason"], "journal_integrity_failed")

    def test_eaon_adapter_uses_verification_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            exp_dir, _ = self.make_experiment(Path(tmp))
            adapter = EAONVerificationAdapter(exp_dir)
            report = adapter.verify_experiment()
            self.assertEqual(report["status"], "MATCH")

            assumptions = adapter.show_assumptions("ISLAND_QES")
            self.assertIn("radiation_entropy", assumptions["fields"])

            transition = adapter.explain_transition()
            self.assertIn("transition", transition)


if __name__ == "__main__":
    unittest.main()
