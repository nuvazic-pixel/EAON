"""Regression checks for isolation policy and honest verifier result counting."""
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from _verify_runner import OfflineViolation, Results, install_guards
from verify_workspace import clean_environment, suites


class VerificationTests(unittest.TestCase):
    def test_environment_drops_credentials_endpoints_and_python_overrides(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "synthetic-test-value", "DATABASE_URL": "synthetic-test-value",
            "OLLAMA_HOST": "synthetic-test-value", "PYTHONPATH": "unsafe",
            "PYTEST_ADDOPTS": "--ignore=tests", "INTEL_ENABLED": "true",
        }):
            env = clean_environment(Path("isolated-home"))
        for name in ("OPENAI_API_KEY", "DATABASE_URL", "OLLAMA_HOST", "PYTHONPATH", "PYTEST_ADDOPTS"):
            self.assertNotIn(name, env)
        self.assertEqual(env["INTEL_ENABLED"], "false")
        self.assertEqual(env["PYTHON_DOTENV_DISABLED"], "1")
        self.assertEqual(env["HOME"], "isolated-home")

    def test_guard_records_even_a_caught_network_or_process_error(self):
        hooks = []
        with patch("sys.addaudithook", side_effect=hooks.append):
            attempts = install_guards()
        for event in ("socket.__new__", "socket.getaddrinfo", "subprocess.Popen", "os.system"):
            with self.subTest(event=event):
                with self.assertRaises(OfflineViolation):
                    hooks[0](event, ())
        self.assertEqual(attempts, ["socket I/O: socket.__new__", "socket I/O: socket.getaddrinfo",
                                    "child process launch: subprocess.Popen", "child process launch: os.system"])

    def test_guard_denies_dotenv_variants_without_reading_their_contents(self):
        hooks = []
        with patch("sys.addaudithook", side_effect=hooks.append):
            attempts = install_guards()
        for name in (".env", ".env.local", ".ENV.PRODUCTION"):
            with self.assertRaises(OfflineViolation):
                hooks[0]("open", (str(Path("anywhere") / name), "r", 0))
        hooks[0]("open", (".env.example", "r", 0))
        hooks[0]("open", ("source.py", "r", 0))
        self.assertEqual(len(attempts), 3)

    def test_teardown_and_collection_errors_cannot_be_counted_as_passes(self):
        plugin = Results()
        plugin.pytest_collection_finish(SimpleNamespace(items=[SimpleNamespace(nodeid="case")]))
        plugin.pytest_runtest_logreport(SimpleNamespace(nodeid="case", when="call", failed=False, skipped=False))
        plugin.pytest_runtest_logreport(SimpleNamespace(nodeid="case", when="teardown", failed=True, skipped=False))
        plugin.pytest_collectreport(SimpleNamespace(failed=True))
        self.assertEqual(plugin.counts()["passed"], 0)
        self.assertEqual(plugin.counts()["errors"], 2)

    def test_subtests_are_reported_separately_from_collected_tests(self):
        plugin = Results()
        plugin.pytest_collection_finish(SimpleNamespace(items=[SimpleNamespace(nodeid="case")]))
        plugin.pytest_runtest_logreport(SimpleNamespace(nodeid="case", context={}, failed=False))
        plugin.pytest_runtest_logreport(SimpleNamespace(nodeid="case", when="call", failed=False, skipped=False))
        self.assertEqual(plugin.counts()["collected"], 1)
        self.assertEqual(plugin.counts()["passed"], 1)
        self.assertEqual(plugin.counts()["subtests"], 1)

    def test_biolab_is_discovered_only_when_its_test_directory_exists(self):
        with patch("verify_workspace.Path.is_dir", return_value=False):
            self.assertNotIn("biolab", {suite.key for suite in suites()})
        with patch("verify_workspace.Path.is_dir", return_value=True):
            biolab = next(suite for suite in suites() if suite.key == "biolab")
        self.assertEqual((biolab.folder, biolab.import_root), ("modules/biolab", "src"))


if __name__ == "__main__":
    unittest.main()
