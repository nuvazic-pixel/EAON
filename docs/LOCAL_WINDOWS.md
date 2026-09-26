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
