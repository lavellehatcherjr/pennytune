<p align="center">
  <img src="https://raw.githubusercontent.com/lavellehatcherjr/pennytune/main/docs/assets/pennytune-logo.png" alt="PennyTune" width="400">
</p>

# PennyTune

**Tune out the noise.**

Read this in other languages: [日本語](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ja.md) | [Español](https://github.com/lavellehatcherjr/pennytune/blob/main/README.es.md) | [Français](https://github.com/lavellehatcherjr/pennytune/blob/main/README.fr.md) | [한국어](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ko.md) | [中文](https://github.com/lavellehatcherjr/pennytune/blob/main/README.zh.md) | [Deutsch](https://github.com/lavellehatcherjr/pennytune/blob/main/README.de.md) | [Português](https://github.com/lavellehatcherjr/pennytune/blob/main/README.pt.md) | [Italiano](https://github.com/lavellehatcherjr/pennytune/blob/main/README.it.md)

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**PennyTune is a free, open-source, no-API-key forensic due-diligence tool for US-listed micro-caps.**
Point it at the tickers you already hold or are watching and it surfaces the
risk signals and forensic flags in each company's SEC filings -
accounting-quality and distress scores, dilution and corporate-action risk,
insider activity, 8-K material events, delisting-notice and active
trading-suspension risk, and fails-to-deliver settlement context - **computed
from each company's public SEC filings**, so you can assess the company yourself.

It runs entirely on **public, no-account, no-API-key data**: SEC EDGAR is the
single data source (the listed-company universe, all filings, and the
fails-to-deliver / trading-suspension feeds). There is **no bring-your-own-key
option anywhere**.

> PennyTune surfaces **evidence for your own due diligence** - it does not tell
> you whether a stock is "clean" or "a landmine", does not give buy/sell advice,
> and does not predict outcomes. It analyzes **SEC-registered US-listed
> companies** and **fetches no live prices**: it does not screen by current
> price, compute technical indicators, or assess tradeability (bid-ask
> spread/liquidity). You supply the ticker(s) to rank, and verify current price
> and tradeability yourself in a brokerage.

---

## ⚠️ Disclaimer - please read carefully

```
DISCLAIMER — PLEASE READ CAREFULLY

1. NOT INVESTMENT ADVICE. PennyTune is a research and educational tool
only. Nothing it produces is investment advice, financial advice, legal
advice, tax advice, trading advice, or a recommendation, offer, or
solicitation to buy, sell, or hold any security or to make any financial
transaction. Rankings, scores, signals, and any other output are the
result of automated rules applied to public data and are provided for
informational and educational purposes only.

2. NO ADVISER RELATIONSHIP; NOT REGISTERED. The author is not a licensed
or registered financial advisor, investment adviser, broker, broker-
dealer, or investment professional, and is not registered with the U.S.
Securities and Exchange Commission, FINRA, or any state or other
securities regulator. Use of this software creates no advisory,
fiduciary, brokerage, agency, or professional relationship of any kind
between you and the author. The author is not acting as a fiduciary to
you.

3. NO RELIANCE. You agree not to rely on this software or its output as
the basis for any investment, trading, or financial decision. Any and
all decisions you make are made solely by you, in your own independent
judgment, and at your own risk. You are solely and exclusively
responsible for your own investment decisions and their consequences.

4. EXTREME RISK OF PENNY STOCKS. Penny stocks and low-priced, micro-cap,
and sub-$1 securities are highly speculative and carry a substantial
risk of loss, up to and including the TOTAL LOSS of your investment.
They are subject to low liquidity, extreme volatility, wide bid-ask
spreads, limited or unreliable public information, fraud, market
manipulation (including pump-and-dump schemes), dilution, reverse
splits, trading halts, suspensions, and delisting. You should not invest
any money you cannot afford to lose entirely.

5. NO GUARANTEE; FORWARD-LOOKING. Scores, rankings, and signals are NOT
predictions and do NOT guarantee any outcome or result. Past performance
is not indicative of, and does not guarantee, future results. No
representation is made that any account will or is likely to achieve
profits or losses similar to any analysis, backtest, or example shown.

6. THIRD-PARTY DATA "AS IS." All data is obtained from third-party and
public sources (including SEC EDGAR and other public sources)
and is provided "AS IS." Such data may be inaccurate,
incomplete, delayed, out of date, or wrong. The author does not create,
endorse, verify, or guarantee any third-party data and makes no
representation or warranty as to its accuracy, completeness, timeliness,
or fitness. You must independently verify all information against primary
sources (such as official SEC filings) before acting on it.

7. NO WARRANTY. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE
SOFTWARE IS PROVIDED "AS IS" AND "AS AVAILABLE," WITHOUT WARRANTY OF ANY
KIND, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE,
ACCURACY, AND NONINFRINGEMENT. THE AUTHOR DOES NOT WARRANT THAT THE
SOFTWARE WILL BE UNINTERRUPTED, ERROR-FREE, SECURE, OR THAT DEFECTS WILL
BE CORRECTED.

8. LIMITATION OF LIABILITY. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE
LAW, IN NO EVENT SHALL THE AUTHOR OR ANY CONTRIBUTOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE, OR
CONSEQUENTIAL DAMAGES, OR FOR ANY LOSS OF PROFITS, REVENUE, DATA, OR
INVESTMENT OR TRADING LOSSES, ARISING OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR ITS USE OR OUTPUT, WHETHER IN AN ACTION OF CONTRACT, TORT
(INCLUDING NEGLIGENCE), STRICT LIABILITY, OR OTHERWISE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGES. THIS LIMITATION APPLIES REGARDLESS OF
THE FAILURE OF ANY ESSENTIAL PURPOSE OF ANY LIMITED REMEDY.

9. INDEMNIFICATION. You agree to indemnify, defend, and hold harmless the
author and any contributors from and against any and all claims,
liabilities, damages, losses, costs, and expenses (including reasonable
legal fees) arising out of or related to your use of the software, your
investment or trading decisions, or your violation of this disclaimer.

10. COMPLIANCE. You are responsible for complying with all laws,
regulations, and rules applicable to you, including securities laws and
the terms of service of any data provider. The software is intended for
lawful personal and educational use only.

11. SEVERABILITY. If any provision of this disclaimer is held to be
invalid or unenforceable, that provision shall be limited or eliminated
to the minimum extent necessary, and the remaining provisions shall
remain in full force and effect.

12. NOT AFFILIATED WITH OR ENDORSED BY ANY REGULATOR. PennyTune is not
sponsored by, endorsed by, approved by, reviewed by, or affiliated with
the U.S. Securities and Exchange Commission (SEC), FINRA, the operators
of EDGAR, or any other government agency, regulator, or securities
exchange. References to "SEC," "EDGAR," and "SEC filings" identify only
the public data sources used and do not imply any endorsement,
partnership, or official status. No regulator sponsors, endorses,
reviews, or verifies PennyTune or its output.

13. INDEPENDENT PERSONAL PROJECT. PennyTune is a personal, independent,
open-source project. It is not a professional, advisory, or regulated
service, and nothing in it or its output constitutes professional or
regulated financial advice.

14. ACCEPTANCE. By installing, accessing, or using PennyTune, you
acknowledge that you have read, understood, and agree to this entire
disclaimer, and that you use the software entirely at your own risk. If
you do not agree, do not install or use the software.
```

---

## What it is

The US micro-cap segment is full of companies that look cheap *for cause* -
cash-burning, diluting, near delisting, or structured for manipulation. The hard
part of due diligence is reading the filings to find those landmines. PennyTune
does that reading for you: point it at a ticker, or rank a curated set of
tickers you choose, and it extracts the risk signals and forensic flags
from the company's SEC filings - **computed from the company's public SEC
filings**.

It surfaces **evidence, not verdicts.** It does not tell you a stock is clean or
a landmine, does not advise buying or selling, and does not predict outcomes -
the judgment is yours.

- **Free & no API keys** - runs entirely on no-account, no-key public data.
- **SEC-registered filers** - the ticker universe comes from SEC public data.
  There is no exchange filter: OTC-quoted names are scanned like any other,
  and the SEC file this is built from carries no NYSE American designation.
- **Evidence-based** - the signals that are computed come from the company's
  public SEC filings, and for event-driven red flags the specific 8-K item is
  named. Two contributors, valuation and coverage tone, have no data source in
  this build and are always suppressed (see **Limitations**).
- **Transparent & tunable** - a decomposable composite score with user-editable
  weights, screening presets (`penny` default / `micro` / `small-cap-value` /
  `broad` / `custom`), and selectable strategy profiles (`hold` default /
  `trader` / `high-return` / `custom`).
- **No live prices** - it does not fetch current price or assess tradeability;
  verify those yourself in a brokerage.
- **Research only, not investment advice.**

## What it surfaces

For each company, PennyTune reads the SEC filings and grades the signals that
matter most for a micro-cap. Any signal it cannot compute is suppressed and
reported as such, never scored as a zero:

- **Financial health & distress** - Altman Z″ solvency scoring plus a forensic
  battery (Beneish earnings-manipulation and Piotroski strength models) over the
  company's filed financials.
- **Dilution & corporate actions** - shelf and ATM ("at-the-market") offerings,
  rising share counts and dilution velocity, serial reverse-splits, and
  auditor-change / restatement flags drawn from the 8-K record.
- **Insider activity** - open-market insider *buying* (the conviction signal),
  kept distinct from routine grants and tax-withholding so awards never read as
  bullish - plus Form 144 proposed-sale overhang and 13D/13G ownership activity.
- **8-K material events** - the structured item-code tape, weighted by severity
  rather than raw count. Item 4.02, the issuer stating that its own previously
  issued financials can no longer be relied upon, is named and counted
  separately from an Item 4.01 change of auditor, alongside officer departures,
  listing-deficiency and the other material items.
- **Delisting-notice risk** - disclosed continued-listing deficiency notices
  (8-K Item 3.01), reported without guessing the price-clock day-count the tool
  cannot compute.
- **Trading suspensions** - a company with an SEC trading suspension in the
  last 180 days is flagged and held out. Note the tool does not track whether
  the suspension has since lapsed: SEC suspensions run at most 10 trading
  days, so a name can be held out on a suspension that has long expired.
- **Fails-to-deliver** - settlement-stress context from the SEC's twice-monthly
  fails-to-deliver data (context only - not evidence of manipulation on its own).
- **SEC staff comment letters** - whether the Division of Corporation Finance
  corresponded with the company in the last year, how many letters and
  registrant responses fall in that window, and the date of the most recent
  letter. Context only, never scored. The filing index records the letter but
  not its subject.
- **Sector classification** - each company's SIC sector is recorded and shown.
  It is context only: scoring uses fixed reference bands, not peer comparison.

## How the score works

The composite is an **unnormalized risk-weighted research score**:

    composite = sum(weight x positive sub-score) - sum(penalty x severity x confidence)

* **Positive contributors** are graded against **fixed reference bands** - the
  Piotroski 0-9 scale, the Altman Z-double-prime zones, and fixed EV/Sales and
  revenue-growth bands. A company's sub-score therefore depends only on its own
  filings, not on which other tickers were in the run, and is comparable across
  runs.
* **Penalties** subtract, scaled by severity and by the active preset.
* **Lower means more filing-derived risk was found.** It is not a valuation, not
  a prediction, and not comparable to a price target. A high score means "less
  risk was found in the filings", never "this will go up".
* The score is **not clamped** and has no fixed range; treat it as an ordering,
  not a magnitude.

**A ticker with no fetched SEC evidence is not scored.** It is reported as
`NOT ASSESSED`, named on the console, and excluded from the ranking, so absence
of evidence is never mistaken for absence of risk.

**Financial health uses re-anchored cutoffs, not Altman's published bands.**
Altman Z-double-prime is computed with its published coefficients, but the
solvency cutoffs are **-3.0 and 1.0**, not the published 1.1 and 2.6, and the
sub-score is graded continuously rather than in three steps. Measured on 194
real filers, using going-concern language in each company's own annual report as
an independent distress label: at the published cutoffs **0 of 41 going-concern
filers were missed, but 47 of 153 healthy filers were called distressed** -
among them Starbucks, HP, AbbVie, Amgen, Oracle, Lowe's, Duke Energy and AT&T.
The published 1.1 boundary sits at the 45th percentile of the real distribution.
The re-anchored cutoffs cut that false-distress rate from 31% to 12% and still
call no going-concern filer safe. This is a deliberate departure from the
published model.

Exports carry `suppressed`, `suppressed_count`, `evidence_complete` and
`completeness` columns, so a reader can tell an assessed row from an unassessed
one without reading prose.

## Limitations

Read these before trusting a ranking.

* **Two contributors are permanently zero.** `valuation` and `sentiment` have no
  data source in this build - there is no market-cap feed and no news feed - so
  they are suppressed for every company, on every run.
* **Altman is not computable for roughly a quarter of large caps.** Banks and
  REITs do not publish a classified balance sheet, and a number of large filers
  publish no operating-income subtotal. Where it cannot be computed it is
  suppressed and reported, never imputed - but the financial-health contributor
  is then missing entirely for that name.
* **Most rows rest on incomplete evidence.** In a representative 20-name scan,
  18 names had at least one check that could not be run. The
  `suppressed_count` column tells you how many, per row.
* **The tool ranks weakly, not authoritatively.** It is useful for deciding
  which filings to read first. It is not a screen you should act on directly,
  and no single flag should be treated as a verdict.
* **Comment-letter activity is history, not an open question.** The SEC releases
  a staff letter no earlier than 20 business days after the review has closed,
  and the filing index carries no subject. The tool can tell you that
  correspondence happened and when; it cannot tell you what was asked or whether
  anything is still outstanding. A letter with no matching response filing is
  not an unanswered one - registrants routinely reply inside another filing.
* **A watched name never alerts on its first run.** Alerts are computed against
  the previous snapshot, so a company raises nothing until it has been scanned
  at least twice.
* **No cache.** Every run re-fetches from SEC EDGAR. The `cache_ttl` settings
  shown by `config get` are inert.

## Data & attribution

PennyTune uses only public, no-key data from a single source: **SEC EDGAR** (the
universe - from the SEC `company_tickers_exchange.json` listed-company file - and
all filings, fundamentals, insider forms, and the fails-to-deliver /
trading-suspension files). The only identity required anywhere is the SEC EDGAR
`User-Agent` string (your name + email) - a request header the SEC's fair-access
policy requires to identify the requester, not a PennyTune account, login, or
key. It is stored only in your local config (redacted in `config get`), sent only
in the SEC request header, and never transmitted to the author or any third
party. Any valid personal email works; setup checks the format, not the provider.

PennyTune is a research tool and does **not** republish raw third-party
datasets; your config and any exported results stay local (never committed).

## Install

PennyTune is a command-line tool published on PyPI. Install it with pip - the
simple, universal default:

```bash
pip install pennytune
```

Because it's a CLI, an **isolated install (recommended for command-line tools)**
keeps it out of your other Python environments:

```bash
pipx install pennytune       # isolated install via pipx
uv tool install pennytune    # the same, via uv's tool installer
```

Requires Python 3.11-3.14 (all CI-tested across Linux, macOS, and Windows; 3.13
is the primary target for linting and type-checking).

**From source (for development):**

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

## Usage

First-time setup records the SEC EDGAR identity (a required request header - not
a key) and the risk acknowledgment; `scan`/`inspect` refuse to run until both
exist:

```bash
pennytune init --identity "Your Name you@example.com" --i-understand-the-risks
```

The primary workflow is **`inspect <TICKER>`** - point the tool at a company you
already have and get its full forensic breakdown computed from the filings:

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

`scan` ranks a **curated set of tickers you choose** - given explicitly or read
from your watchlist - by their SEC-filing risk signals (no price filtering - the
tool fetches no prices). At most 100 tickers per run; PennyTune never scans the
whole market. Positive sub-scores are graded against **fixed reference bands**,
so a company's score does not depend on which other tickers were in the run and
is comparable across runs. The ranking is nonetheless driven mainly by the
**risk/penalty** signals (dilution, distress, delisting, insider selling), since
those are what the filings support best. Tune the weighting and strategy with
`--preset` / `--profile`:

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

Every other command:

```bash
pennytune --help              # all commands and global flags
pennytune --version           # app version + pinned dependency versions
pennytune disclaimer          # print the full legal disclaimer
pennytune watch add GROW NUKK # persistent watchlist (add | list | rm)
pennytune watch list          #   run-over-run score deltas
pennytune config get          # view all settings (EDGAR email redacted)
pennytune config set weights.valuation 1.5   # tune a scoring weight
pennytune config set profile custom          # switch to hand-tuned weights
pennytune sources             # data sources, rate limits, contacted domains
```

`scan` output leads with a header (active preset/profile + data-freshness
lines), ranks the top N, and ends with the short disclaimer. Exported files
carry the one-line disclaimer header so the disclaimer travels with the data.

## Development

```bash
python -m pytest tests/ -v    # run the test suite
ruff check .                  # lint
python -m mypy                # type-check
pip-audit                     # supply-chain scan
```

Dependencies are hash-pinned in a committed `uv.lock` (supply-chain discipline).
Upgrades are deliberate and reviewed; nothing auto-merges.

## License

[MIT](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE). © Lavelle Hatcher Jr.

---

## ⚠️ Disclaimer (repeated)

```
DISCLAIMER — PLEASE READ CAREFULLY

1. NOT INVESTMENT ADVICE. PennyTune is a research and educational tool
only. Nothing it produces is investment advice, financial advice, legal
advice, tax advice, trading advice, or a recommendation, offer, or
solicitation to buy, sell, or hold any security or to make any financial
transaction. Rankings, scores, signals, and any other output are the
result of automated rules applied to public data and are provided for
informational and educational purposes only.

2. NO ADVISER RELATIONSHIP; NOT REGISTERED. The author is not a licensed
or registered financial advisor, investment adviser, broker, broker-
dealer, or investment professional, and is not registered with the U.S.
Securities and Exchange Commission, FINRA, or any state or other
securities regulator. Use of this software creates no advisory,
fiduciary, brokerage, agency, or professional relationship of any kind
between you and the author. The author is not acting as a fiduciary to
you.

3. NO RELIANCE. You agree not to rely on this software or its output as
the basis for any investment, trading, or financial decision. Any and
all decisions you make are made solely by you, in your own independent
judgment, and at your own risk. You are solely and exclusively
responsible for your own investment decisions and their consequences.

4. EXTREME RISK OF PENNY STOCKS. Penny stocks and low-priced, micro-cap,
and sub-$1 securities are highly speculative and carry a substantial
risk of loss, up to and including the TOTAL LOSS of your investment.
They are subject to low liquidity, extreme volatility, wide bid-ask
spreads, limited or unreliable public information, fraud, market
manipulation (including pump-and-dump schemes), dilution, reverse
splits, trading halts, suspensions, and delisting. You should not invest
any money you cannot afford to lose entirely.

5. NO GUARANTEE; FORWARD-LOOKING. Scores, rankings, and signals are NOT
predictions and do NOT guarantee any outcome or result. Past performance
is not indicative of, and does not guarantee, future results. No
representation is made that any account will or is likely to achieve
profits or losses similar to any analysis, backtest, or example shown.

6. THIRD-PARTY DATA "AS IS." All data is obtained from third-party and
public sources (including SEC EDGAR and other public sources)
and is provided "AS IS." Such data may be inaccurate,
incomplete, delayed, out of date, or wrong. The author does not create,
endorse, verify, or guarantee any third-party data and makes no
representation or warranty as to its accuracy, completeness, timeliness,
or fitness. You must independently verify all information against primary
sources (such as official SEC filings) before acting on it.

7. NO WARRANTY. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE
SOFTWARE IS PROVIDED "AS IS" AND "AS AVAILABLE," WITHOUT WARRANTY OF ANY
KIND, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE,
ACCURACY, AND NONINFRINGEMENT. THE AUTHOR DOES NOT WARRANT THAT THE
SOFTWARE WILL BE UNINTERRUPTED, ERROR-FREE, SECURE, OR THAT DEFECTS WILL
BE CORRECTED.

8. LIMITATION OF LIABILITY. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE
LAW, IN NO EVENT SHALL THE AUTHOR OR ANY CONTRIBUTOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE, OR
CONSEQUENTIAL DAMAGES, OR FOR ANY LOSS OF PROFITS, REVENUE, DATA, OR
INVESTMENT OR TRADING LOSSES, ARISING OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR ITS USE OR OUTPUT, WHETHER IN AN ACTION OF CONTRACT, TORT
(INCLUDING NEGLIGENCE), STRICT LIABILITY, OR OTHERWISE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGES. THIS LIMITATION APPLIES REGARDLESS OF
THE FAILURE OF ANY ESSENTIAL PURPOSE OF ANY LIMITED REMEDY.

9. INDEMNIFICATION. You agree to indemnify, defend, and hold harmless the
author and any contributors from and against any and all claims,
liabilities, damages, losses, costs, and expenses (including reasonable
legal fees) arising out of or related to your use of the software, your
investment or trading decisions, or your violation of this disclaimer.

10. COMPLIANCE. You are responsible for complying with all laws,
regulations, and rules applicable to you, including securities laws and
the terms of service of any data provider. The software is intended for
lawful personal and educational use only.

11. SEVERABILITY. If any provision of this disclaimer is held to be
invalid or unenforceable, that provision shall be limited or eliminated
to the minimum extent necessary, and the remaining provisions shall
remain in full force and effect.

12. NOT AFFILIATED WITH OR ENDORSED BY ANY REGULATOR. PennyTune is not
sponsored by, endorsed by, approved by, reviewed by, or affiliated with
the U.S. Securities and Exchange Commission (SEC), FINRA, the operators
of EDGAR, or any other government agency, regulator, or securities
exchange. References to "SEC," "EDGAR," and "SEC filings" identify only
the public data sources used and do not imply any endorsement,
partnership, or official status. No regulator sponsors, endorses,
reviews, or verifies PennyTune or its output.

13. INDEPENDENT PERSONAL PROJECT. PennyTune is a personal, independent,
open-source project. It is not a professional, advisory, or regulated
service, and nothing in it or its output constitutes professional or
regulated financial advice.

14. ACCEPTANCE. By installing, accessing, or using PennyTune, you
acknowledge that you have read, understood, and agree to this entire
disclaimer, and that you use the software entirely at your own risk. If
you do not agree, do not install or use the software.
```
