# EAON C/3 — benchmark vocal + State Journal

Acest modul implementează împreună A/1 și B/2: un benchmark offline pentru
română, germană și engleză și un jurnal tipizat pentru traseul
`wake → VAD → STT → router → LLM → TTS`.

## Ce produce

- `report.json`: WER pe limbă, false-accept/false-reject pentru wake word și
  latențe p50/p95 pe etapă;
- `state-journal.jsonl`: evenimente `Transition` și `Observation`, legate prin
  hash-uri SHA-256;
- niciun audio brut nu este copiat în jurnal; transcriptul complet rămâne doar
  în raportul de benchmark și poate fi șters după agregare.

## Pornire rapidă pe Windows

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python -m unittest discover -s tests -v
python -m eaon_c3 run --manifest examples/manifest.csv --output runs/smoke --adapter mock
python -m eaon_c3 verify runs/smoke/state-journal.jsonl
```

Modul `mock` verifică infrastructura, nu performanța. Fișierele WAV din
manifest nu sunt necesare pentru acest smoke test.

## Legarea Sherpa-ONNX

Adaptorul real trebuie să primească un WAV și să scrie pe stdout un singur JSON:

```json
{"wake_detected":true,"transcript":"EAON aprinde lumina","model":"sherpa-onnx-1.13.6","latencies_ms":{"wake":8.1,"vad":4.3,"stt":91.2,"router":0.7,"llm":183.0,"tts":62.4}}
```

Rulare (înlocuiește executabilul cu wrapperul local Sherpa-ONNX):

```powershell
python -m eaon_c3 run `
  --manifest corpus/manifest.csv `
  --output runs/2026-08-24 `
  --adapter command `
  --command '.\sherpa_adapter.exe --audio "{audio}" --language {language}'
```

Nu se folosește shell pentru execuție. Sunt disponibile tokenurile `{audio}`,
`{language}`, `{reference}` și `{wake_expected}`. Referința este destinată
scorării, nu trebuie transmisă motorului ASR în adaptorul de producție.

## Protocol recomandat C/3

Pentru fiecare limbă: minimum 50 comenzi pozitive și 100 mostre negative,
înregistrate la 0,5 m și 3 m, în liniște și cu zgomot casnic. Includeți vorbitori
diferiți și negative cu pronunție apropiată de „EAON”. Păstrați același corpus
pentru fiecare build și raportați separat:

- WER pe `ro`, `de`, `en`;
- false accept/hour pe fluxul negativ continuu și false reject rate;
- p50/p95 pentru fiecare etapă și latența end-to-end;
- versiunea exactă a modelelor, buildului, driverului și hardware-ului.

Praguri inițiale de acceptare (de calibrat după primul corpus real): WER ≤ 12%
în liniște, false reject ≤ 5%, false accept ≤ 0,2/oră și p95 wake-to-first-audio
≤ 1.2 s. Nu comparați builduri dacă modelele sau corpusul diferă.

## Limite curente

Repo-ul nu include modele, audio sau binare Sherpa-ONNX. Latențele din modul
`mock` sunt sintetice. Lanțul hash detectează modificarea, dar nu oferă singur
autenticitate externă; ancorați periodic ultimul hash într-un storage separat
sau semnați checkpointurile pentru protecție împotriva rescrierii complete.
