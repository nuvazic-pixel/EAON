"""Exercise real Streamlit session transitions with a synthetic project/model."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from streamlit.testing.v1 import AppTest
    from core.telemetry import TelemetryRecorder
    from eaon_kernel import ContinuityKernel

    with tempfile.TemporaryDirectory(prefix="eaon-project-ui-") as folder:
        path = Path(folder) / "fixture.db"
        kernel = ContinuityKernel.create(path)
        kernel.create_project("alpha", "Synthetic Alpha")
        kernel.create_project("beta", "Synthetic Beta")
        kernel.record_memory("alpha", "unknown", "ALPHA_PRIVATE_FIXTURE", status="unknown")
        before = kernel.verify()
        calls = []
        def transport(route, payload=None, **kwargs):
            if route == "/api/tags":
                return {"models": [{"name": "llama3"}, {"name": "mistral"}]}
            assert route == "/api/chat"
            calls.append(payload)
            return {"message": {"content": "Synthetic answer"}}
        def widget(elements, label):
            return next(item for item in elements if item.label == label)
        def connect(app, project_id):
            widget(app.text_input, "Fișierul proiectului").set_value(str(path))
            widget(app.text_input, "Identificator proiect").set_value(project_id)
            widget(app.button, "Conectează proiectul").click().run()
            assert not app.exception

        with patch("dotenv.load_dotenv", return_value=False), \
             patch("core.ollama_client._request", side_effect=transport), \
             patch("core.orchestrator.TelemetryRecorder", side_effect=lambda: TelemetryRecorder(Path(folder) / "telemetry.jsonl")), \
             patch("ui.voice_backend.model_ready", return_value=False):
            app = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=15).run()
            assert not app.exception
            connect(app, "alpha")
            app.chat_input[0].set_value("Summarize current project").run()
            assert not app.exception
            assert len(app.session_state["messages"]) == 2
            assert "ALPHA_PRIVATE_FIXTURE" in calls[-1]["messages"][-2]["content"]
            app.session_state["draft"] = "old voice fixture"
            app.session_state["draft_stt_ms"] = 12
            connect(app, "beta")
            assert app.session_state["messages"] == [] and app.session_state["draft"] == ""
            assert app.session_state["draft_stt_ms"] is None
            app.chat_input[0].set_value("Summarize current project").run()
            assert "ALPHA_PRIVATE_FIXTURE" not in json.dumps(calls[-1])
            assert "Synthetic Beta" in calls[-1]["messages"][-2]["content"]
            connect(app, "absent")
            assert app.error and app.session_state["project_context"].project_id == "beta"
            assert len(app.session_state["messages"]) == 2
            widget(app.button, "Șterge conversația").click().run()
            assert app.session_state["messages"] == []
            assert app.session_state["project_context"].project_id == "beta"
            widget(app.button, "Deconectează proiectul").click().run()
            assert app.session_state["project_context"] is None and app.session_state["messages"] == []
            app.chat_input[0].set_value("Ordinary chat").run()
            assert not app.exception
            assert not any(message["content"].startswith("EAON_PROJECT_CONTEXT_V1\n") for message in calls[-1]["messages"])
        assert kernel.verify() == before
        assert "ALPHA_PRIVATE_FIXTURE" not in (Path(folder) / "telemetry.jsonl").read_text()
        print(json.dumps({"ok": True, "ui": "real Streamlit AppTest", "models": "synthetic transport",
              "checks": ["attach and model context", "project switch clears chat/voice state",
                         "failed attach preserves session", "clear keeps binding", "detach",
                         "no journal append", "no source text in telemetry"]}, indent=2))


if __name__ == "__main__":
    main()
