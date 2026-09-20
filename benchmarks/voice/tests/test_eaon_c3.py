import json
import tempfile
import unittest
from pathlib import Path

from eaon_c3.journal import StateJournal, verify
from eaon_c3.metrics import summarize, word_error_rate


class JournalTests(unittest.TestCase):
    def test_hash_chain_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            journal = StateJournal(path)
            journal.transition("s1", "wake", "listening", "detected", 4.2)
            journal.append("Observation", "voice_session/s1", {"wer": 0})
            self.assertEqual(verify(path), (True, 2, None))
            lines = path.read_text(encoding="utf-8").splitlines()
            record = json.loads(lines[0]); record["payload"]["latency_ms"] = 999
            lines[0] = json.dumps(record)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.assertFalse(verify(path)[0])

    def test_metrics(self):
        self.assertEqual(word_error_rate("EAON aprinde lumina", "eaon aprinde lumina"), 0)
        self.assertAlmostEqual(word_error_rate("turn on light", "turn light"), 1 / 3)
        summary = summarize([{"language": "ro", "wer": .2, "wake_expected": False,
                              "wake_detected": True, "latencies_ms": {"stt": 100}}])
        self.assertEqual(summary["wake"]["false_accept_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
