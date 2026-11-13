# Instalare locală pe Windows

Pachetul complet se extrage într-un folder propriu, de exemplu
`Documents\EAON-local`. Păstrează copiile vechi în folderele lor. Pachetul nu
include mediul Python, tokenuri, baze personale sau modele.

## Prima pornire

1. Este necesar Python **3.12** cu Python Launcher (`py`). Dacă lipsește,
   instalează-l din [sursa oficială Python](https://www.python.org/downloads/windows/).
   Python implicit 3.14 nu este mediul testat pentru acest pachet.
2. Deschide **Instaleaza-EAON.cmd**. Creează `.venv` în folderul pachetului și
   instalează versiunile declarate în `requirements-desktop.txt`. Instalarea
   dependențelor are nevoie de internet. Nu instalează Python global și nu
   modifică alte medii Python.
3. Pornește Ollama local. Conversația folosește `llama3` și `mistral`; instalatorul
   nu le descarcă și nu pornește servicii. Dacă nu sunt deja disponibile,
   comenzile explicite sunt `ollama pull llama3` și `ollama pull mistral`.
4. Deschide **Porneste-EAON.cmd**. Interfața este disponibilă la
   `http://127.0.0.1:8501`. Fereastra de pornire păstrează procesul local; închiderea
   ei oprește aplicația. Dacă portul este ocupat: `Porneste-EAON.cmd --port 8502`.

Profilul implicit oferă conversație text și proiecte. Instalatorul păstrează
orice `.env` existent. Dacă lipsește, creează o configurație locală cu
INTEL/Redis/Slack/Jira dezactivate. Launcherul impune aceleași valori pentru
procesul UI, chiar dacă fișierul `.env` existent conține alte valori. Nu afișează
tokenuri și nu mută, șterge sau înlocuiește baze existente.

Un `.venv` existent este reutilizat numai dacă este un mediu Python 3.12 valid
al acestui folder. Un mediu incompatibil sau incomplet este refuzat și păstrat;
extrage pachetul într-un folder nou pentru o instalare curată. Instalatorul nu
șterge automat directoare.

## Verificare fără schimbări

```bat
Instaleaza-EAON.cmd --check-only
Instaleaza-EAON.cmd --no-network
Porneste-EAON.cmd --check-only
.venv\Scripts\python.exe -I scripts\doctor_local.py
```

`doctor_local.py` produce JSON cu versiunea Python, dependențele și prezența
modelelor cerute. Citește numai `/api/tags` de la Ollama pe loopback; nu trimite
prompturi, nu descarcă modele și nu încarcă `.env`. Proxy-urile și redirectările
sunt dezactivate. Raportul nu afișează celelalte modele instalate sau configurația
privată.

`--no-network` nu contactează nici Ollama și nu creează/configurează nimic.
Verificarea offline poate confirma `installation_ready`; `inference_ready`
rămâne `null`, iar `ready` nu pretinde că un model a fost verificat. Codul de
ieșire offline validează numai instalarea cerută. Launcherul poate deschide UI
fără Ollama pornit; răspunsurile modelului cer ca acesta să fie disponibil.

## Microfon, opțional

Vocea folosește profilul existent Sherpa; nu schimbă stackul din brief-uri:

```bat
Instaleaza-EAON.cmd --voice
Instaleaza-EAON.cmd --voice --download-voice-model
.venv\Scripts\python.exe -I scripts\doctor_local.py --voice
```

`--voice` instalează numai dependențele vocale declarate. Descărcarea modelului
Sherpa tiny se cere separat prin `--download-voice-model`; reutilizează fișierele
complete deja prezente și refuză un director incomplet. Nu descarcă automat
modele Ollama sau runtime-uri noi. Prezența fișierelor nu este o măsurătoare a
calității ASR.

Pentru oprire, folosește `Ctrl+C` în fereastra launcherului. Proiectele, sursele
și jurnalele rămân în folderul local. Pentru depanare poți trimite raportul
doctorului; acesta nu conține tokenurile sau textele proiectelor.
