"""Start with: python -m streamlit run ui/app.py --server.address 127.0.0.1"""

from __future__ import annotations

import hashlib
import html
from pathlib import Path
import sys
import time

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from core import Orchestrator  # noqa: E402
from core.ollama_client import OllamaError, MAX_PROMPT_CHARS, installed_models  # noqa: E402
from ui.voice_backend import VoiceUIError, create_recognizer, model_directory, model_ready, transcribe  # noqa: E402
from core.project_context import ProjectContextError  # noqa: E402
from core.voice_state import TranscriptDraft, VoiceStateError, commit_transcript  # noqa: E402
from ui.project_binding import (CONTEXT_PROBLEMS, FILE_PROBLEMS, attach_project, detach_project,
    reset_conversation, create_and_attach_project, restore_and_attach_project,
    memory_history, save_memory, revoke_saved_memory)  # noqa: E402
from core.project_files import ProjectFileError, create_backup, list_backups  # noqa: E402

st.set_page_config(page_title="EAON • conversație locală", page_icon="🎙️", layout="centered")
st.html("""
<style>
  .block-container { max-width: 820px; padding-top: 2rem; }
  [data-testid="stSidebar"] { border-right: 1px solid #333; }
  .eaon-kicker { letter-spacing: .2em; color: #94a3b8; font-size: .78rem; }
  .eaon-card { border: 1px solid #334155; border-radius: 14px; padding: 1rem;
               background: rgba(30,41,59,.45); margin: 1rem 0; }
</style>
""")


@st.cache_resource(show_spinner="Încarc modelul Sherpa...")
def recognizer_for(language: str):
    return create_recognizer(model_directory(ROOT), language)


def speak_button(message: str, index: int, language: str) -> None:
    """Fixed JavaScript; assistant text is escaped into a data attribute."""
    safe_message = html.escape(message[:4000], quote=True)
    safe_language = html.escape(language, quote=True)
    st.html(
        f'<button id="eaon-speak-{index}" data-message="{safe_message}" '
        f'data-language="{safe_language}" type="button" '
        'style="padding:.35rem .8rem; cursor:pointer; border-radius:.5rem">'
        '🔊 Ascultă răspunsul</button>'
        '<script>'
        f'const button = document.getElementById("eaon-speak-{index}");'
        'button.addEventListener("click", () => {'
        '  if (!window.speechSynthesis) { alert("Vocea nu este disponibilă în acest browser."); return; }'
        '  window.speechSynthesis.cancel();'
        '  const utterance = new SpeechSynthesisUtterance(button.dataset.message);'
        '  utterance.lang = button.dataset.language;'
        '  window.speechSynthesis.speak(utterance);'
        '});'
        '</script>',
        unsafe_allow_javascript=True,
    )


def send_message(prompt: str, source: str) -> None:
    prompt = prompt.strip()
    if not 0 < len(prompt) <= MAX_PROMPT_CHARS:
        st.error("Mesajul trebuie să aibă între 1 și 4000 de caractere.")
        return
    orchestrator = st.session_state.orchestrator
    if source == "voice":
        try:
            # Offline Sherpa returns final text; only this explicit submit commits it.
            draft = TranscriptDraft(st.session_state.draft, st.session_state.get("microphone_version", 0), final=True)
            committed = commit_transcript(draft, reviewed_text=prompt, user_confirmed=True,
                                          activation="explicit_submit", arguments_stable=True)
            decision, report = orchestrator.run_voice(committed, history=st.session_state.messages,
                                    stt_ms=st.session_state.get("draft_stt_ms"))
        except VoiceStateError:
            st.error("La trimitere este necesară o transcriere finală, verificată de tine.")
            return
    else:
        decision, report = orchestrator.run(prompt, history=st.session_state.messages, source=source)
    if not report.ok:
        problems = {
            "llama3_unavailable": "Ollama nu răspunde local. Pornește Ollama.",
            "mistral_unavailable": "Ollama nu răspunde local. Pornește Ollama.",
            "model_missing": f"Modelul lipsește. Rulează: ollama pull {decision.model}",
            "invalid_prompt": "Mesajul trebuie să aibă între 1 și 4000 de caractere.",
            "empty_model_response": "Ollama a trimis un răspuns gol. Încearcă din nou.",
            "voice_uncommitted": "Verifică transcrierea finală înainte de trimitere.",
            "model_identity_mismatch": "Modelul care a răspuns nu corespunde celui cerut. Cererea a fost oprită.",
            **CONTEXT_PROBLEMS,
        }
        st.error(problems.get(report.error, f"Cererea a eșuat ({report.error})."))
        return
    st.session_state.messages += [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": report.output_text,
         "route": {"intent": decision.intent, "model": decision.model,
                   "latency_ms": round(report.inference_time_ms)}},
    ]
    if source == "voice":
        st.session_state.draft = ""
        st.session_state.draft_stt_ms = None
    st.rerun()


st.markdown('<span class="eaon-kicker">EDGE AI ORCHESTRATION NODE</span>', unsafe_allow_html=True)
st.title("Vorbește cu EAON")
st.caption("Conversație locală • Microfon la cerere • Răspuns vocal la apăsarea butonului")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "draft" not in st.session_state:
    st.session_state.draft = ""
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = Orchestrator(local_only=True)

with st.sidebar:
    st.header("Orchestrare")
    st.caption("Routerul alege Llama 3 sau Mistral după intenție. Modul este local, fără integrări externe.")
    language_name = st.selectbox("Limba vorbită", ("Română", "Deutsch", "English", "Automat"))
    language = {"Română": "ro", "Deutsch": "de", "English": "en", "Automat": ""}[language_name]
    browser_language = language or "ro"
    st.subheader("Proiect")
    st.caption("Conectează un proiect existent pentru a folosi starea lui în conversație.")
    with st.form("project_binding"):
        project_db = st.text_input("Fișierul proiectului", value="data/continuity.db")
        project_id = st.text_input("Identificator proiect", value="demo")
        with st.expander("Documente din Synapse"):
            use_synapse = st.checkbox("Include dovezi din Synapse")
            synapse_url = st.text_input("Adresa locală Synapse", value="http://127.0.0.1:8000")
            collection_id = st.text_input("Colecția Synapse")
            st.caption("Accesul folosește SYNAPSE_TOKEN configurat pe acest calculator.")
        connect_project = st.form_submit_button("Conectează proiectul")
    if connect_project:
        try:
            attach_project(st.session_state, project_db.strip(), project_id.strip(),
                           synapse_url=synapse_url.strip() if use_synapse else None,
                           collection_id=collection_id.strip() if use_synapse else None)
        except ProjectContextError as exc:
            st.error(CONTEXT_PROBLEMS.get(str(exc), "Nu pot conecta proiectul."))
        else:
            st.rerun()
    with st.expander("Proiect nou"):
        st.caption("Creează un fișier nou. Proiectele existente sunt păstrate.")
        with st.form("new_project"):
            new_db = st.text_input("Fișier pentru proiectul nou", value="data/proiectul-meu.db")
            new_id = st.text_input("Identificator proiect nou", value="proiectul-meu")
            new_title = st.text_input("Numele proiectului", value="Proiectul meu")
            new_goal = st.text_area("Obiectiv inițial (opțional)")
            new_task = st.text_input("Prima sarcină (opțional)")
            new_owner = st.text_input("Proprietar (pentru Synapse)", value="local")
            create_project = st.form_submit_button("Creează proiectul")
        if create_project:
            try:
                create_and_attach_project(st.session_state, new_db.strip(), new_id.strip(), new_title.strip(),
                    owner_id=new_owner.strip(), goal=new_goal.strip(), first_task=new_task.strip())
            except ProjectFileError as exc:
                st.error(FILE_PROBLEMS.get(str(exc), "Nu pot crea proiectul."))
            else:
                st.rerun()
    context = st.session_state.get("project_context")
    if context is not None:
        try:
            card = context.project_card()
        except ProjectContextError as exc:
            st.error(CONTEXT_PROBLEMS.get(str(exc), "Proiectul nu este disponibil."))
        else:
            st.success("Proiect conectat: " + card["title"])
            if card.get("blocked_memories"):
                st.warning(CONTEXT_PROBLEMS["context_state_contaminated"])
            with st.expander("Starea proiectului"):
                goal, task = card["active_goal"], card["next_task"]
                st.write("Obiectiv: " + (goal["text"] if goal else "Niciun obiectiv activ"))
                st.write("Următorul pas: " + (task["text"] if task else "Nicio sarcină în așteptare"))
                labels = {"confirmed": "Confirmat cu sursă", "hypothesis": "Ipoteză", "unknown": "Necunoscut"}
                for key, memory in card["memories"].items():
                    st.text(f"{labels[memory['status']]} · {key}\n{memory['text']}")
                st.caption("Starea este citită din nou la fiecare mesaj. Conversația nu o modifică automat.")
            with st.expander("Memorie și dovezi"):
                st.caption("Doar butoanele de mai jos salvează sau revocă. Modificările pornesc o conversație nouă, fără istoricul stării vechi.")
                try:
                    records = memory_history(st.session_state)
                except ProjectFileError as exc:
                    st.error(FILE_PROBLEMS.get(str(exc), "Nu pot verifica memoria."))
                else:
                    for key, memory in records.items():
                        st.text(f"{key} · revizia {memory['revision']} · {memory['status']} · {memory['lifecycle']}")
                    plain_keys = [key for key, record in records.items() if "card" not in record and key.split(":", 1)[0].strip().casefold() not in {"skill", "procedure", "procedural"}]
                    selected_memory = st.selectbox("Memoria de editat", [None, *plain_keys],
                        format_func=lambda key: "Memorie nouă" if key is None else key)
                    current_memory = records.get(selected_memory) if selected_memory is not None else None
                    editor_binding = (str(context.db), context.project_id, selected_memory)
                    editor = st.session_state.get("memory_editor")
                    if editor is None or editor["binding"] != editor_binding:
                        editor = {"binding": editor_binding, "record": current_memory}
                        st.session_state.memory_editor = editor
                    previous = editor["record"]
                    stale_memory = previous is not None and (current_memory is None or current_memory["revision"] != previous["revision"])
                    if stale_memory:
                        st.warning("Memoria s-a schimbat de când ai început editarea. Reîncarcă înainte de salvare.")
                    if selected_memory is not None and st.button("Reîncarcă memoria selectată"):
                        st.session_state.pop("memory_editor", None)
                        st.rerun()
                    with st.form("save_project_memory"):
                        memory_key = st.text_input("Numele memoriei", value=selected_memory or "", disabled=previous is not None)
                        memory_text = st.text_area("Textul memoriei", value=previous["text"] if previous else "")
                        statuses = {"Ipoteză": "hypothesis", "Necunoscut": "unknown", "Confirmat cu dovadă": "confirmed"}
                        default_status = next((i for i, value in enumerate(statuses.values()) if previous and value == previous["status"]), 0)
                        memory_status = st.selectbox("Starea memoriei", list(statuses), index=default_status)
                        keep_sources = st.checkbox("Păstrează dovezile existente", value=previous is not None)
                        if previous:
                            st.caption(f"Revizia așteptată: {previous['revision']} · Dovezi existente: {len(previous['sources'])}")
                        source_uri = st.text_input("Adresa sursei noi (URI)")
                        source_text = st.text_area("Textul dovezii noi")
                        save_record = st.form_submit_button("Salvează memorie", disabled=stale_memory)
                    if save_record:
                        try:
                            save_memory(st.session_state, memory_key.strip(), memory_text.strip(),
                                status=statuses[memory_status], source_uri=source_uri.strip(), source_text=source_text,
                                expected_revision=previous["revision"] if previous else None, keep_existing_sources=keep_sources)
                        except ProjectFileError as exc:
                            st.error(FILE_PROBLEMS.get(str(exc), "Nu pot salva memoria."))
                        else:
                            st.rerun()
                    revocable = [key for key, memory in records.items() if memory["lifecycle"] != "revoked"]
                    if revocable:
                        revoke_key = st.selectbox("Memoria de revocat", revocable)
                        revoke_binding = (str(context.db), context.project_id, revoke_key)
                        revoke_editor = st.session_state.get("memory_revoke_editor")
                        if revoke_editor is None or revoke_editor["binding"] != revoke_binding:
                            revoke_editor = {"binding": revoke_binding, "revision": records[revoke_key]["revision"]}
                            st.session_state.memory_revoke_editor = revoke_editor
                        stale_revoke = records[revoke_key]["revision"] != revoke_editor["revision"]
                        if stale_revoke:
                            st.warning("Memoria de revocat s-a schimbat. Reîncarcă revizia înainte de revocare.")
                        if st.button("Reîncarcă revizia pentru revocare"):
                            st.session_state.pop("memory_revoke_editor", None)
                            st.rerun()
                        with st.form("revoke_project_memory"):
                            st.caption(f"Revizia de revocat: {revoke_editor['revision']}")
                            reason = st.text_input("Motivul revocării")
                            revoke_record = st.form_submit_button("Revocă memoria", disabled=stale_revoke)
                        if revoke_record:
                            try:
                                revoke_saved_memory(st.session_state, revoke_key, revoke_editor["revision"], reason.strip())
                            except ProjectFileError as exc:
                                st.error(FILE_PROBLEMS.get(str(exc), "Nu pot revoca memoria."))
                            else:
                                st.rerun()
        if st.button("Deconectează proiectul", use_container_width=True):
            detach_project(st.session_state)
            st.rerun()
    with st.expander("Copii de siguranță"):
        backup_folder = st.text_input("Folder pentru copii", value="backups")
        st.caption("Copiile conțin textul proiectului. Verificarea locală folosește un fișier separat; păstrează ambele fișiere.")
        if st.button("Creează copie", disabled=context is None):
            try:
                copied = create_backup(context.db, backup_folder.strip())
            except ProjectFileError as exc:
                st.error(FILE_PROBLEMS.get(str(exc), "Nu pot crea copia."))
            else:
                st.success("Copie verificată: " + copied.name)
        try:
            copies = list_backups(backup_folder.strip())
        except ProjectFileError as exc:
            st.error(FILE_PROBLEMS.get(str(exc), "Nu pot citi copiile."))
            copies = []
        if copies:
            with st.form("restore_project"):
                selected_copy = st.selectbox("Copia de restaurat", [path.name for path in copies])
                restore_target = st.text_input("Fișier nou pentru restaurare", value="data/proiect-restaurat.db")
                restore_id = st.text_input("Identificator pentru conectarea copiei", value=context.project_id if context else "demo")
                restore_project = st.form_submit_button("Restaurează copia")
            if restore_project:
                try:
                    restore_and_attach_project(st.session_state, Path(backup_folder.strip()) / selected_copy,
                        restore_target.strip(), restore_id.strip(), backup_dir=backup_folder.strip())
                except ProjectFileError as exc:
                    st.error(FILE_PROBLEMS.get(str(exc), "Nu pot restaura copia."))
                else:
                    st.rerun()
        else:
            st.caption("Nu există copii verificate în acest folder.")
    try:
        available = installed_models()
    except OllamaError:
        st.warning("Nu pot verifica Ollama la 127.0.0.1:11434. Verifică aplicația locală.")
    else:
        for model in ("llama3", "mistral"):
            if model in available:
                st.success(f"Ollama gata: {model}")
            else:
                st.warning(f"Pentru rutarea automată instalează: ollama pull {model}")
    if model_ready(model_directory(ROOT)):
        st.success("Sherpa gata pentru microfon")
    else:
        st.info("Pentru microfon: Instaleaza-EAON.cmd --voice --download-voice-model")
    if st.button("Șterge conversația", use_container_width=True):
        reset_conversation(st.session_state)
        st.rerun()
    stats = st.session_state.orchestrator.get_stats()
    col_a, col_b = st.columns(2)
    col_a.metric("Cereri", stats["request_count"])
    col_b.metric("Erori", stats["error_count"])
    st.caption("Jurnal local: data/telemetry.jsonl (doar metadate). Ștergerea conversației nu șterge jurnalul.")

for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            route = message.get("route")
            if route:
                st.caption(f"{route['intent']} → {route['model']} · {route['latency_ms']} ms")
            speak_button(message["content"], index, browser_language)

st.markdown('<div class="eaon-card"><b>🎙️ Microfon</b><br>Apasă, vorbește, apoi oprește înregistrarea. Verifică transcrierea înainte de trimitere.</div>', unsafe_allow_html=True)
recorded = st.audio_input("Înregistrează mesajul", sample_rate=16_000,
                          key=f"microphone-{st.session_state.get('microphone_version', 0)}")
if recorded is not None:
    recording = recorded.getvalue()
    recording_key = (hashlib.sha256(recording).hexdigest(), language)
    if recording_key != st.session_state.get("last_recording"):
        started = time.perf_counter()
        st.session_state.draft = ""
        st.session_state.draft_stt_ms = None
        try:
            st.session_state.draft = transcribe(recording, recognizer_for(language))
            st.session_state.draft_stt_ms = (time.perf_counter() - started) * 1000
        except (VoiceUIError, ImportError, RuntimeError) as exc:
            st.session_state.draft_stt_ms = None
            st.error(f"Transcriere indisponibilă: {exc}")
        st.session_state.last_recording = recording_key

if st.session_state.draft:
    with st.form("voice_draft", clear_on_submit=False):
        reviewed = st.text_area("Corectează transcrierea dacă e nevoie", value=st.session_state.draft)
        submitted = st.form_submit_button("Trimite mesajul vocal", type="primary")
    if submitted:
        send_message(reviewed, "voice")

typed = st.chat_input("Scrie un mesaj pentru EAON...")
if typed:
    send_message(typed, "text")
