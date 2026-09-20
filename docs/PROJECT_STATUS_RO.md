# EAON — ce avem concret

Actualizat la **20 septembrie 2026**. Acest repo adună codul și deciziile recuperate.
Înainte de consolidare, `main` avea baseline-ul INTEL din aprilie; Knowledge Gap și
ingestia erau pe un branch separat, iar celelalte prototipuri se aflau în arhive.

| Componentă | Ce face acum |
|---|---|
| Genesis SELF v0.2 | Caută memorie, marchează presupuneri/riscuri/teste, propune un pas și salvează jurnalul. Council determinist. |
| Local-first v0.1 | Documente locale → dovezi în SQLite → răspuns extractiv sau Ollama local. |
| INTEL 2.0 | Routing simplu, moduri de risc, Ollama și adaptoare de informații despre IP-uri. |
| Knowledge Gap + ingestion | Surse, afirmații, dovezi, detector de goluri structurale, OpenAlex și SQLite. |
| Skills v0.1 | Cinci skill-uri cu selecția contextului relevant. |
| Cognitive Twin Genesis | API, jurnal, graf, ipoteze, feedback și snapshot-uri în PostgreSQL. |
| C3 vocal | Infrastructura de benchmark și State Journal. Rezultatele mock sunt simulate. |
| MetaBench | Teste reproductibile pentru contradicții, informații insuficiente, adaptare și repararea erorilor. |
| BHIDT v0.4 | Recalculare și adaptor EAON pentru MATCH/DRIFT/DIVERGENCE/UNVERIFIABLE. |
| EAON-Red | Sursa experimentului de securitate într-un benchmark izolat; SDK-ul original lipsește. |

**40 de teste existente au trecut.** [Raportul](VERIFICATION.md) spune exact ce am
rulat și ce nu a putut fi validat pe hardware/servicii reale.

Continuity kernel, MCP, Council cu mai multe modele, Azure, CAUC shadow, interlock-ul
vocal complet, senzorii și consola centrală sunt documentate cu starea lor reală.

SELF, memoria SQLite și serviciul Twin au jurnale și structuri diferite. Le putem
porni separat; memoria comună și traseul unic de execuție sunt pași de integrare.

**Recomandarea: Genesis SELF → continuity kernel → adaptorul local-first.**
Prima probă: o sesiune salvează o decizie, alta recuperează sursa și incertitudinea;
lipsa memoriei produce „necunoscut”, iar jurnalul invalid blochează utilizarea lui.

```bash
python scripts/run_module.py genesis think "Vreau sa verific o presupunere despre EAON."
python scripts/run_module.py genesis recall "EAON"
python scripts/run_module.py genesis verify
```

[Istoric](HISTORY.md) · [Arhitectură](ARCHITECTURE.md) · [Pași următori](ROADMAP.md)
