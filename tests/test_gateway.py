import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.inference_gateway import InferenceGateway, ModelDispatchError
from core.orchestrator import Orchestrator, Priority, RoutingDecision


def decision(model):
    return RoutingDecision(intent="general", model=model, priority=Priority.NORMAL,
                           reason="test", mode="normal")


class GatewayTests(unittest.TestCase):
    def test_missing_or_unknown_model_does_not_call_a_handler(self):
        called = []
        gateway = InferenceGateway({"llama3": lambda prompt: called.append(prompt) or "ok"})
        for model in (None, "", "unknown", "LLAMA3"):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ModelDispatchError, "unknown_model_id"):
                    gateway.dispatch(model, "hello")
        self.assertEqual(called, [])

    def test_exact_model_dispatch_and_blank_response(self):
        gateway = InferenceGateway({"llama3": lambda _: "answer",
                                    "mistral": lambda _: "  "})
        self.assertEqual(gateway.dispatch("llama3", "hello"), "answer")
        with self.assertRaisesRegex(ModelDispatchError, "empty_model_response"):
            gateway.dispatch("mistral", "hello")

    def test_orchestrator_rejects_unknown_and_reports_ollama_failure(self):
        orchestrator = Orchestrator.__new__(Orchestrator)
        orchestrator._error_count = 0
        orchestrator.orch_config = SimpleNamespace(timeout_seconds=1)
        with patch.object(orchestrator, "_call_llama") as handler:
            report = orchestrator._execute("hello", decision("unregistered"))
            self.assertFalse(report.ok)
            self.assertEqual(report.error, "unknown_model_id")
            handler.assert_not_called()
        with patch("requests.post", side_effect=ConnectionError("offline")):
            report = orchestrator._execute("hello", decision("llama3"))
            self.assertFalse(report.ok)
            self.assertEqual(report.error, "llama3_unavailable")
            self.assertIsNone(report.output_text)
        self.assertEqual(orchestrator._error_count, 2)

    def test_orchestrator_reports_success_only_for_actual_model_output(self):
        orchestrator = Orchestrator.__new__(Orchestrator)
        orchestrator._error_count = 0
        with patch.object(orchestrator, "_call_mistral", return_value="  "):
            report = orchestrator._execute("hello", decision("mistral"))
            self.assertFalse(report.ok)
            self.assertEqual(report.error, "empty_model_response")
        with patch.object(orchestrator, "_call_mistral", return_value="real output"):
            report = orchestrator._execute("hello", decision("mistral"))
            self.assertTrue(report.ok)
            self.assertEqual(report.output_text, "real output")


if __name__ == "__main__":
    unittest.main()
