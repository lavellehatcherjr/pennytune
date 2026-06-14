# Contributing to PennyTune

PennyTune is a free, open-source, no-API-key forensic due-diligence CLI for
US-listed micro-caps. It surfaces the risk signals and forensic flags in a
company's SEC filings — **evidence for your own due diligence, not investment
advice**. Contributions are welcome; please read this first.

## Quick Links

- **GitHub:** <https://github.com/lavellehatcherjr/pennytune>
- **Issues:** <https://github.com/lavellehatcherjr/pennytune/issues/new>
- **Maintainer:** Lavelle Hatcher Jr ([@lavellehatcherjr](https://github.com/lavellehatcherjr)) — Creator & Maintainer

## How to Contribute

PennyTune is maintained by one person, who reviews and decides on every
contribution — so not everything will be merged. For anything beyond a small
fix, please open an issue first so we can agree on the approach before you write
code.

- **Typos / small bug fixes** → open a PR directly.
- **New features / larger changes** → open an issue first.
- **Refactor-only or style-only PRs** → please don't, unless they were asked for.
- **Questions** → open an issue.

Reviews can take time (solo maintainer) — thanks for your patience.

## Project Scope

To avoid wasted effort, please keep changes within PennyTune's deliberate scope:

- **Evidence, not advice.** PennyTune surfaces evidence for the user's own due
  diligence — never buy/sell advice, verdicts, or price predictions. PRs must
  not introduce investment advice, recommendations, or outcome predictions.
- **Public, no-key data only.** PennyTune runs on public, no-API-key data (SEC
  EDGAR + GDELT). PRs adding paid or API-key-gated data sources are out of scope.
- **No prices / no technicals.** By design the tool fetches no live prices and
  does not assess tradeability. PRs adding price or technical-analysis features
  are out of scope.

## Development Setup

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

Requires Python 3.11+.

Running PennyTune against live data requires setting the SEC EDGAR identity:

```bash
pennytune init --identity "Your Name you@example.com"
```

The SEC's fair-access policy requires a contact `User-Agent`. PennyTune
rate-limits SEC requests (the SEC asks for no more than 10 requests/second);
please don't disable or raise the limiter when testing against live SEC data.

## Running Tests and Lint

CI enforces all four checks — run them locally before opening a PR:

```bash
python -m pytest tests/ -v   # full test suite
ruff check .                 # lint
python -m mypy               # type-check
pip-audit                    # supply-chain scan
```

All tests must pass, and changes should be ruff-clean and mypy-clean.

## What Makes a Good PR

- **Focused** — one logical change per PR.
- **Tested** — include or update tests for any behavior change.
- **Consistent** — match the existing code style.
- **Explained** — describe what changed and why.
- **Sourced** — if a change affects scoring, the gates, or the forensic models,
  explain the reasoning and cite the source (the filing or the standard) where
  relevant. Accuracy matters for a due-diligence tool.

## Security

See [SECURITY.md](SECURITY.md) for how to report security vulnerabilities.
Please do **not** open public issues for security problems.

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT](LICENSE) license.
