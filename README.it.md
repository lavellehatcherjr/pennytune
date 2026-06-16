<p align="center">
  <img src="https://raw.githubusercontent.com/lavellehatcherjr/pennytune/main/docs/assets/pennytune-logo.png" alt="PennyTune" width="400">
</p>

> Nota: questa è una traduzione fornita esclusivamente a scopo informativo. Il
> [README in inglese](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) è la versione ufficiale e autorevole.
> L'interfaccia, i comandi e l'output di PennyTune sono disponibili solo in
> inglese. In caso di qualsiasi discrepanza, prevale la versione inglese.

[English](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) | [日本語](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ja.md) | [Español](https://github.com/lavellehatcherjr/pennytune/blob/main/README.es.md) | [Français](https://github.com/lavellehatcherjr/pennytune/blob/main/README.fr.md) | [한국어](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ko.md) | [中文](https://github.com/lavellehatcherjr/pennytune/blob/main/README.zh.md) | [Deutsch](https://github.com/lavellehatcherjr/pennytune/blob/main/README.de.md) | [Português](https://github.com/lavellehatcherjr/pennytune/blob/main/README.pt.md) | Italiano

# PennyTune

**Elimina il rumore di fondo.**

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**PennyTune è uno strumento gratuito, open-source e senza chiavi API per la due diligence forense sulle micro-cap quotate negli Stati Uniti.**
Puntalo sui ticker che già detieni o che stai monitorando e fa emergere i
segnali di rischio e i campanelli d'allarme forensi nelle dichiarazioni SEC di
ciascuna società - punteggi sulla qualità contabile e sullo stato di difficoltà
finanziaria, rischio di diluizione e di operazioni societarie, attività degli
insider, eventi rilevanti 8-K, rischio di notifica di delisting e di sospensione
attiva delle negoziazioni, e contesto di regolamento sui fails-to-deliver -
**calcolati dalle dichiarazioni SEC pubbliche di ciascuna società**, così da
poter valutare tu stesso la società.

Funziona interamente su **dati pubblici, senza account e senza chiavi API**: SEC
EDGAR è l'unica fonte di dati (l'universo delle società quotate, tutte le
dichiarazioni e i feed sui fails-to-deliver / sulle sospensioni delle
negoziazioni). Non esiste **alcuna opzione bring-your-own-key, da nessuna parte**.

> PennyTune fa emergere **prove per la tua due diligence personale** - non ti
> dice se un titolo è "pulito" o "una mina vagante", non fornisce consigli di
> acquisto/vendita e non prevede gli esiti. Analizza **società registrate presso
> la SEC e quotate negli Stati Uniti** e **non recupera prezzi in tempo reale**:
> non effettua screening in base al prezzo corrente, non calcola indicatori
> tecnici e non valuta la negoziabilità (spread bid-ask/liquidità). Sei tu a
> fornire il/i ticker da classificare e a verificare personalmente il prezzo
> corrente e la negoziabilità presso un broker.

---

## ⚠️ Avvertenza - leggere attentamente

PennyTune è uno strumento di ricerca ed educativo, non un consiglio di
investimento. Non ti dice se acquistare, vendere o detenere un qualsiasi
titolo. Le micro-cap e le penny stock comportano un rischio estremo, inclusa
la possibile perdita totale del tuo capitale. L'avvertenza completa, che
costituisce la versione che fa fede, è disponibile in inglese nel
[README in inglese](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) e tramite il comando `pennytune disclaimer`.

---

## Che cos'è

Il segmento delle micro-cap statunitensi è pieno di società che sembrano a buon
mercato *per un motivo* - che bruciano cassa, si diluiscono, sono prossime al
delisting o sono strutturate per la manipolazione. La parte difficile della due
diligence è leggere le dichiarazioni per individuare queste mine vaganti.
PennyTune svolge per te questa lettura: puntalo su un ticker, o classifica un
insieme selezionato di ticker a tua scelta, ed estrae i segnali di rischio e i
campanelli d'allarme forensi dalle dichiarazioni SEC della società - **calcolati
dalle dichiarazioni SEC pubbliche della società**.

Fa emergere **prove, non verdetti.** Non ti dice se un titolo è pulito o una mina
vagante, non consiglia di acquistare o vendere e non prevede gli esiti - il
giudizio spetta a te.

- **Gratuito e senza chiavi API** - funziona interamente su dati pubblici, senza
  account e senza chiavi.
- **Registrata presso la SEC, quotata su una delle principali borse statunitensi (NYSE/NASDAQ/NYSE American), mai OTC** - per costruzione.
- **Basato su prove** - ogni segnale è calcolato dalle dichiarazioni SEC
  pubbliche della società e, per i campanelli d'allarme guidati dagli eventi,
  viene indicato lo specifico item 8-K.
- **Trasparente e regolabile** - un punteggio composito scomponibile con pesi
  modificabili dall'utente, preset di screening (`penny` predefinito / `micro` /
  `small-cap-value` / `broad` / `custom`) e profili di strategia selezionabili
  (`hold` predefinito / `trader` / `high-return` / `custom`).
- **Nessun prezzo in tempo reale** - non recupera il prezzo corrente né valuta la
  negoziabilità; verificali tu stesso presso un broker.
- **Solo ricerca, non consulenza sugli investimenti.**

## Cosa fa emergere

Per ciascuna società, PennyTune legge le dichiarazioni SEC e valuta i segnali
più rilevanti per una micro-cap - ognuno calcolato dalle dichiarazioni della
società:

- **Salute finanziaria e difficoltà** - punteggio di solvibilità Altman Z″ più
  una batteria forense (i modelli di manipolazione degli utili Beneish e di
  solidità Piotroski) sui bilanci depositati della società.
- **Diluizione e operazioni societarie** - offerte shelf e ATM ("at-the-market"),
  aumento del numero di azioni e velocità di diluizione, frazionamenti inversi
  seriali e segnalazioni di cambio del revisore / riformulazione di bilancio
  tratte dal registro degli 8-K.
- **Attività degli insider** - *acquisti* di insider sul mercato aperto (il
  segnale di convinzione), tenuti distinti dalle assegnazioni di routine e dalle
  ritenute fiscali, in modo che i premi non vengano mai interpretati come rialzisti
  - più l'overhang da vendite proposte nel Form 144 e l'attività di proprietà
  13D/13G.
- **Eventi rilevanti 8-K** - il flusso strutturato dei codici item (riformulazioni,
  cambi di revisore, dimissioni di dirigenti, carenze di quotazione e altre voci
  rilevanti), ponderato per gravità anziché per conteggio grezzo.
- **Rischio di notifica di delisting** - notifiche di carenza per il mantenimento
  della quotazione divulgate (8-K Item 3.01), riportate senza indovinare il
  conteggio dei giorni del price-clock che lo strumento non può calcolare.
- **Sospensioni attive delle negoziazioni** - una società sottoposta a una
  sospensione delle negoziazioni SEC *in corso* viene segnalata ed esclusa; le
  sospensioni storiche scadute sono mostrate come contesto, non a sfavore della
  società.
- **Fails-to-deliver** - contesto sullo stress di regolamento dai dati bimestrali
  della SEC sui fails-to-deliver (solo contesto - di per sé non è prova di
  manipolazione).
- **Classificazione settoriale** - il settore SIC di ciascuna società, in modo che
  i confronti di qualità e valutazione siano effettuati rispetto a società
  comparabili per settore e dimensione anziché a soglie assolute.

## Dati e attribuzione

PennyTune utilizza esclusivamente dati pubblici, senza chiavi, provenienti da
un'unica fonte: **SEC EDGAR** (l'universo - dal file delle società quotate
`company_tickers_exchange.json` della SEC - e tutte le dichiarazioni, i dati
fondamentali, i moduli sugli insider e i file sui fails-to-deliver / sulle
sospensioni delle negoziazioni). L'unica identità richiesta, ovunque, è la
stringa `User-Agent` di SEC EDGAR (il tuo nome + email) - un header di richiesta
che la politica di equo accesso della SEC richiede per identificare il
richiedente, non un account, un login o una chiave di PennyTune. È memorizzata
solo nella tua configurazione locale (oscurata in `config get`), inviata solo
nell'header della richiesta SEC e mai trasmessa all'autore o a terze parti. Va
bene qualsiasi email personale valida; la configurazione verifica il formato, non
il provider.

PennyTune è uno strumento di ricerca e **non** ripubblica dataset grezzi di terze
parti; la tua configurazione e qualsiasi risultato esportato rimangono in locale
(mai sottoposti a commit).

## Installazione

PennyTune è uno strumento da riga di comando pubblicato su PyPI. Installalo con
pip - l'impostazione predefinita semplice e universale:

```bash
pip install pennytune
```

Trattandosi di una CLI, un'**installazione isolata (consigliata per gli strumenti
da riga di comando)** lo mantiene fuori dai tuoi altri ambienti Python:

```bash
pipx install pennytune       # isolated install via pipx
uv tool install pennytune    # the same, via uv's tool installer
```

Richiede Python 3.11-3.14 (tutti testati in CI su Linux, macOS e Windows; 3.13 è
il target principale per il linting e il controllo dei tipi).

**Da sorgente (per lo sviluppo):**

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

## Utilizzo

La configurazione iniziale registra l'identità di SEC EDGAR (un header di
richiesta obbligatorio - non una chiave) e l'accettazione del rischio;
`scan`/`inspect` si rifiutano di funzionare finché entrambi non esistono:

```bash
pennytune init --identity "Your Name you@example.com" --i-understand-the-risks
```

Il flusso di lavoro principale è **`inspect <TICKER>`** - punta lo strumento su
una società che già detieni e ottieni la sua analisi forense completa calcolata
dalle dichiarazioni:

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

`scan` classifica un **insieme selezionato di ticker a tua scelta** - forniti
esplicitamente o letti dalla tua watchlist - in base ai loro segnali di rischio
nelle dichiarazioni SEC (nessun filtro sul prezzo - lo strumento non recupera
alcun prezzo). Al massimo 100 ticker per esecuzione; PennyTune non analizza mai
l'intero mercato. Poiché i sotto-punteggi di qualità positivi sono percentili
relativi al settore/dimensione (significativi solo su un'ampia sezione
trasversale), su un piccolo insieme selezionato la classifica è determinata
principalmente dai segnali di **rischio/penalità** (diluizione, difficoltà,
delisting, vendite degli insider) - fa emergere i nomi più rischiosi del tuo
insieme. Regola la ponderazione del rischio e la strategia con `--preset` /
`--profile`:

```bash
pennytune scan AAA BBB CCC                       # rank the tickers you name
pennytune scan                                   # rank your watchlist (top 10)
pennytune --profile high-return scan AAA BBB --preset broad  # preset + profile
pennytune scan AAA BBB --exclude-serial-splitter --require-insider-buying

# Export the full ranked set (CSV/Parquet/JSON/Markdown); pipe clean JSON:
pennytune scan AAA BBB --format parquet
pennytune --json scan AAA BBB | jq '.results[0]'

# Offline / no-network run (degraded; no live SEC fetch):
pennytune --offline scan AAA BBB
```

Tutti gli altri comandi:

```bash
pennytune --help              # all commands and global flags
pennytune --version           # app version + pinned dependency versions
pennytune disclaimer          # print the full legal disclaimer
pennytune watch add GROW NUKK # persistent watchlist (add | list | rm)
pennytune watch list          #   run-over-run score deltas + alerts
pennytune config get          # view all settings (EDGAR email redacted)
pennytune config set weights.valuation 1.5   # tune a scoring weight
pennytune config set profile custom          # switch to hand-tuned weights
pennytune sources             # data sources, free-tier limits, contacted domains
```

L'output si apre con un'intestazione di freschezza (preset/profilo attivo +
timestamp as-of per dominio), mostra un banner di avviso della watchlist quando
pertinente, classifica i primi N e termina con l'avvertenza breve. I file
esportati riportano l'intestazione dell'avvertenza su una riga, in modo che
l'avvertenza viaggi insieme ai dati.

## Sviluppo

```bash
python -m pytest tests/ -v    # run the test suite
ruff check .                  # lint
python -m mypy                # type-check
pip-audit                     # supply-chain scan
```

Le dipendenze sono bloccate tramite hash in un `uv.lock` sottoposto a commit
(disciplina della supply-chain). Gli aggiornamenti sono deliberati e revisionati;
nulla viene unito automaticamente.

## Licenza

[MIT](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE). © Lavelle Hatcher Jr.

---

## ⚠️ Avvertenza (ripetuta)

PennyTune è uno strumento di ricerca ed educativo, non un consiglio di
investimento. Non ti dice se acquistare, vendere o detenere un qualsiasi
titolo. Le micro-cap e le penny stock comportano un rischio estremo, inclusa
la possibile perdita totale del tuo capitale. L'avvertenza completa, che
costituisce la versione che fa fede, è disponibile in inglese nel
[README in inglese](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) e tramite il comando `pennytune disclaimer`.
