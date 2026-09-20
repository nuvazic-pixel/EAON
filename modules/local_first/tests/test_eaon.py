import tempfile
import unittest
from pathlib import Path

from eaon import EAON


class EAONTests(unittest.TestCase):
    def test_ingest_deduplicate_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            tmp_path = Path(folder)
            source = tmp_path / "paper.txt"
            source.write_text(
                "The experiment shows that local memory reduces accidental cloud exposure. "
                "Independent validation indicates that evidence tracking improves auditability.",
                encoding="utf-8",
            )
            eaon = EAON(tmp_path / "eaon.db", model="model-that-does-not-exist")
            first = eaon.ingest(source)
            second = eaon.ingest(source)
            result = eaon.run("Does local memory reduce cloud exposure?")
            self.assertEqual(first["claims_added"], 2)
            self.assertEqual(second["status"], "duplicate")
            self.assertTrue(result.evidence)
            self.assertEqual(result.route.backend, "extractive")
            self.assertNotIn("#", result.evidence[0].text)
            self.assertEqual(eaon.memory.stats(), {"sources": 1, "claims": 2, "runs": 1})

    def test_export(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            tmp_path = Path(folder)
            eaon = EAON(tmp_path / "eaon.db")
            destination = eaon.export(tmp_path / "backup.json")
            self.assertTrue(destination.exists())
            self.assertIn('"sources": []', destination.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
