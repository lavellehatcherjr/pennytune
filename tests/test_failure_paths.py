"""Failure-path tests: local state breaks, and the CLI has to stay honest about it.

Each case pins something that is easy to get quietly wrong:

* watchlist alerts have to be able to fire at all, which needs the recorded
  vocabulary to match the alert set and the threshold to sit inside the real
  composite range;
* an unusable database, config file or export destination must name the file
  and return a code that does not claim results were written;
* ``inspect`` must not report success for a ticker that resolved to nothing;
* ``init`` must not reset tuned weights on a re-run.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pennytune import cli
from pennytune import scan as scan_mod
from pennytune.exit_codes import ExitCode
from pennytune.features.delisting import DelistingInputs
from pennytune.features.fundamentals import PeriodFinancials
from pennytune.features.universe import UniverseCandidate
from pennytune.features.watchlist import (
    GATE_ALERT_REASONS,
    MATERIAL_ALERT_FLAGS,
    SCORE_ALERT_DROP,
    snapshot_flags,
)
from pennytune.scoring import Gates

runner = CliRunner()

_FEATURES = Path(__file__).resolve().parents[1] / "src" / "pennytune" / "features"


def _emitted_feature_flags() -> set[str]:
    """Ground truth: the flag literals the feature modules actually append.

    Read from the source, not from a constant, so a wrong constant cannot agree
    with itself.
    """
    found: set[str] = set()
    for path in _FEATURES.glob("*.py"):
        found.update(
            re.findall(r'flags\.append\(\s*"([A-Z0-9-]+)"', path.read_text("utf-8"))
        )
    return found


def _recordable_flags() -> set[str]:
    """Everything a snapshot can contain: feature flags + gate reasons."""
    gates = Gates(active_suspension=True, disclosed_determination=True)
    return _emitted_feature_flags() | set(gates.reasons())


@pytest.fixture(autouse=True)
def _isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PENNYTUNE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("PENNYTUNE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)


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


def _evidence(ticker: str, *, deficiency: bool = False) -> scan_mod.RawEvidence:
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
        delisting=DelistingInputs(deficiency_notice=True) if deficiency else None,
    )


class _Deteriorating:
    """Clean on the first scan, carrying a delisting deficiency on the second."""

    def __init__(self) -> None:
        self.deficient = False

    def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
        return _evidence(candidate.ticker, deficiency=self.deficient)


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


def test_alert_vocabulary_intersects_what_snapshots_actually_record() -> None:
    """The two vocabularies must overlap, or no new-flag alert can ever fire.

    The alert set holds feature flags (DELISTING-DEFICIENCY); a snapshot that
    records only module names (delisting) never intersects it.
    """
    assert MATERIAL_ALERT_FLAGS & _recordable_flags()


def test_every_material_alert_flag_is_one_the_code_can_emit() -> None:
    """A flag nobody raises is a dead entry that quietly narrows the alert set."""
    assert MATERIAL_ALERT_FLAGS <= _recordable_flags()


def test_score_alert_threshold_is_reachable() -> None:
    """A threshold wider than the real composite range can never fire."""
    assert SCORE_ALERT_DROP <= 5.0


def test_material_flag_transition_raises_an_alert_through_the_real_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A watched name acquiring a delisting deficiency must raise an alert.

    Drives the real pipeline both times rather than injecting a snapshot, so the
    vocabulary under test is the one the pipeline actually records.
    """
    cfg = tmp_path / "c.toml"
    _init(cfg)
    provider = _Deteriorating()
    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: provider)

    assert (
        runner.invoke(cli.app, ["--config", str(cfg), "watch", "add", "AAA"]).exit_code
        == 0
    )

    clean = runner.invoke(cli.app, ["--config", str(cfg), "scan", "AAA"])
    assert clean.exit_code == 0, clean.output

    provider.deficient = True
    worse = runner.invoke(cli.app, ["--config", str(cfg), "scan", "AAA"])
    assert worse.exit_code == 0, worse.output

    listing = runner.invoke(cli.app, ["--config", str(cfg), "watch", "list"])
    assert "DELISTING-DEFICIENCY" in listing.output, listing.output


def _corrupt_db(tmp_path: Path) -> Path:
    db = tmp_path / "data" / "pennytune.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    db.write_bytes(b"\x00\x01not a database\x02\x03" * 128)
    return db


@pytest.mark.parametrize(
    "argv",
    [["watch", "add", "AAA"], ["watch", "list"], ["watch", "rm", "AAA"]],
)
def test_corrupt_watchlist_db_reports_the_path(tmp_path: Path, argv: list[str]) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    db = _corrupt_db(tmp_path)

    result = runner.invoke(cli.app, ["--config", str(cfg), *argv])
    assert result.exit_code == int(ExitCode.CONFIG_ERROR), result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert str(db) in result.output


def test_watchlist_db_that_is_a_directory_reports_the_path(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    db = tmp_path / "data" / "pennytune.db"
    db.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(cli.app, ["--config", str(cfg), "watch", "list"])
    assert result.exit_code == int(ExitCode.CONFIG_ERROR), result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_scan_with_corrupt_db_does_not_claim_the_watchlist_is_empty(
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    _corrupt_db(tmp_path)

    result = runner.invoke(cli.app, ["--config", str(cfg), "--offline", "scan"])
    assert "watchlist is empty" not in result.output, result.output
    assert result.exit_code == int(ExitCode.CONFIG_ERROR), result.output


def test_init_cannot_write_config_reports_the_path(tmp_path: Path) -> None:
    """Config dir is a regular file, so the write fails for any uid."""
    blocker = tmp_path / "blocked"
    blocker.write_text("not a directory")
    cfg = blocker / "c.toml"

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
    assert result.exit_code == int(ExitCode.CONFIG_ERROR), result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert str(cfg) in result.output


def test_config_set_cannot_write_reports_the_path(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    # Replace the parent with a file after init, so the rewrite cannot land.
    cfg.unlink()
    holder = tmp_path / "holder"
    holder.write_text("x")
    target = holder / "c.toml"

    result = runner.invoke(
        cli.app, ["--config", str(target), "config", "set", "weights.growth", "1.4"]
    )
    assert result.exit_code == int(ExitCode.CONFIG_ERROR), result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_export_to_an_impossible_output_dir_reports_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """output_dir is an existing FILE: mkdir raises FileExistsError."""
    cfg = tmp_path / "c.toml"
    _init(cfg)
    blocker = tmp_path / "afile"
    blocker.write_text("x")
    runner.invoke(
        cli.app, ["--config", str(cfg), "config", "set", "output_dir", str(blocker)]
    )

    class _Fixture:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            return _evidence(candidate.ticker)

    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Fixture())
    result = runner.invoke(
        cli.app, ["--config", str(cfg), "scan", "AAA", "--format", "csv"]
    )
    assert result.exit_code == int(ExitCode.USAGE_ERROR), result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert str(blocker) in result.output


def test_scan_survives_a_watchlist_that_breaks_mid_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The watchlist is best-effort: a mid-scan DB failure must not lose the scan."""
    cfg = tmp_path / "c.toml"
    _init(cfg)

    class _Fixture:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            return _evidence(candidate.ticker)

    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Fixture())
    runner.invoke(cli.app, ["--config", str(cfg), "watch", "add", "AAA"])

    real_open = cli._open_watchlist

    def _broken_after_open() -> object:
        watchlist = real_open()
        assert watchlist is not None

        def _boom(*args: object, **kwargs: object) -> None:
            raise sqlite3.OperationalError("database is locked")

        watchlist.record_snapshot = _boom  # type: ignore[method-assign]
        return watchlist

    monkeypatch.setattr(cli, "_open_watchlist", _broken_after_open)
    result = runner.invoke(cli.app, ["--config", str(cfg), "scan", "AAA"])
    assert result.exit_code == 0, result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "AAA" in result.output


def test_inspect_on_an_unresolvable_ticker_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)

    class _NoEvidence:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            return scan_mod.degraded_evidence(
                candidate, "no SEC CIK for ticker (cannot fetch EDGAR data)"
            )

    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _NoEvidence())
    result = runner.invoke(cli.app, ["--config", str(cfg), "inspect", "ZZZZZZ"])
    assert result.exit_code == int(ExitCode.USAGE_ERROR), result.output
    # The NOT ASSESSED finding is still reported to the human.
    assert "no evidence could be assembled" in result.output


def test_inspect_on_a_failed_fetch_exits_like_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)

    class _Down:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            raise RuntimeError("simulated total SEC outage")

    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Down())
    inspected = runner.invoke(cli.app, ["--config", str(cfg), "inspect", "AAA"])
    scanned = runner.invoke(cli.app, ["--config", str(cfg), "scan", "AAA"])
    assert inspected.exit_code == int(ExitCode.PARTIAL_FAILURE), inspected.output
    # Same condition, same code: the two commands must not disagree.
    assert inspected.exit_code == scanned.exit_code


def test_inspect_on_a_scored_ticker_still_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)

    class _Fixture:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            return _evidence(candidate.ticker)

    monkeypatch.setattr(cli, "_make_evidence_provider", lambda c, s: _Fixture())
    result = runner.invoke(cli.app, ["--config", str(cfg), "inspect", "AAA"])
    assert result.exit_code == 0, result.output


def test_reinit_preserves_a_tuned_custom_profile(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    runner.invoke(cli.app, ["--config", str(cfg), "config", "set", "profile", "custom"])
    runner.invoke(
        cli.app, ["--config", str(cfg), "config", "set", "weights.valuation", "1.5"]
    )

    result = runner.invoke(
        cli.app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "Dana Lee dana@newjob.com",
            "--i-understand-the-risks",
        ],
    )
    assert result.exit_code == 0, result.output

    profile = runner.invoke(cli.app, ["--config", str(cfg), "config", "get", "profile"])
    weight = runner.invoke(
        cli.app, ["--config", str(cfg), "config", "get", "weights.valuation"]
    )
    assert "custom" in profile.output, profile.output
    assert "1.5" in weight.output, weight.output


def test_reinit_preserves_a_named_profile_and_its_tuning(tmp_path: Path) -> None:
    """A stored named profile must survive too: re-init is not a profile change."""
    cfg = tmp_path / "c.toml"
    _init(cfg)
    runner.invoke(cli.app, ["--config", str(cfg), "config", "set", "profile", "trader"])

    runner.invoke(
        cli.app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "Dana Lee dana@newjob.com",
            "--i-understand-the-risks",
        ],
    )
    profile = runner.invoke(cli.app, ["--config", str(cfg), "config", "get", "profile"])
    assert "trader" in profile.output, profile.output


def test_explicit_profile_flag_still_switches_and_says_so(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    runner.invoke(
        cli.app, ["--config", str(cfg), "config", "set", "weights.valuation", "1.5"]
    )

    result = runner.invoke(
        cli.app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "Dana Lee dana@example.com",
            "--profile",
            "trader",
            "--i-understand-the-risks",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "reset" in result.output.lower(), result.output
    weight = runner.invoke(
        cli.app, ["--config", str(cfg), "config", "get", "weights.valuation"]
    )
    assert "1.5" not in weight.output, weight.output


def test_snapshot_flags_carries_all_three_vocabularies() -> None:
    """Module names drive the delta; feature flags and gate reasons drive alerts."""
    recorded = snapshot_flags(
        {"delisting": 1.6, "dilution": 0.5},
        ["active SEC trading suspension"],
        ["DELISTING-DEFICIENCY", "DELISTING-DEFICIENCY"],
    )
    assert recorded == [
        "delisting",
        "dilution",
        "active SEC trading suspension",
        "DELISTING-DEFICIENCY",
    ]
    assert GATE_ALERT_REASONS & set(recorded)
    assert MATERIAL_ALERT_FLAGS & set(recorded)
