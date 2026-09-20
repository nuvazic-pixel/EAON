# Personal Cognitive Twin — Genesis v0.1

Primul nucleu rulabil al unui **Digital Twin cognitiv personal**.

> **The Twin models the person; it does not define the person.**

Genesis v0.1 nu încearcă să fie un chatbot complet. Construiește fundația corectă: evenimente imuabile, provenance, graph cognitiv, ipoteze cu confidence, user feedback și Temporal Self.

## Ce este deja implementat

- PostgreSQL + pgvector într-o singură bază autoritativă
- Event Journal append-only cu SHA-256 hash chain
- politică strict personală: `work/professional/employment` sunt excluse implicit
- Evidence / provenance
- Cognitive Graph: nodes + edges
- Hypotheses cu confidence și alternative interpretation
- Confirm / reject / uncertain pentru ipotezele Twin-ului
- Self Snapshots + timeline
- API FastAPI + Swagger UI
- două exemple sintetice pentru verificarea jurnalului, fără evenimente personale
- teste de bază

## Cerințe pe Windows

1. Docker Desktop instalat și pornit.
2. PowerShell.
3. Minimum câțiva GB liberi pentru imaginile Docker și baza locală.

Python local nu este obligatoriu; rulează în container.

## Start — cea mai simplă variantă

În PowerShell, intră în folder și rulează:

```powershell
./start.ps1
```

La prima pornire scriptul creează `.env` din `.env.example`.

Apoi deschide:

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`

## Seed Genesis

După ce serviciile sunt UP:

```powershell
docker compose exec api python scripts/seed_genesis.py
```

Verifică jurnalul:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/journal/verify
```

Ar trebui să vezi `valid: true`.

## Exemplu: adaugă o idee personală

```powershell
$body = @{
    event_type = "idea"
    domain = "cognitive"
    source = "manual"
    content = "Vreau ca Twin-ul să poată găsi idei vechi care au redevenit relevante."
    metadata = @{
        importance = 0.9
        tags = @("memory", "resurfacing")
    }
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri http://localhost:8000/api/v1/events `
    -ContentType "application/json" `
    -Body $body
```

## Protecția față de datele de muncă

Acest request este respins:

```json
{
  "event_type": "work_log",
  "domain": "work",
  "content": "..."
}
```

Dacă o experiență de muncă a scos la iveală ceva relevant cognitiv, **nu introducem contextul profesional brut**. Îl reformulăm, de exemplu:

```json
{
  "event_type": "observation",
  "domain": "cognitive",
  "content": "În sisteme ambigue caut spontan ownership și responsabilități explicite."
}
```

## Endpoint-uri Genesis

| Endpoint | Rol |
|---|---|
| `GET /api/v1/health` | stare sistem |
| `POST /api/v1/events` | adaugă eveniment imuabil |
| `GET /api/v1/events` | citește jurnalul |
| `GET /api/v1/journal/verify` | verifică hash chain |
| `POST /api/v1/evidence` | leagă evidence de un event |
| `POST /api/v1/graph/nodes` | adaugă concept/belief/idea/etc. |
| `POST /api/v1/graph/edges` | adaugă relație între noduri |
| `POST /api/v1/hypotheses` | ipoteză cognitivă |
| `POST /api/v1/hypotheses/{id}/feedback` | confirm/reject/uncertain |
| `POST /api/v1/self/snapshots` | snapshot Temporal Self |
| `GET /api/v1/self/timeline` | evoluția snapshot-urilor |

## Oprire

```powershell
./stop.ps1
```

Datele PostgreSQL rămân în Docker volume.

Pentru a șterge **și baza de date** (atenție, distructiv):

```powershell
docker compose down -v
```

## Backup Genesis

Pentru început:

```powershell
docker compose exec db pg_dump -U twin cognitive_twin > cognitive_twin_backup.sql
```

Mai târziu adăugăm backup criptat automat și export JSONL/GraphML.

## Structura proiectului

```text
cognitive-twin-genesis-v0.1/
├─ app/
│  ├─ api/routes.py
│  ├─ core/config.py
│  ├─ db/
│  ├─ models/entities.py
│  ├─ schemas/entities.py
│  ├─ services/journal.py
│  ├─ services/policy.py
│  └─ main.py
├─ docs/ARCHITECTURE.md
├─ scripts/seed_genesis.py
├─ tests/
├─ docker-compose.yml
├─ Dockerfile
├─ requirements.txt
├─ start.ps1
├─ stop.ps1
└─ status.ps1
```

## Prima definiție de succes

Genesis este sănătos când poate păstra evenimentele în ordine, demonstra că nu au fost modificate, lega dovezi de concepte/ipoteze și reconstrui primele puncte din Timeline.

Următorul milestone este **v0.2 SELF**: Belief History + Question History + Interests + Contradiction Engine + primele snapshot-uri cognitive generate din evidence.
