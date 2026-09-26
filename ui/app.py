"""Start with: python -m streamlit run ui/app.py --server.address 127.0.0.1"""

from __future__ import annotations

import hashlib
import html
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.voice_backend import (  # noqa: E402
    VoiceUIError, chat_reply, create_recognizer, installed_models,
    model_directory, model_ready, transcribe,
)

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


def send_message(prompt: str, model: str) -> None:
    try:
        answer = chat_reply(prompt, st.session_state.messages, model)
    except VoiceUIError as exc:
        st.error(str(exc))
        return
    st.session_state.messages += [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": answer},
    ]
    st.session_state.draft = ""
    st.rerun()


st.markdown('<span class="eaon-kicker">EDGE AI ORCHESTRATION NODE</span>', unsafe_allow_html=True)
st.title("Vorbește cu EAON")
st.caption("Conversație locală • Microfon la cerere • Răspuns vocal la apăsarea butonului")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "draft" not in st.session_state:
    st.session_state.draft = ""

with st.sidebar:
    st.header("Configurare")
    selected_model = st.selectbox("Model Ollama", ("llama3", "mistral"))
    language_name = st.selectbox("Limba vorbită", ("Română", "Deutsch", "English", "Automat"))
    language = {"Română": "ro", "Deutsch": "de", "English": "en", "Automat": ""}[language_name]
    browser_language = language or "ro"
    try:
        available = installed_models()
    except VoiceUIError:
        st.warning("Ollama este oprit. Pornește aplicația Ollama.")
    else:
        if selected_model in available:
            st.success(f"Ollama gata: {selected_model}")
        else:
            st.warning(f"Instalează modelul: ollama pull {selected_model}")
    if model_ready(model_directory(ROOT)):
        st.success("Sherpa gata pentru microfon")
    else:
        st.info("Pentru microfon: py -3.12 scripts\\setup_voice_model.py")
    if st.button("Șterge conversația", use_container_width=True):
        st.session_state.messages = []
        st.session_state.draft = ""
        st.session_state.last_recording = None
        st.session_state.microphone_version = st.session_state.get("microphone_version", 0) + 1
        st.rerun()
    st.caption("Istoricul rămâne în această sesiune. Mesajele merg doar la Ollama pe 127.0.0.1.")

for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            speak_button(message["content"], index, browser_language)

st.markdown('<div class="eaon-card"><b>🎙️ Microfon</b><br>Apasă, vorbește, apoi oprește înregistrarea. Verifică transcrierea înainte de trimitere.</div>', unsafe_allow_html=True)
recorded = st.audio_input("Înregistrează mesajul", sample_rate=16_000,
                          key=f"microphone-{st.session_state.get('microphone_version', 0)}")
if recorded is not None:
    recording = recorded.getvalue()
    recording_key = (hashlib.sha256(recording).hexdigest(), language)
    if recording_key != st.session_state.get("last_recording"):
        try:
            st.session_state.draft = transcribe(recording, recognizer_for(language))
        except (VoiceUIError, ImportError, RuntimeError) as exc:
            st.error(f"Transcriere indisponibilă: {exc}")
        st.session_state.last_recording = recording_key

if st.session_state.draft:
    with st.form("voice_draft", clear_on_submit=False):
        reviewed = st.text_area("Corectează transcrierea dacă e nevoie", value=st.session_state.draft)
        submitted = st.form_submit_button("Trimite mesajul vocal", type="primary")
    if submitted:
        send_message(reviewed, selected_model)

typed = st.chat_input("Scrie un mesaj pentru EAON...")
if typed:
    send_message(typed, selected_model)
