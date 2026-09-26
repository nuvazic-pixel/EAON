import unittest
import json
import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from core.inference_gateway import InferenceGateway, ModelDispatchError
from core.orchestrator import ExecutionReport, IntelContext, Orchestrator, Priority, RoutingDecision
from core.ollama_client import OllamaError, chat
from core.telemetry import TelemetryRecorder


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
        with patch("core.orchestrator.ollama_chat", side_effect=OllamaError("ollama_unavailable")):
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
        with patch.object(orchestrator, "_call_llama",
                          side_effect=RuntimeError("private phrase from model")):
            report = orchestrator._execute("hello", decision("llama3"))
            self.assertEqual(report.error, "execution_error")
            self.assertNotIn("private phrase", str(report))

    def test_client_limits_context_and_rejects_unapproved_model(self):
        history = [{"role": "user", "content": str(i)} for i in range(14)]
        history += [{"role": "tool", "content": "do not forward"}]
        with patch("core.ollama_client._request",
                   return_value={"message": {"content": " Răspuns "}}) as call:
            self.assertEqual(chat("llama3", " Salut ", history), "Răspuns")
            with self.assertRaisesRegex(OllamaError, "unknown_model_id"):
                chat("other", "Salut", history)
        call.assert_called_once()
        path, payload = call.call_args.args
        self.assertEqual(path, "/api/chat")
        self.assertEqual(payload["model"], "llama3")
        self.assertEqual(len(payload["messages"]), 14)
        self.assertEqual(payload["messages"][-1], {"role": "user", "content": "Salut"})
        self.assertEqual(payload["messages"][1]["content"], "2")
        self.assertNotIn("tool", {turn["role"] for turn in payload["messages"]})

    def test_one_orchestration_path_for_voice_text_and_telemetry(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "telemetry.jsonl"
            orchestrator = Orchestrator(local_only=True, telemetry=TelemetryRecorder(path))
            calls = []

            def model_response(route, payload, *, timeout):
                calls.append(payload)
                return {"message": {"content": "Un răspuns local"}}

            with patch("core.ollama_client._request", side_effect=model_response), \
                    patch.object(orchestrator, "_enrich_intel") as intel, \
                    patch.object(orchestrator, "_post_process") as external:
                decision, report = orchestrator.run(
                    "Cum tratez un atac? PRIVATE_SENTINEL", source="voice", stt_ms=12.5)
                self.assertTrue(report.ok)
                self.assertEqual(decision.intent, "security")
                self.assertEqual(decision.model, "mistral")
                self.assertEqual(calls[0]["model"], "mistral")
                history = [{"role": "user", "content": "Cum tratez un atac?"},
                           {"role": "assistant", "content": report.output_text,
                            "route": {"model": "mistral"}}]
                decision2, report2 = orchestrator.run(
                    "Scrie un script", history=history, source="text")
                self.assertTrue(report2.ok)
                self.assertEqual(decision2.model, "llama3")
                self.assertEqual(calls[1]["model"], "llama3")
                self.assertEqual(calls[1]["messages"][-2]["content"], "Un răspuns local")
                intel.assert_not_called()
                external.assert_not_called()
            with patch("core.orchestrator.ollama_chat", side_effect=OllamaError("model_missing")):
                _, failed = orchestrator.run("Salut", source="text")
            self.assertFalse(failed.ok)
            self.assertEqual(failed.error, "model_missing")
            self.assertEqual(orchestrator.get_stats()["error_count"], 1)
            cli = Orchestrator(telemetry=TelemetryRecorder(path))
            with patch.object(cli, "_enrich_intel", return_value=IntelContext()), \
                    patch.object(cli, "_post_process"), \
                    patch("core.ollama_client._request", side_effect=model_response):
                cli_decision, cli_report = cli.run("Explică pe scurt")
            self.assertTrue(cli_report.ok)
            self.assertEqual(cli_decision.model, "llama3")
            contents = path.read_text(encoding="utf-8")
            self.assertNotIn("PRIVATE_SENTINEL", contents)
            self.assertNotIn("Un răspuns local", contents)
            events = [json.loads(line) for line in contents.splitlines()]
            self.assertEqual([item["source"] for item in events], ["voice", "text", "text", "cli"])
            self.assertEqual(events[0]["stt_ms"], 12.5)
            self.assertEqual(events[2]["error_code"], "model_missing")
            self.assertEqual(set(events[0]), {
                "request_id", "source", "intent", "model", "mode", "ok",
                "error_code", "total_ms", "inference_ms", "stt_ms", "timestamp",
            })

    def test_cli_interactive_keeps_bounded_turn_context(self):
        from main import interactive_loop

        class FakeOrchestrator:
            def __init__(self):
                self.seen = []

            def run(self, prompt, *, history):
                self.seen.append((prompt, list(history)))
                return decision("llama3"), ExecutionReport(ok=True, output_text="reply", model_used="llama3")

        orchestrator = FakeOrchestrator()
        with patch("builtins.input", side_effect=["Salut", "Continua", "exit"]), \
                patch("main.show_banner"), redirect_stdout(io.StringIO()):
            interactive_loop(orchestrator, None)
        self.assertEqual(orchestrator.seen[1][1], [
            {"role": "user", "content": "Salut"},
            {"role": "assistant", "content": "reply"},
        ])

    def test_missing_german_security_model_has_no_silent_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            orchestrator = Orchestrator(
                local_only=True, telemetry=TelemetryRecorder(Path(temporary) / "telemetry.jsonl"))
            with patch("core.orchestrator.ollama_chat",
                       side_effect=OllamaError("model_missing")) as request:
                decision, report = orchestrator.run("Sicherheit und Angriff", source="text")
            self.assertEqual(decision.model, "mistral")
            self.assertFalse(report.ok)
            self.assertEqual(report.error, "model_missing")
            request.assert_called_once()
            self.assertEqual(request.call_args.args[0], "mistral")


if __name__ == "__main__":
    unittest.main()
