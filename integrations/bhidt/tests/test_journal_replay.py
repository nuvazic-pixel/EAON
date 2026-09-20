import copy
import json
import tempfile
import unittest
from pathlib import Path

from engine.experiment import ExperimentConfig, ExperimentRunner
from engine.journal import ExperimentJournal, canonical_json
from engine.replay import replay_snapshots, replay_around_transition


class TestJournalReplay(unittest.TestCase):
    def run_experiment(self, root: Path, experiment_id="test-exp"):
        cfg = ExperimentConfig(
            initial_mass_kg=1e12,
            model="ISLAND_QES",
            steps=101,
            tau_start=0.0,
            tau_end=0.999999,
        )
        runner = ExperimentRunner(root / experiment_id, cfg, experiment_id=experiment_id)
        return runner, runner.run()

    def test_journal_chain_valid_and_snapshots_replay_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner, result = self.run_experiment(Path(tmp))
            self.assertTrue(result["journal_verification"]["valid"])

            replayed = replay_snapshots(runner.journal_path)
            self.assertEqual(replayed, result["snapshots"])
            self.assertEqual(len(replayed), 101)

    def test_page_transition_is_journaled_and_replayable(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner, result = self.run_experiment(Path(tmp))
            window = replay_around_transition(runner.journal_path, before=2, after=2)

            self.assertEqual(
                window["transition_event"]["event_type"],
                "PAGE_TRANSITION",
            )
            saddles = [s["dominant_saddle"] for s in window["snapshots"]]
            self.assertIn("NO_ISLAND", saddles)
            self.assertIn("ISLAND", saddles)

    def test_checkpoint_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner, _ = self.run_experiment(Path(tmp))
            checkpoint = json.loads(runner.checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["reason"], "experiment_completed")
            self.assertIn("journal_hash", checkpoint)
            self.assertIn("snapshot", checkpoint)

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner, _ = self.run_experiment(Path(tmp))
            events = runner.journal.read_events()

            # Change an old snapshot while leaving its stored hash untouched.
            for event in events:
                if event["event_type"] == "SNAPSHOT":
                    event["payload"]["snapshot"]["mass_normalized"] = 123.0
                    break

            tampered = Path(tmp) / "tampered.jsonl"
            tampered.write_text(
                "\n".join(canonical_json(e) for e in events) + "\n",
                encoding="utf-8",
            )
            journal = ExperimentJournal(tampered, "test-exp")
            result = journal.verify_chain()
            self.assertFalse(result["valid"])
            self.assertEqual(result["error"], "record_hash_mismatch")

    def test_existing_journal_cannot_be_silently_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_experiment(root)
            cfg = ExperimentConfig()
            with self.assertRaises(FileExistsError):
                ExperimentRunner(root / "test-exp", cfg, experiment_id="test-exp")


if __name__ == "__main__":
    unittest.main()
