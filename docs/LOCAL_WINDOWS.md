# EAON local pe Windows

Din PowerShell, în folderul repo-ului tău:

```powershell
git status --short
git switch main
git pull --ff-only origin main
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
.\.venv\Scripts\python.exe scripts\local_run.py
```

Dacă nu ai clonat repo-ul, începe cu
`git clone https://github.com/nuvazic-pixel/EAON.git` și `cd EAON`.
Dacă `git status --short` arată modificări, salvează-le înainte de `git switch`.
Python 3.11 este suficient pentru verificarea locală; pentru `--all-tests`
folosește Python 3.12 și instalează și `requirements-verify.txt`.

Verificarea locală rulează testele gateway/interlock, `main.py --stats` și
benchmarkul vocal **mock** cu șase exemple. Raportul este salvat într-un folder
nou sub `benchmarks/voice/runs/` la fiecare rulare. Nu are nevoie de Ollama.

Pentru toate suitele recuperate:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-verify.txt
.\.venv\Scripts\python.exe scripts\local_run.py --all-tests
```

Pentru a trimite un prompt către Ollama local, pornește Ollama și verifică modelul:

```powershell
ollama list
ollama pull llama3
.\.venv\Scripts\python.exe scripts\local_run.py --prompt "Salut, EAON. Răspunde în română."
```

`ollama pull llama3` este necesar doar dacă modelul lipsește. Pentru
`--mode safe` sau `--mode lockdown`, instalează `mistral`. Pentru consola
interactivă folosește `scripts\local_run.py --interactive`.

Acesta este CLI-ul INTEL existent plus verificarea simulată. Componentele din
repo rămân module separate; Sherpa live, microfonul, izolarea de rețea a testului
vocal și acțiunile fizice nu sunt integrate în acest launcher.

## Interfață cu text și microfon local

Folosește folderul **EAON** conectat la `https://github.com/nuvazic-pixel/EAON`.
Dacă ai `EAON` și `EAON2`, verifică `git remote -v` și `git status --short`
în fiecare înainte să alegi folderul; nu suprascrie modificările locale. Dacă
nu ai un clone curat, creează un folder nou cu `git clone`.

În PowerShell, din folderul repo-ului:

```powershell
git switch main
git pull --ff-only origin main
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
.\.venv\Scripts\python.exe scripts\setup_voice_model.py
ollama pull llama3
.\.venv\Scripts\python.exe scripts\voice_ui.py
```

Deschide `http://127.0.0.1:8501` în browser și permite accesul la microfon
pentru acest site local. Înregistrează mesajul, oprește înregistrarea, verifică
transcrierea, apoi apasă **Trimite mesajul vocal**. Alternativ, tastează direct
în chat. Pentru a auzi răspunsul, apasă **Ascultă răspunsul**; calitatea și
disponibilitatea vocii depind de vocile instalate în browser/Windows. În
sidebar poți alege Mistral (după `ollama pull mistral`) sau limba de vorbire.

Instalarea Sherpa descarcă din release-ul oficial modelul multilingv Whisper
tiny într-un folder `models/` ignorat de Git. Fișierele pot fi mari; este
necesară o conexiune la internet **la instalare**. După instalare, transcrierea
rulează local pe CPU, chiar dacă ai RTX 4070. La prima pornire, modelul poate
avea nevoie de câteva secunde pentru încărcare; modelul tiny poate greși
cuvinte, așa că verifică transcrierea. Textul chatului este trimis doar către
Ollama pe `127.0.0.1:11434`; Streamlit ascultă pe `127.0.0.1:8501`.

Butonul de voce folosește funcția de citire a browserului; pentru folosire fără
internet, selectează o voce instalată local. Interfața nu ascultă permanent,
nu are cuvânt de activare și nu lansează comenzi sau acțiuni fizice. Istoricul
chatului este păstrat în sesiunea browserului, nu salvat intenționat pe disc.
Această interfață nu măsoară sau certifică izolarea completă a proceselor la
nivelul sistemului de operare.
