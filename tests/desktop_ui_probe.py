"""Actual Streamlit form acceptance probe; run explicitly, outside offline pytest."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from streamlit.testing.v1 import AppTest
    from core.project_files import list_backups
    from core.telemetry import TelemetryRecorder
    from eaon_kernel import ContinuityKernel

    def widget(elements, label):
        return next(item for item in elements if item.label == label)

    with tempfile.TemporaryDirectory(prefix="eaon-desktop-projects-") as temporary:
        folder = Path(temporary)
        source, restored = folder / "source.db", folder / "restored.db"
        def response(route, payload=None, **kwargs):
            assert route == "/api/tags", "These explicit project forms must not invoke a model"
            return {"models": [{"name": "llama3"}, {"name": "mistral"}]}
        with patch("dotenv.load_dotenv", return_value=False), \
             patch("core.ollama_client._request", side_effect=response), \
             patch("core.orchestrator.TelemetryRecorder", side_effect=lambda: TelemetryRecorder(folder / "telemetry.jsonl")), \
             patch("ui.voice_backend.model_ready", return_value=False):
            app = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=15).run()
            assert not app.exception
            widget(app.text_input, "Fișier pentru proiectul nou").set_value(str(source))
            widget(app.text_input, "Identificator proiect nou").set_value("p")
            widget(app.text_input, "Numele proiectului").set_value("Desktop fixture")
            widget(app.text_area, "Obiectiv inițial (opțional)").set_value("Verify the desktop flow")
            widget(app.text_input, "Prima sarcină (opțional)").set_value("Create a backup")
            widget(app.button, "Creează proiectul").click().run()
            assert not app.exception and app.session_state["project_context"].db == source.resolve()
            kernel = ContinuityKernel(source)
            assert kernel.recover("p")["next_task"]["text"] == "Create a backup"

            widget(app.text_input, "Numele memoriei").set_value("decision")
            widget(app.text_area, "Textul memoriei").set_value("Keep project state local")
            widget(app.selectbox, "Starea memoriei").set_value("Confirmat cu dovadă")
            widget(app.button, "Salvează memorie").click().run()
            assert app.error and not kernel.recover("p")["memories"]
            widget(app.text_input, "Adresa sursei noi (URI)").set_value("note://decision")
            widget(app.text_area, "Textul dovezii noi").set_value("Explicit source from a synthetic user")
            widget(app.button, "Salvează memorie").click().run()
            assert not app.exception and kernel.recover("p")["memories"]["decision"]["status"] == "confirmed"

            widget(app.selectbox, "Memoria de editat").set_value("decision").run()
            widget(app.text_area, "Textul memoriei").set_value("Stale edit")
            prior = kernel.recover("p")["memories"]["decision"]
            from eaon_kernel import SourceRef
            kernel.record_memory("p", "decision", "Concurrent update", status="confirmed",
                                 sources=tuple(SourceRef(**item) for item in prior["sources"]), expected_revision=1)
            widget(app.button, "Salvează memorie").click().run()
            assert kernel.recover("p")["memories"]["decision"]["text"] == "Concurrent update"
            assert widget(app.button, "Salvează memorie").disabled
            widget(app.button, "Reîncarcă memoria selectată").click().run()
            widget(app.text_area, "Textul memoriei").set_value("Reviewed update")
            widget(app.button, "Salvează memorie").click().run()
            assert kernel.recover("p")["memories"]["decision"]["revision"] == 3

            widget(app.text_input, "Folder pentru copii").set_value(str(folder / "backups")).run()
            widget(app.button, "Creează copie").click().run()
            assert not app.exception
            copy = list_backups(folder / "backups")[0]
            backup_digest = sha256(copy.read_bytes()).hexdigest()
            kernel.record_memory("p", "later", "Only the original has this later observation")
            original_head = kernel.verify()
            widget(app.text_input, "Fișier nou pentru restaurare").set_value(str(restored))
            widget(app.text_input, "Identificator pentru conectarea copiei").set_value("p")
            widget(app.button, "Restaurează copia").click().run()
            assert not app.exception and app.session_state["project_context"].db == restored.resolve()
            restored_kernel = ContinuityKernel(restored)
            assert "later" not in restored_kernel.recover("p")["memories"]
            assert kernel.verify() == original_head
            assert sha256(copy.read_bytes()).hexdigest() == backup_digest

            widget(app.selectbox, "Memoria de revocat").set_value("decision").run()
            widget(app.text_input, "Motivul revocării").set_value("Revoked explicitly by the synthetic user")
            widget(app.button, "Revocă memoria").click().run()
            assert not app.exception
            assert restored_kernel.recover("p")["memories"]["decision"]["lifecycle"] == "revoked"
            assert kernel.recover("p")["memories"]["decision"]["lifecycle"] == "active"
            assert app.session_state["messages"] == []
        print(json.dumps({"ok": True, "ui": "real Streamlit AppTest", "model_calls": 0,
            "checks": ["new project with goal and task", "confirmation needs evidence", "explicit evidence capture",
                       "stale edit blocked", "explicit revision reload", "verified backup", "restore into separate file",
                       "original and backup preserved", "explicit revocation clears conversation"]}, indent=2))


if __name__ == "__main__":
    main()
