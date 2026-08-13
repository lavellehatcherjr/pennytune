"""CLI contract tests: side effects and exit codes must not vary by output mode.

Each case pins a way the surface can drift apart:

* the authorized-headroom flag must need a measured ceiling, not an 8-K item
  5.07, which is the annual shareholder meeting every issuer files;
* ``--json scan`` must still write its export and still return the
  partial-failure exit code;
* ``--format`` must be rejected before any fetching;
* ``inspect`` must strip its argument, as ``scan`` does;
* a config file with invalid UTF-8 must report its path, not a traceback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from pennytune import cli
from pennytune import scan as scan_mod
from pennytune.exit_codes import ExitCode
from pennytune.features.dilution import (
    CoverPageFacts,
    DilutionInputs,
    ShareCountPoint,
    authorized_headroom,
    authorized_shares_from_facts,
    compute_dilution,
)
from pennytune.features.events import build_event, build_event_tape
from pennytune.features.fundamentals import PeriodFinancials
from pennytune.features.universe import UniverseCandidate

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PENNYTUNE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("PENNYTUNE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)


def _tape(*items: str) -> Any:
    return build_event_tape(
        [build_event(str(i), "2026-01-01", "8-K", item) for i, item in enumerate(items)]
    )


def _series(*counts: float) -> list[ShareCountPoint]:
    return [
        ShareCountPoint(period_end=f"2026-0{i + 1}-01", shares=c)
        for i, c in enumerate(counts)
    ]


def test_annual_meeting_alone_does_not_flag_authorized_headroom() -> None:
    """An 8-K item 5.07 is the annual shareholder vote, not evidence of dilution.

    Essentially every issuer files one, so keying the flag off it fires on the
    whole market, Apple included.
    """
    profile = compute_dilution(
        DilutionInputs(share_series=_series(1_000_000.0), event_tape=_tape("5.07"))
    )
    assert "AUTHORIZED-HEADROOM-LOW" not in profile.flags


def test_charter_amendment_alone_does_not_flag_authorized_headroom() -> None:
    """5.03 covers any charter/bylaw amendment or fiscal-year change.

    Without a real authorized count there is no headroom to call low, so it
    must not raise the flag on its own either.
    """
    profile = compute_dilution(
        DilutionInputs(share_series=_series(1_000_000.0), event_tape=_tape("5.03"))
    )
    assert "AUTHORIZED-HEADROOM-LOW" not in profile.flags


def test_authorized_headroom_flags_only_when_actually_near_the_ceiling() -> None:
    near = compute_dilution(
        DilutionInputs(
            share_series=_series(95_000_000.0),
            cover=CoverPageFacts(authorized_shares=100_000_000.0),
        )
    )
    assert "AUTHORIZED-HEADROOM-LOW" in near.flags

    roomy = compute_dilution(
        DilutionInputs(
            share_series=_series(29_000_000.0),
            cover=CoverPageFacts(authorized_shares=100_000_000.0),
        )
    )
    assert "AUTHORIZED-HEADROOM-LOW" not in roomy.flags


def test_headroom_is_suppressed_when_authorized_is_not_credible() -> None:
    """Outstanding above authorized means stale or per-class tagging, not a ceiling."""
    headroom = authorized_headroom(1_000.0, 500_000_000.0, None)
    assert headroom.headroom_pct is None
    assert headroom.near_ceiling is False


def test_authorized_shares_read_from_companyfacts() -> None:
    facts = {
        "facts": {
            "us-gaap": {
                "CommonStockSharesAuthorized": {
                    "units": {
                        "shares": [
                            {"val": 1_000_000.0, "end": "2024-12-31"},
                            {"val": 2_000_000.0, "end": "2026-06-30"},
                        ]
                    }
                }
            }
        }
    }
    assert authorized_shares_from_facts(facts) == 2_000_000.0
    assert authorized_shares_from_facts({"facts": {}}) is None


def _period(scale: float = 1.0) -> PeriodFinancials:
    return PeriodFinancials(
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


def _evidence(ticker: str) -> scan_mod.RawEvidence:
    """Evidence rich enough to actually score, so an export has a row to write."""
    return scan_mod.RawEvidence(
        ticker=ticker,
        sic_sector="3674",
        sic_code=3674,
        market_cap=2_000.0,
        current_price=0.5,
        period_t=_period(),
        period_t1=_period(0.85),
        revenue_growth=0.20,
        sentiment_compound=0.10,
    )


class _Fixture:
    def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
        return _evidence(candidate.ticker)


class _AlwaysFails:
    def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
        raise RuntimeError("simulated total SEC outage")


def _init(cfg: Path) -> None:
    result = runner.invoke(
        cli.app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "Dana Lee dana@example.com",
            "--i-understand-the-risks",
        ],
    )
    assert result.exit_code == 0, result.output


def test_json_scan_still_writes_the_export_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    out = tmp_path / "out"
    _init(cfg)
    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Fixture())
    runner.invoke(
        cli.app, ["--config", str(cfg), "config", "set", "output_dir", str(out)]
    )

    result = runner.invoke(
        cli.app, ["--config", str(cfg), "--json", "scan", "AAA", "--format", "csv"]
    )
    assert result.exit_code == 0, result.output
    assert list(out.glob("scan_*.csv")), "--json scan --format csv wrote no file"


def test_json_scan_stdout_stays_parseable_after_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 'Wrote ...' line must never contaminate the JSON payload."""
    cfg = tmp_path / "c.toml"
    out = tmp_path / "out"
    _init(cfg)
    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Fixture())
    runner.invoke(
        cli.app, ["--config", str(cfg), "config", "set", "output_dir", str(out)]
    )

    result = runner.invoke(
        cli.app, ["--config", str(cfg), "--json", "scan", "AAA", "--format", "csv"]
    )
    assert result.exit_code == 0, result.output
    json.loads(result.stdout)


def test_json_scan_exits_nonzero_on_total_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _AlwaysFails())

    result = runner.invoke(cli.app, ["--config", str(cfg), "--json", "scan", "AAA"])
    payload = json.loads(result.stdout)
    assert payload["meta"]["partial_failure"] is True
    assert result.exit_code == int(ExitCode.PARTIAL_FAILURE)


def test_invalid_format_is_rejected_before_any_fetching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--format must be validated up front like --sort, not after the scan."""
    cfg = tmp_path / "c.toml"
    _init(cfg)

    called: list[str] = []

    class _Tracking:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            called.append(candidate.ticker)
            return _evidence(candidate.ticker)

    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Tracking())
    result = runner.invoke(
        cli.app, ["--config", str(cfg), "scan", "AAA", "--format", "xlsx"]
    )
    assert result.exit_code == int(ExitCode.USAGE_ERROR)
    assert not called, "the scan ran before --format was validated"


def test_invalid_format_is_rejected_under_json_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Fixture())
    result = runner.invoke(
        cli.app, ["--config", str(cfg), "--json", "scan", "AAA", "--format", "xlsx"]
    )
    assert result.exit_code == int(ExitCode.USAGE_ERROR)


def test_verbose_names_the_reason_a_ticker_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _AlwaysFails())

    quiet = runner.invoke(cli.app, ["--config", str(cfg), "scan", "AAA"])
    loud = runner.invoke(cli.app, ["--config", str(cfg), "--verbose", "scan", "AAA"])

    assert "simulated total SEC outage" not in quiet.output
    assert "simulated total SEC outage" in loud.output
    assert loud.output != quiet.output


def test_inspect_strips_surrounding_whitespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Fixture())

    clean = runner.invoke(cli.app, ["--config", str(cfg), "inspect", "AAA"])
    padded = runner.invoke(cli.app, ["--config", str(cfg), "inspect", "  AAA  "])
    assert clean.exit_code == padded.exit_code == 0
    assert padded.output == clean.output


def test_invalid_utf8_config_reports_the_path_without_a_traceback(
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "bad.toml"
    cfg.write_bytes(
        b'edgar_identity = "\xff\xfe not utf-8"\nrisk_acknowledged = true\n'
    )

    for argv in (
        ["config", "get", "profile"],
        ["--offline", "scan", "AAA"],
        ["--offline", "inspect", "AAA"],
        ["config", "set", "weights.growth", "1.1"],
    ):
        result = runner.invoke(cli.app, ["--config", str(cfg), *argv])
        assert result.exit_code == int(ExitCode.CONFIG_ERROR), (argv, result.output)
        assert result.exception is None or isinstance(result.exception, SystemExit), (
            argv,
            result.exception,
        )
        assert str(cfg) in result.output
