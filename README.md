# PennyTune

**Tune out the noise.**

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**PennyTune is a free, open-source, no-API-key forensic due-diligence tool for US-listed micro-caps.**
Point it at a ticker you already have (or rank the SEC-listed universe by filing
quality) and it surfaces the risk signals and forensic flags in that company's
SEC filings - accounting-quality and distress scores, dilution and
corporate-action risk, insider activity, 8-K material events, delisting-notice
and active trading-suspension risk, fails-to-deliver settlement context, and
news-coverage characterization - with **every flag traced to the underlying
filing**, so you can assess the company yourself.

It runs entirely on **public, no-account, no-API-key data sources**: SEC EDGAR
(the universe and all filings), plus GDELT news and SEC fails-to-deliver /
trading-suspension feeds for context. There is **no bring-your-own-key option
anywhere**.

> PennyTune surfaces **evidence for your own due diligence** - it does not tell
> you whether a stock is "clean" or "a landmine", does not give buy/sell advice,
> and does not predict outcomes. It analyzes **SEC-registered US-listed
> companies** and **fetches no live prices**: it does not screen by current
> price, compute technical indicators, or assess tradeability (bid-ask
> spread/liquidity). You supply the ticker(s) or use quality-based screening,
> and verify current price and tradeability yourself in a brokerage.

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
public sources (including SEC EDGAR, GDELT, and other public sources)
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

12. ACCEPTANCE. By installing, accessing, or using PennyTune, you
acknowledge that you have read, understood, and agree to this entire
disclaimer, and that you use the software entirely at your own risk. If
you do not agree, do not install or use the software.
```

---

## What it is

The US micro-cap segment is full of companies that look cheap *for cause* -
cash-burning, diluting, near delisting, or structured for manipulation. The hard
part of due diligence is reading the filings to find those landmines. PennyTune
does that reading for you: point it at a ticker (or screen the SEC-listed
universe by filing quality) and it extracts the risk signals and forensic flags
from the company's SEC filings and **shows its work for every one** - each flag
traced back to the filing it came from.

It surfaces **evidence, not verdicts.** It does not tell you a stock is clean or
a landmine, does not advise buying or selling, and does not predict outcomes -
the judgment is yours.

- **Free & no API keys** - runs entirely on no-account, no-key public data.
- **SEC-registered, listed on a major US exchange (NYSE/NASDAQ/NYSE American), never OTC** - by construction.
- **Evidence-traced** - every dilution, delisting, distress, and
  accounting-quality flag links to the underlying filing.
- **Transparent & tunable** - a decomposable composite score with user-editable
  weights, screening presets (`penny` default / `micro` / `small-cap-value` /
  `broad` / `custom`), and selectable strategy profiles (`hold` default /
  `trader` / `high-return` / `custom`).
- **No live prices** - it does not fetch current price or assess tradeability;
  verify those yourself in a brokerage.
- **Research only, not investment advice.**

## What it surfaces

For each company, PennyTune reads the SEC filings and grades the signals that
matter most for a micro-cap - every one linked back to the filing behind it:

- **Financial health & distress** - Altman Z″ solvency scoring plus a forensic
  battery (Beneish earnings-manipulation and Piotroski strength models) over the
  company's filed financials.
- **Dilution & corporate actions** - shelf and ATM ("at-the-market") offerings,
  rising share counts and dilution velocity, serial reverse-splits, and
  auditor-change / restatement flags drawn from the 8-K record.
- **Insider activity** - open-market insider *buying* (the conviction signal),
  kept distinct from routine grants and tax-withholding so awards never read as
  bullish - plus Form 144 proposed-sale overhang and 13D/13G ownership activity.
- **8-K material events** - the structured item-code tape (restatements, auditor
  changes, officer departures, listing-deficiency and other material items),
  weighted by severity rather than raw count.
- **Delisting-notice risk** - disclosed continued-listing deficiency notices
  (8-K Item 3.01), reported without guessing the price-clock day-count the tool
  cannot compute.
- **Active trading suspensions** - a company under a *current* SEC trading
  suspension is flagged and held out; expired historical suspensions are shown
  as context, not held against the company.
- **Fails-to-deliver** - settlement-stress context from the SEC's bi-monthly
  fails-to-deliver data (context only - not evidence of manipulation on its own).
- **News & coverage characterization** - tone, promotional-source skew, and
  catalyst keywords from news headlines and the SEC filing feed, framed as
  context. This is the lightest signal - coverage characterization, never a
  verdict.
- **Sector classification** - each company's SIC sector, so quality and
  valuation comparisons are made against sector-and-size peers rather than
  absolute cutoffs.

## Data & attribution

PennyTune uses only public, no-key data sources: **SEC EDGAR** (the universe -
from the SEC `company_tickers_exchange.json` listed-company file - and all
filings, fundamentals, and insider forms), plus the **SEC fails-to-deliver /
trading-suspension files** and **GDELT** news for context. The only identity
required anywhere is the SEC EDGAR `User-Agent` string (your name + email) - a
request header the SEC's fair-access policy requires to identify the requester,
not a PennyTune account, login, or key. It is stored only in your local config
(redacted in `config get`), sent only in the SEC request header, and never
transmitted to the author or any third party - GDELT requests use a generic
keyless User-Agent, so your email reaches only the SEC. Any valid personal email
works; setup checks the format, not the provider.

> **GDELT attribution (required).** Any use or redistribution of GDELT-derived
> output must credit *The GDELT Project* (<https://www.gdeltproject.org/>).
> PennyTune emits this attribution string with any GDELT-derived output.

PennyTune is a research tool and does **not** republish raw third-party
datasets; downloaded vendor data and the local cache are never committed.

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

Requires Python 3.11-3.13 (3.13 is the primary target). Python 3.14 is not yet
CI-verified.

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
already have and get its full, filing-traced forensic breakdown:

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

`scan` ranks the SEC-listed universe by **filing quality** (no price filtering -
the tool fetches no prices). Narrow it by listing venue and tune the risk
weighting and strategy:

```bash
pennytune scan                                   # rank the listed universe, top 10
pennytune scan --exchange nasdaq --top 25 --sort risk
pennytune --profile high-return scan --preset broad   # preset + profile compose
pennytune scan --exclude-serial-splitter --require-insider-buying --exclude-flagged

# Export the full ranked set (CSV/Parquet/JSON/Markdown); pipe clean JSON:
pennytune scan --format parquet
pennytune --json scan | jq '.results[0]'

# Cache-only run (no network) and a forced re-fetch:
pennytune --offline scan
pennytune --refresh scan
```

Every other command:

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
pennytune cache status        # inspect the local DuckDB/Parquet cache
pennytune cache clear --all   # clear it (confirmation-gated unless --yes)
```

Output leads with a freshness header (active preset/profile + per-domain as-of
stamps), shows a watchlist alert banner when relevant, ranks the top N, and ends
with the short disclaimer. Exported files carry the one-line disclaimer header
and - when a result used GDELT coverage - the GDELT attribution.

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

[MIT](LICENSE). © Lavelle Hatcher Jr.

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
public sources (including SEC EDGAR, GDELT, and other public sources)
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

12. ACCEPTANCE. By installing, accessing, or using PennyTune, you
acknowledge that you have read, understood, and agree to this entire
disclaimer, and that you use the software entirely at your own risk. If
you do not agree, do not install or use the software.
```
