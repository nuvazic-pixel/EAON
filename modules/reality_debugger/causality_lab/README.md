# EAON Reality Debugger — Causality Lab

Experimentul 4: doua semnale par conectate cauzal, dar sunt generate de o cauza
comuna ascunsa, observata cu intarzieri si zgomot diferite. Modul Python independent,
offline, fara integrare automata in runtime-ul EAON si fara acces la memoria lui.

## Instalare si rulare

Din radacina repository-ului, Python 3.11+ (PowerShell):

```powershell
py -3.12 -m venv .venv-causality
.\.venv-causality\Scripts\python.exe -m pip install -e './modules/reality_debugger/causality_lab[test,plots]'
.\.venv-causality\Scripts\eaon-causality.exe --seed 42 --samples 2000 --delay-x 1 --delay-y 4 --noise 0.4 --max-lag 8 --plots --output runs/causality-exp4
.\.venv-causality\Scripts\python.exe -m pytest modules/reality_debugger/causality_lab/tests -q --basetemp .pytest-causality
```

Pe Linux/macOS: `python3 -m venv .venv-causality`, apoi folositi executabilele
din `.venv-causality/bin/`. Alternativa CLI: `python -m eaon_causality_lab`.
`--help` listeaza toti parametrii, inclusiv `--ar`, `--alpha`, `--intervention-value`,
`--control-beta`, `--control-delay`. Pentru instalarea fara grafice, folositi `[test]`
si omiteti `--plots`. Modulul nu importa Matplotlib pana la solicitarea graficelor.
Folderul de iesire este relativ la directorul curent; fisierele cu acelasi nume
sunt inlocuite la rerulare. Folositi foldere distincte pentru experimente arhivate.

## Modelul structural

```text
H[t] = ar * H[t-1] + u[t]
X[t] = H[t-delay_x] + ex[t]
Y[t] = H[t-delay_y] + beta * X[t-control_delay] + ey[t]
```

`u ~ N(0,1)`, `ex,ey ~ N(0,noise^2)`, independente. `H` este initializat din
distributia stationara, iar istoricul suplimentar elimina marginile afectate de
intarzieri. `abs(ar)<1`; zgomotul trebuie sa fie strict pozitiv. `beta=0` in
experimentul principal. Controlul pozitiv foloseste `control_beta` (implicit 0.8).
H este disponibil doar simulatorului si graficului de diagnostic, niciodata
analizei cross-correlation/Granger. Nu se folosesc date reale.

Corelatia este Pearson pe suprapuneri, cu conventia explicita
`corr(X[t],Y[t+lag])`: lag pozitiv inseamna X inaintea lui Y. Lagul asteptat
pentru modelul principal este `delay_y-delay_x`; daca nu intra in fereastra
analizata, varful gasit poate fi diferit. Nu se foloseste deplasare circulara.

Granger testeaza ambele directii, fiecare ordin 1..max_lag, cu testul SSR F din
statsmodels. Coloanele sunt `[tinta, sursa]`. Raportul pastreaza toate rezultatele,
p brut si p ajustat Bonferroni pentru familia de `2*max_lag` teste. Seriile
degenerate primesc status `unavailable`, nu un verdict negativ.

## Interventii si interpretare

- `do(X=k)` inlocuieste ecuatia lui X pe intregul istoric. In modelul principal,
  Y ramane identic, desi X poate imbunatati predictia lui Y.
- `do(H=k)` inlocuieste ecuatia lui H; ambele semnale se schimba. Este o interventie
  oracle, posibila fiindca noi construim simulatorul, nu o procedura observationala.
- In controlul cu legatura reala X -> Y, `do(X=k)` schimba Y conform coeficientului
  si intarzierii specificate. Acesta verifica sensibilitatea demonstratiei.

Fiecare pereche refoloseste exact aceleasi realizari exogene, fara a reseta
generatorul aleator global. Efectele sunt diferente contrafactuale pereche, nu
estimatori cu intervale de incredere din studii independente. Interventiile sunt
sustinute pe tot istoricul, nu impulsuri aplicate la mijlocul unei serii.

Predictibilitatea Granger nu identifica o legatura structurala. Stationaritatea
este garantata de model, dar confuzia ascunsa si ordinul finit pot produce
reziduuri autocorelate si p-valori prost calibrate. Nu efectuam diagnostic complet
al reziduurilor, selectie automata de ordin sau inferenta pe date externe.
Bonferroni nu corecteaza cautarea repetata a unui seed favorabil sau a parametrilor.
Un rezultat nesemnificativ nu dovedeste absenta cauzalitatii. Varful corelatiei
este descriptiv, fara interval de incredere. Concluzia interventiei este valabila
pentru ecuatiile simulate, nu pentru cauze din lumea reala.

Referinte de implementare: [statsmodels Granger](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.grangercausalitytests.html)
si [ipoteza de stationaritate VAR](https://www.statsmodels.org/stable/vector_ar.html).

## Arhitectura si livrabile

- `simulation.py`: configuratie validata, generator PCG64, ecuatii si interventii.
- `analysis.py`: corelatia pe laguri si testele predictive bidirectionale.
- `experiment.py`: coordonare, efecte pereche, provenienta si limite explicite.
- `report.py`: `report.md`, `report.json`, optional `diagnostics.png` fara GUI.
- `cli.py`: interfata command-line; `tests/`: verificari numerice si end-to-end.

JSON are `schema_version`, configuratia completa, versiunile bibliotecilor,
modelul cunoscut, toate lagurile, efectele interventiilor si precautiile.
Nu include timestamp sau cai absolute: aceleasi argumente si acelasi mediu produc
rapoarte identice. Intre versiuni NumPy/BLAS/platforme pot aparea diferente numerice;
pastrati `pip freeze` al mediului pentru reproducere stricta. PNG nu are garantie
de identitate binara intre versiuni. Rapoartele generate raman in `runs/`, ignorat
de Git; codul si testele sunt versionate.
