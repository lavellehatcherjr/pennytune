"""End-to-end user-flow tests - complete journeys, exercised via the CLI.

Each test drives a whole documented flow (not just a feature in isolation)
through the Typer app with CliRunner: onboarding, the core research loop,
watchlist, export, profile-switching, config/cache/sources, offline+degradation,
and machine-readable + banner suppression. Network is never touched - the
universe and evidence seams are injected with fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pennytune import cli
from pennytune import scan as scan_mod
from pennytune.cli import app
from pennytune.disclaimer import EXPORT_HEADER
from pennytune.features.delisting import DelistingInputs
from pennytune.features.quant_scores import PeriodFinancials
from pennytune.features.universe import UniverseCandidate
from pennytune.output import read_parquet_disclaimer

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PENNYTUNE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("PENNYTUNE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PENNYTUNE_DATA_DIR", str(tmp_path / "data"))


# ---- shared fixtures --------------------------------------------------------


def _period(*, scale: float = 1.0, **kw: float) -> PeriodFinancials:
    base: dict[str, float | None] = dict(
        total_assets=1000.0 * scale,
        current_assets=600.0 * scale,
        current_liabilities=200.0 * scale,
        cash=300.0 * scale,
        total_liabilities=300.0 * scale,
        total_debt=100.0 * scale,
        long_term_debt=80.0 * scale,
        retained_earnings=200.0 * scale,
        book_equity=700.0 * scale,
        revenue=900.0 * scale,
        cogs=500.0 * scale,
        ebit=120.0 * scale,
        net_income=90.0 * scale,
        operating_cash_flow=110.0 * scale,
        capex=30.0 * scale,
        interest_expense=10.0 * scale,
        shares_outstanding=1000.0 * scale,
        receivables=120.0 * scale,
        inventory=80.0 * scale,
        gross_ppe=400.0 * scale,
        net_ppe=300.0 * scale,
        depreciation=40.0 * scale,
        sga=150.0 * scale,
    )
    base.update(kw)
    return PeriodFinancials(**base)


def _candidate(ticker: str) -> UniverseCandidate:
    return UniverseCandidate(
        ticker=ticker, name=ticker, cik="0000000001", exchange="Nasdaq"
    )


def _evidence(
    ticker: str,
    *,
    cap: float,
    growth: float,
    sentiment: float,
    delisting: bool = False,
) -> scan_mod.RawEvidence:
    return scan_mod.RawEvidence(
        ticker=ticker,
        sic_sector="3674",
        sic_code=3674,
        market_cap=cap,
        current_price=0.5,
        period_t=_period(),
        period_t1=_period(scale=0.85),
        revenue_growth=growth,
        sentiment_compound=sentiment,
        delisting=DelistingInputs(deficiency_notice=True) if delisting else None,
    )


# SENT: sentiment-heavy + a delisting penalty (which `hold` weights 1.6x vs
# `trader` 1.0x); VALU: cheaper + clean but low sentiment. Growth equalized so
# the only differentiators are valuation (favors VALU) and sentiment (favors
# SENT) - so trader ranks SENT first, hold ranks VALU first (a real flip).
_MAPPING = {
    "SENT": _evidence(
        "SENT", cap=120_000_000.0, growth=0.20, sentiment=0.95, delisting=True
    ),
    "VALU": _evidence("VALU", cap=60_000_000.0, growth=0.20, sentiment=-0.80),
}


class _FixtureProvider:
    def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
        return _MAPPING[candidate.ticker]


def _install_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    # scan ranks an explicit curated set (tickers / watchlist); only the
    # evidence provider needs a fixture - no universe is built.
    monkeypatch.setattr(
        cli, "_make_evidence_provider", lambda config, state: _FixtureProvider()
    )


def _init(cfg: Path, profile: str = "hold") -> None:
    res = runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "Dana Lee dana@example.com",
            "--profile",
            profile,
            "--i-understand-the-risks",
        ],
    )
    assert res.exit_code == 0, res.output


# ---- Flow 1: first-run onboarding (positive + negative) ---------------------


def test_flow_onboarding(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    # Negative path: scan/inspect refuse before acknowledgment (exit 3).
    assert runner.invoke(app, ["--config", str(cfg), "scan"]).exit_code == 3
    assert runner.invoke(app, ["--config", str(cfg), "inspect", "AAA"]).exit_code == 3
    # Positive: init persists state, and a subsequent read-back command works.
    _init(cfg)
    assert cfg.exists()
    got = runner.invoke(app, ["--config", str(cfg), "config", "get", "profile"])
    assert got.exit_code == 0 and "hold" in got.output


# ---- Flow 2: core research loop --------------------------------------------


def test_flow_core_research_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    _install_pipeline(monkeypatch)

    scan = runner.invoke(
        app, ["--config", str(cfg), "scan", "SENT", "VALU", "--top", "5"]
    )
    assert scan.exit_code == 0, scan.output
    assert "VALU" in scan.output
    assert "Not investment advice" in scan.output  # disclaimer footer

    inspect = runner.invoke(app, ["--config", str(cfg), "inspect", "VALU"])
    assert inspect.exit_code == 0
    assert "composite" in inspect.output.lower()

    # Reproducible: the same fixtures + weights → the same JSON ranking.
    first = runner.invoke(
        app, ["--config", str(cfg), "--json", "scan", "SENT", "VALU"]
    ).output
    second = runner.invoke(
        app, ["--config", str(cfg), "--json", "scan", "SENT", "VALU"]
    ).output
    order1 = [r["ticker"] for r in json.loads(first)["results"]]
    order2 = [r["ticker"] for r in json.loads(second)["results"]]
    assert order1 == order2


# ---- Flow 3: watchlist loop -------------------------------------------------


def test_flow_watchlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    _install_pipeline(monkeypatch)
    assert runner.invoke(app, ["watch", "add", "VALU"]).exit_code == 0

    # Seed a high prior snapshot so the next scan's lower score raises an alert.
    from pennytune import paths
    from pennytune.features.watchlist import Watchlist

    wl = Watchlist(db_path=paths.data_dir() / "pennytune.db")
    wl.record_snapshot("VALU", 99.0, [])
    wl.close()

    scan = runner.invoke(app, ["--config", str(cfg), "scan"])
    assert "Watchlist alerts" in scan.output
    listed = runner.invoke(app, ["watch", "list"])
    assert "VALU" in listed.output
    assert runner.invoke(app, ["watch", "rm", "VALU"]).exit_code == 0
    assert "VALU" not in runner.invoke(app, ["watch", "list"]).output


# ---- Flow 4: export loop (every format, disclaimer header + GDELT credit) ----


@pytest.mark.parametrize(
    "fmt,ext",
    [("csv", "csv"), ("json", "json"), ("markdown", "md"), ("parquet", "parquet")],
)
def test_flow_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fmt: str, ext: str
) -> None:
    cfg = tmp_path / "c.toml"
    out = tmp_path / "out"
    _init(cfg)
    _install_pipeline(monkeypatch)

    result = runner.invoke(
        app,
        ["--config", str(cfg), "scan", "SENT", "VALU", "--format", fmt, "--top", "5"],
    )
    assert result.exit_code == 0, result.output
    # output_dir defaults to ./results; redirect via config for the test.
    runner.invoke(app, ["--config", str(cfg), "config", "set", "output_dir", str(out)])
    result = runner.invoke(
        app, ["--config", str(cfg), "scan", "SENT", "VALU", "--format", fmt]
    )
    assert result.exit_code == 0, result.output

    files = list(out.glob(f"scan_*.{ext}"))
    assert files, f"no {fmt} export written"
    path = files[0]
    if fmt == "parquet":
        assert read_parquet_disclaimer(path) == EXPORT_HEADER
    else:
        text = path.read_text(encoding="utf-8")
        assert "research/educational only" in text  # one-line disclaimer header


# ---- Flow 5: profile-switching yields different rankings --------------------


def test_flow_profile_switching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    _install_pipeline(monkeypatch)

    def _order(profile: str) -> list[str]:
        out = runner.invoke(
            app,
            [
                "--config",
                str(cfg),
                "--profile",
                profile,
                "--json",
                "scan",
                "SENT",
                "VALU",
            ],
        ).output
        return [r["ticker"] for r in json.loads(out)["results"]]

    trader = _order("trader")
    hold = _order("hold")
    # The same fixture universe ranks differently under different profiles
    # (trader favors SENT's sentiment; hold's heavier delisting/valuation
    # weighting favors clean, cheap VALU).
    assert trader != hold


# ---- Flow 6: config + cache + sources + disclaimer --------------------------


def test_flow_config_cache_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)

    # config set changes a weight; the next scan's JSON meta reflects it.
    runner.invoke(
        app, ["--config", str(cfg), "config", "set", "weights.valuation", "3.0"]
    )
    _install_pipeline(monkeypatch)
    payload = json.loads(
        runner.invoke(
            app, ["--config", str(cfg), "--json", "scan", "SENT", "VALU"]
        ).output
    )
    # valuation weight 3.0 lifts the cheap name's valuation contribution.
    valu = next(r for r in payload["results"] if r["ticker"] == "VALU")
    assert valu["positive_contributions"]["valuation"] > 1.0

    assert runner.invoke(app, ["sources"]).exit_code == 0
    assert "DISCLAIMER" in runner.invoke(app, ["disclaimer"]).output


# ---- Flow 7: offline + degradation ------------------------------------------


def test_flow_offline_and_degradation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)

    # Offline: the degrading provider returns completeness-flagged evidence for
    # the chosen ticker without any network call.
    offline = runner.invoke(app, ["--config", str(cfg), "--offline", "scan", "AAA"])
    assert offline.exit_code == 0

    # Provider "down": gather returns degraded, completeness-flagged evidence.
    class _Down:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            return scan_mod.degraded_evidence(candidate, "provider down")

    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Down())
    degraded = runner.invoke(app, ["--config", str(cfg), "scan", "DOWN"])
    assert degraded.exit_code == 0
    assert "reduced data completeness" in degraded.output


# ---- Flow 8: machine-readable + banner suppression --------------------------


def test_flow_machine_readable_and_banner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    _install_pipeline(monkeypatch)

    # --json is clean and parses; no banner/decoration leaks in.
    out = runner.invoke(
        app, ["--config", str(cfg), "--json", "scan", "SENT", "VALU"]
    ).output
    payload = json.loads(out)  # must parse
    assert "Tune out the noise." not in out  # banner never in machine output
    assert payload["results"]

    # The banner appears only on bare invocation / init - never before scan.
    bare = runner.invoke(app, [])
    assert "Usage" in bare.output  # non-TTY → help, banner suppressed
