<p align="center">
  <img src="https://raw.githubusercontent.com/lavellehatcherjr/pennytune/main/docs/assets/pennytune-logo.png" alt="PennyTune" width="400">
</p>

> Hinweis: Dies ist eine ausschließlich zu Informationszwecken bereitgestellte Übersetzung. Die [englische README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) ist die offizielle, maßgebliche Fassung. Die Benutzeroberfläche, die Befehle und die Ausgabe von PennyTune sind ausschließlich in englischer Sprache verfügbar. Im Falle von Abweichungen ist die englische Fassung maßgeblich.

[English](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) | [日本語](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ja.md) | [Español](https://github.com/lavellehatcherjr/pennytune/blob/main/README.es.md) | [Français](https://github.com/lavellehatcherjr/pennytune/blob/main/README.fr.md) | [한국어](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ko.md) | [中文](https://github.com/lavellehatcherjr/pennytune/blob/main/README.zh.md) | Deutsch | [Português](https://github.com/lavellehatcherjr/pennytune/blob/main/README.pt.md) | [Italiano](https://github.com/lavellehatcherjr/pennytune/blob/main/README.it.md)

# PennyTune

**Blenden Sie das Rauschen aus.**

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**PennyTune ist ein kostenloses, quelloffenes forensisches Due-Diligence-Tool für US-notierte Micro-Caps, das ohne API-Schlüssel auskommt.**
Richten Sie es auf die Ticker, die Sie bereits halten oder beobachten, und es legt
die Risikosignale und forensischen Warnzeichen in den SEC-Einreichungen jedes Unternehmens offen -
Kennzahlen zur Bilanzqualität und zum Insolvenzrisiko, Verwässerungs- und Corporate-Action-Risiko,
Insider-Aktivitäten, wesentliche Ereignisse aus 8-K-Meldungen, Delisting-Hinweis- und aktives
Handelsaussetzungsrisiko sowie Kontext zu Lieferausfällen (Fails-to-Deliver) bei der Abwicklung - **berechnet
aus den öffentlichen SEC-Einreichungen jedes Unternehmens**, sodass Sie das Unternehmen selbst beurteilen können.

Es läuft vollständig mit **öffentlichen Daten ohne Konto und ohne API-Schlüssel**: SEC EDGAR ist die
einzige Datenquelle (das Universum der notierten Unternehmen, alle Einreichungen sowie die
Feeds zu Fails-to-Deliver / Handelsaussetzungen). Es gibt **nirgendwo eine Bring-your-own-key-Option**.

> PennyTune legt **Belege für Ihre eigene Due Diligence** offen - es sagt Ihnen nicht,
> ob eine Aktie „sauber" oder „eine Tretmine" ist, gibt keine Kauf-/Verkaufsempfehlungen
> und sagt keine Ergebnisse voraus. Es analysiert **SEC-registrierte, US-notierte
> Unternehmen** und **ruft keine Live-Kurse ab**: Es filtert nicht nach dem aktuellen
> Kurs, berechnet keine technischen Indikatoren und beurteilt nicht die Handelbarkeit
> (Geld-Brief-Spanne/Liquidität). Sie liefern den/die Ticker, die eingestuft werden sollen, und überprüfen den aktuellen Kurs
> und die Handelbarkeit selbst bei einem Broker.

---

## ⚠️ Haftungsausschluss - bitte sorgfältig lesen

PennyTune ist ein Recherche- und Bildungswerkzeug, keine Anlageberatung. Es sagt Ihnen nicht, ob Sie ein Wertpapier kaufen, verkaufen oder halten sollen. Micro-Cap- und Penny Stocks bergen ein extremes Risiko, einschließlich des möglichen Totalverlusts Ihres Kapitals. Der vollständige Haftungsausschluss, der die maßgebliche Fassung darstellt, ist auf Englisch in der [englischen README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) und über den Befehl `pennytune disclaimer` verfügbar.

---

## Was es ist

Das US-Micro-Cap-Segment ist voll von Unternehmen, die *aus gutem Grund* günstig
aussehen - sie verbrennen Cash, verwässern, stehen kurz vor dem Delisting oder
sind auf Manipulation ausgelegt. Der schwierige Teil der Due Diligence besteht
darin, die Einreichungen zu lesen, um diese Tretminen zu finden. PennyTune
übernimmt dieses Lesen für Sie: Richten Sie es auf einen Ticker oder stufen Sie
eine kuratierte, von Ihnen gewählte Auswahl an Tickern ein, und es extrahiert
die Risikosignale und forensischen Warnzeichen aus den SEC-Einreichungen des
Unternehmens - **berechnet aus den öffentlichen SEC-Einreichungen des Unternehmens**.

Es legt **Belege offen, keine Urteile.** Es sagt Ihnen nicht, dass eine Aktie sauber oder
eine Tretmine ist, rät weder zum Kauf noch zum Verkauf und sagt keine Ergebnisse voraus -
das Urteil liegt bei Ihnen.

- **Kostenlos & ohne API-Schlüssel** - läuft vollständig mit öffentlichen Daten ohne Konto und ohne Schlüssel.
- **SEC-registriert, an einer großen US-Börse notiert (NYSE/NASDAQ/NYSE American), niemals OTC** - per Konstruktion.
- **Belegbasiert** - jedes Signal wird aus den öffentlichen SEC-Einreichungen des
  Unternehmens berechnet, und bei ereignisgetriebenen Warnsignalen wird der konkrete 8-K-Punkt benannt.
- **Transparent & abstimmbar** - ein zerlegbarer zusammengesetzter Score mit benutzerseitig
  bearbeitbaren Gewichtungen, Screening-Voreinstellungen (`penny` Standard / `micro` / `small-cap-value` /
  `broad` / `custom`) sowie auswählbaren Strategieprofilen (`hold` Standard /
  `trader` / `high-return` / `custom`).
- **Keine Live-Kurse** - es ruft keinen aktuellen Kurs ab und beurteilt nicht die Handelbarkeit;
  überprüfen Sie diese selbst bei einem Broker.
- **Nur Recherche, keine Anlageberatung.**

## Was es offenlegt

Für jedes Unternehmen liest PennyTune die SEC-Einreichungen und bewertet die Signale, die
für einen Micro-Cap am wichtigsten sind - jedes davon aus den Einreichungen des Unternehmens berechnet:

- **Finanzielle Gesundheit & Insolvenzgefahr** - Altman-Z″-Solvenzbewertung sowie eine
  forensische Reihe (Beneish-Modell zur Gewinnmanipulation und Piotroski-Stärkemodell) über die
  eingereichten Finanzdaten des Unternehmens.
- **Verwässerung & Corporate Actions** - Shelf- und ATM-Angebote („at-the-market"),
  steigende Aktienzahlen und Verwässerungsgeschwindigkeit, serielle Reverse Splits sowie
  Warnzeichen für Wirtschaftsprüferwechsel / Restatements aus den 8-K-Meldungen.
- **Insider-Aktivitäten** - Insider-*Käufe* am offenen Markt (das Überzeugungssignal),
  klar getrennt von routinemäßigen Zuteilungen und Steuereinbehaltung, sodass Zuteilungen niemals als
  optimistisch gelesen werden - sowie Überhang aus geplanten Verkäufen (Form 144) und 13D/13G-Eigentumsaktivität.
- **Wesentliche Ereignisse aus 8-K-Meldungen** - das strukturierte Band der Item-Codes (Restatements, Wirtschaftsprüfer-
  wechsel, Abgänge von Führungskräften, Notierungsdefizite und andere wesentliche Punkte),
  gewichtet nach Schweregrad statt nach reiner Anzahl.
- **Delisting-Hinweis-Risiko** - offengelegte Hinweise auf Defizite bei der fortgesetzten Notierung
  (8-K Item 3.01), gemeldet ohne zu erraten, wie viele Tage die Kursfrist umfasst, die das Tool
  nicht berechnen kann.
- **Aktive Handelsaussetzungen** - ein Unternehmen, das einer *aktuellen* SEC-Handelsaussetzung
  unterliegt, wird gekennzeichnet und ausgeschlossen; abgelaufene historische Aussetzungen werden
  als Kontext angezeigt und nicht zulasten des Unternehmens gewertet.
- **Fails-to-Deliver** - Kontext zu Abwicklungsstress aus den zweimonatlichen
  Fails-to-Deliver-Daten der SEC (nur Kontext - für sich allein kein Beleg für Manipulation).
- **Sektorklassifizierung** - der SIC-Sektor jedes Unternehmens, sodass Qualitäts- und
  Bewertungsvergleiche gegen Vergleichswerte nach Sektor und Größe statt gegen absolute
  Schwellenwerte angestellt werden.

## Daten & Quellenangabe

PennyTune verwendet ausschließlich öffentliche Daten ohne Schlüssel aus einer einzigen Quelle: **SEC EDGAR** (das
Universum - aus der Datei `company_tickers_exchange.json` der SEC mit den notierten Unternehmen - sowie
alle Einreichungen, Fundamentaldaten, Insider-Formulare und die Dateien zu Fails-to-Deliver /
Handelsaussetzungen). Die einzige überhaupt erforderliche Identität ist die `User-Agent`-Zeichenkette
von SEC EDGAR (Ihr Name + Ihre E-Mail-Adresse) - ein Anfrage-Header, den die Fair-Access-Richtlinie der SEC
zur Identifizierung des Anfragenden verlangt, kein PennyTune-Konto, kein Login und kein Schlüssel. Sie wird nur
in Ihrer lokalen Konfiguration gespeichert (in `config get` redigiert), nur im SEC-Anfrage-Header gesendet
und niemals an den Autor oder einen Dritten übermittelt. Jede gültige persönliche E-Mail-Adresse funktioniert;
das Setup prüft das Format, nicht den Anbieter.

PennyTune ist ein Recherchewerkzeug und veröffentlicht **keine** rohen Drittanbieter-Datensätze
erneut; Ihre Konfiguration und alle exportierten Ergebnisse bleiben lokal (werden niemals committet).

## Installation

PennyTune ist ein Kommandozeilen-Tool, das auf PyPI veröffentlicht ist. Installieren Sie es mit pip - dem
einfachen, universellen Standard:

```bash
pip install pennytune
```

Da es sich um ein CLI handelt, hält eine **isolierte Installation (empfohlen für Kommandozeilen-Tools)**
es aus Ihren anderen Python-Umgebungen heraus:

```bash
pipx install pennytune       # isolated install via pipx
uv tool install pennytune    # the same, via uv's tool installer
```

Erfordert Python 3.11-3.14 (alle CI-getestet unter Linux, macOS und Windows; 3.13
ist das primäre Ziel für Linting und Typprüfung).

**Aus dem Quellcode (für die Entwicklung):**

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

## Verwendung

Beim ersten Setup werden die SEC-EDGAR-Identität (ein erforderlicher Anfrage-Header - kein
Schlüssel) und die Risikobestätigung erfasst; `scan`/`inspect` verweigern die Ausführung, bis beide
vorhanden sind:

```bash
pennytune init --identity "Your Name you@example.com" --i-understand-the-risks
```

Der primäre Arbeitsablauf ist **`inspect <TICKER>`** - richten Sie das Tool auf ein Unternehmen, das Sie
bereits halten, und erhalten Sie dessen vollständige forensische Aufschlüsselung, berechnet aus den Einreichungen:

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

`scan` stuft eine **kuratierte, von Ihnen gewählte Auswahl an Tickern** ein - explizit angegeben oder aus
Ihrer Beobachtungsliste eingelesen - nach ihren Risikosignalen aus SEC-Einreichungen (keine Kursfilterung - das
Tool ruft keine Kurse ab). Höchstens 100 Ticker pro Durchlauf; PennyTune durchsucht niemals den
gesamten Markt. Da die positiven Qualitäts-Subscores sektor-/größenrelative Perzentile sind
(nur über einen großen Querschnitt aussagekräftig), wird die Einstufung bei einer kleinen kuratierten
Auswahl hauptsächlich von den **Risiko-/Strafsignalen** bestimmt (Verwässerung,
Insolvenzgefahr, Delisting, Insider-Verkäufe) - sie legt die riskantesten Namen in Ihrer
Auswahl offen. Stimmen Sie die Risikogewichtung und die Strategie mit `--preset` / `--profile` ab:

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

Alle weiteren Befehle:

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

Die Ausgabe beginnt mit einem Aktualitäts-Header (aktive Voreinstellung/aktives Profil + Stand-Stempel
je Domain), zeigt bei Bedarf ein Beobachtungslisten-Warnbanner an, stuft die Top N ein und endet
mit dem kurzen Haftungsausschluss. Exportierte Dateien tragen die einzeilige Haftungsausschluss-Kopfzeile,
sodass der Haftungsausschluss mit den Daten mitreist.

## Entwicklung

```bash
python -m pytest tests/ -v    # run the test suite
ruff check .                  # lint
python -m mypy                # type-check
pip-audit                     # supply-chain scan
```

Die Abhängigkeiten sind in einer committeten `uv.lock` per Hash gepinnt (Lieferketten-Disziplin).
Upgrades erfolgen bewusst und werden überprüft; nichts wird automatisch gemergt.

## Lizenz

[MIT](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE). © Lavelle Hatcher Jr.

---

## ⚠️ Haftungsausschluss (Wiederholung)

PennyTune ist ein Recherche- und Bildungswerkzeug, keine Anlageberatung. Es sagt Ihnen nicht, ob Sie ein Wertpapier kaufen, verkaufen oder halten sollen. Micro-Cap- und Penny Stocks bergen ein extremes Risiko, einschließlich des möglichen Totalverlusts Ihres Kapitals. Der vollständige Haftungsausschluss, der die maßgebliche Fassung darstellt, ist auf Englisch in der [englischen README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) und über den Befehl `pennytune disclaimer` verfügbar.
