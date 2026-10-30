from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eaon.cli import main
from eaon.memory import MemoryStore
from eaon.models import MemoryRecord
from eaon.orchestrator import EAONOrchestrator


class MemoryIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "memory.jsonl"
        self.store = MemoryStore(self.path)

    def tamper(self) -> bytes:
        self.store.append(kind="note", text="Confirmed local memory.")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["text"] = "Forged local memory."
        self.path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return self.path.read_bytes()

    def test_all_memory_reads_and_append_reject_tampered_records(self) -> None:
        before = self.tamper()
        operations = {
            "records": self.store.records,
            "last_hash": self.store.last_hash,
            "search": lambda: self.store.search("local memory"),
            "empty_search": lambda: self.store.search(""),
            "snapshot": self.store.snapshot,
            "append": lambda: self.store.append(kind="note", text="Another note."),
        }
        for name, operation in operations.items():
            with self.subTest(operation=name):
                with self.assertRaises(ValueError):
                    operation()
                self.assertEqual(self.path.read_bytes(), before)

    def test_think_rejects_before_council_or_writes(self) -> None:
        before = self.tamper()
        orchestrator = EAONOrchestrator(self.path)
        with patch.object(orchestrator.council, "respond", wraps=orchestrator.council.respond) as council:
            with self.assertRaises(ValueError):
                orchestrator.think("What does local memory say?")
            council.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_unmatched_record_still_blocks_retrieval(self) -> None:
        self.tamper()
        with self.assertRaises(ValueError):
            self.store.search("completely unrelated query")

    def test_rehashed_broken_link_is_rejected(self) -> None:
        self.store.append(kind="note", text="First local memory.")
        self.store.append(kind="note", text="Second local memory.")
        rows = self.path.read_text(encoding="utf-8").splitlines()
        payload = json.loads(rows[1])
        payload["previous_hash"] = "not-the-first-record"
        rows[1] = json.dumps(MemoryRecord.from_dict(payload).signed().to_dict())
        self.path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.search("local memory")
        ok, errors = self.store.verify_chain()
        self.assertFalse(ok)
        self.assertIn("previous_hash", " ".join(errors))

    def test_corrupt_data_is_reported_without_overwriting_it(self) -> None:
        for content in ('{"broken":', '{"text": "missing required fields"}\n', '[]\n'):
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                before = self.path.read_bytes()
                ok, errors = self.store.verify_chain()
                self.assertFalse(ok)
                self.assertTrue(errors)
                with self.assertRaises(ValueError):
                    self.store.records()
                self.assertEqual(self.path.read_bytes(), before)

    def test_append_preserves_a_valid_journal_without_final_newline(self) -> None:
        first = self.store.append(kind="note", text="First local memory.")
        self.path.write_bytes(self.path.read_bytes().rstrip(b"\n"))
        self.assertEqual(self.store.verify_chain(), (True, []))
        second = self.store.append(kind="note", text="Second local memory.")
        self.assertEqual(second.previous_hash, first.content_hash)
        self.assertEqual([record.id for record in self.store.records()], [first.id, second.id])
        self.assertEqual(self.store.verify_chain(), (True, []))

    def test_invalid_unicode_payload_is_reported_and_blocks_cli(self) -> None:
        self.store.append(kind="note", text="Valid local memory.")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["text"] = "\ud800"
        self.path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        before = self.path.read_bytes()
        ok, errors = self.store.verify_chain()
        self.assertFalse(ok)
        self.assertTrue(errors)
        for command in (["verify"], ["recall", "local memory"]):
            with self.subTest(command=command[0]):
                output = io.StringIO()
                with redirect_stdout(output):
                    status = main(["--memory", str(self.path), "--json", *command])
                self.assertEqual(status, 1)
                self.assertFalse(json.loads(output.getvalue())["ok"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_valid_memory_survives_a_new_session(self) -> None:
        first_session = EAONOrchestrator(self.path)
        saved = first_session.remember("Decision: test local memory before integration.")
        second_session = EAONOrchestrator(self.path)
        recalled = second_session.recall("local memory")
        self.assertEqual(recalled[0]["id"], saved["id"])
        result = second_session.think("How should I test local memory?")
        self.assertIn(saved["id"], [item["id"] for item in result["memories"]])
        self.assertTrue(second_session.verify_memory()["ok"])

    def test_missing_and_empty_journals_are_valid(self) -> None:
        self.assertEqual(self.store.records(), [])
        self.assertEqual(self.store.search("local memory"), [])
        self.assertEqual(self.store.verify_chain(), (True, []))
        self.path.write_text("", encoding="utf-8")
        self.assertEqual(self.store.snapshot(), [])
        self.assertEqual(self.store.verify_chain(), (True, []))

    def test_search_validates_the_snapshot_it_returns(self) -> None:
        saved = self.store.append(kind="note", text="Confirmed local memory.")
        original_read = self.path.read_text(encoding="utf-8")
        forged = json.loads(original_read)
        forged["text"] = "Forged local memory."
        forged_read = json.dumps(forged) + "\n"
        with patch.object(Path, "open", side_effect=[
            io.StringIO(original_read),
            io.StringIO(forged_read),
        ]) as read:
            result = self.store.search("local memory")
        self.assertEqual(read.call_count, 1)
        self.assertEqual(result[0].id, saved.id)
        self.assertEqual(result[0].text, saved.text)

    def test_cli_blocks_corrupt_memory_without_a_traceback(self) -> None:
        before = self.tamper()
        commands = (
            ["think", "Check local memory"],
            ["recall", "local memory"],
            ["snapshot"],
            ["remember", "Another note"],
        )
        for command in commands:
            with self.subTest(command=command[0]):
                output = io.StringIO()
                with redirect_stdout(output):
                    status = main(["--memory", str(self.path), "--json", *command])
                self.assertEqual(status, 1)
                result = json.loads(output.getvalue())
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "memory_integrity_failed")
                self.assertNotIn("Forged", output.getvalue())
                self.assertEqual(self.path.read_bytes(), before)

    def test_cli_verify_reports_malformed_json(self) -> None:
        self.path.write_text('{"broken":', encoding="utf-8")
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["--memory", str(self.path), "--json", "verify"])
        self.assertEqual(status, 1)
        self.assertFalse(json.loads(output.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
