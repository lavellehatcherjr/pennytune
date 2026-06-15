"""Full-CLI tests: banner, init gate, screens, exit codes, --json."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from pennytune import banner
from pennytune.cli import app
from pennytune.disclaimer import FULL_DISCLAIMER

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every CLI test hermetic: config/cache/data land under tmp, not $HOME."""
    monkeypatch.setenv("PENNYTUNE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("PENNYTUNE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PENNYTUNE_DATA_DIR", str(tmp_path / "data"))


# ---- banner -----------------------------------------------------------------


def test_should_show_banner_logic() -> None:
    assert banner.should_show_banner(
        is_tty=True, no_color=False, quiet=False, json_output=False
    )
    assert not banner.should_show_banner(
        is_tty=False, no_color=False, quiet=False, json_output=False
    )
    assert not banner.should_show_banner(
        is_tty=True, no_color=True, quiet=False, json_output=False
    )
    assert not banner.should_show_banner(
        is_tty=True, no_color=False, quiet=True, json_output=False
    )
    assert not banner.should_show_banner(
        is_tty=True, no_color=False, quiet=False, json_output=True
    )


def test_render_banner_content_plain() -> None:
    out = banner.render_banner(no_color=True)
    assert "Tune out the noise." in out
    assert "not investment advice" in out
    assert "\x1b[" not in out  # no ANSI when color disabled


def test_bare_invocation_shows_help_banner_suppressed_in_non_tty() -> None:
    # CliRunner stdout is not a TTY → banner suppressed; help shown.
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert (
        "Research tool — not investment advice." not in result.output
    )  # banner reminder absent


# ---- init gate + exit codes -------------------------------------------------


def test_scan_blocked_before_init_then_allowed(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    before = runner.invoke(app, ["--config", str(cfg), "scan"])
    assert before.exit_code == 3  # config error: not initialized
    setup = runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "Dana Lee dana@example.com",
            "--i-understand-the-risks",
        ],
    )
    assert setup.exit_code == 0, setup.output
    # --offline → no network; empty cache degrades to an empty (valid) result.
    after = runner.invoke(app, ["--config", str(cfg), "--offline", "scan", "AAA"])
    assert after.exit_code == 0, after.output


def test_init_requires_identity_when_non_interactive(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    result = runner.invoke(
        app, ["--config", str(cfg), "--yes", "init", "--i-understand-the-risks"]
    )
    assert result.exit_code == 3


def test_init_requires_acknowledgment(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    result = runner.invoke(
        app, ["--config", str(cfg), "--yes", "init", "--identity", "X x@y.com"]
    )
    assert result.exit_code == 3


def test_init_rejects_malformed_identity(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    # A name-only / email-less identity is a non-compliant SEC User-Agent.
    result = runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "foo",
            "--i-understand-the-risks",
        ],
    )
    assert result.exit_code == 3
    assert "email" in result.output.lower()


def test_bad_flag_is_usage_error() -> None:
    assert runner.invoke(app, ["--nonexistent-flag"]).exit_code == 2


# ---- --json clean -----------------------------------------------------------


def test_scan_json_is_clean_and_parses(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "X x@y.com",
            "--i-understand-the-risks",
        ],
    )
    result = runner.invoke(
        app, ["--config", str(cfg), "--offline", "--json", "scan", "AAA"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "_disclaimer" in payload
    assert "results" in payload
    assert "meta" in payload  # preset/profile/freshness/failures metadata


# ---- sources / cache / watch screens ----------------------------------------


def test_sources_lists_no_key_providers() -> None:
    result = runner.invoke(app, ["sources"])
    assert result.exit_code == 0
    assert "SEC EDGAR" in result.output
    assert "no API keys" in result.output
    assert "GDELT" not in result.output  # news/GDELT removed → SEC EDGAR only
    payload = json.loads(runner.invoke(app, ["--json", "sources"]).output)
    assert "sources" in payload


def test_watch_add_list_rm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PENNYTUNE_DATA_DIR", str(tmp_path))
    assert runner.invoke(app, ["watch", "add", "grow", "nukk"]).exit_code == 0
    listed = runner.invoke(app, ["watch", "list"])
    assert "GROW" in listed.output
    assert "NUKK" in listed.output
    assert runner.invoke(app, ["watch", "rm", "grow"]).exit_code == 0
    assert "GROW" not in runner.invoke(app, ["watch", "list"]).output


def test_scan_carries_due_diligence_note(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "X x@y.com",
            "--i-understand-the-risks",
        ],
    )
    result = runner.invoke(app, ["--config", str(cfg), "--offline", "scan", "AAA"])
    assert result.exit_code == 0, result.output
    assert "due diligence" in result.output.lower()
    assert "tradeability" in result.output.lower()


def _init(cfg: Path) -> None:
    runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "X x@y.com",
            "--i-understand-the-risks",
        ],
    )


# ---- disclaimer surfacing: acknowledgment gate + footers --------------------


def test_interactive_init_displays_full_disclaimer_before_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the interactive path (CliRunner stdin is not a TTY); identity and
    # profile come from flags so the only prompt is the risk acknowledgment.
    monkeypatch.setattr("pennytune.cli._interactive", lambda state: True)
    cfg = tmp_path / "c.toml"
    result = runner.invoke(
        app,
        ["--config", str(cfg), "init", "--identity", "X x@y.com", "--profile", "hold"],
        input="I UNDERSTAND\n",
    )
    assert result.exit_code == 0, result.output
    # The COMPLETE text is shown before acknowledgment, not a summary/pointer.
    assert FULL_DISCLAIMER in result.output
    assert "14. ACCEPTANCE." in result.output


def test_interactive_init_shows_disclaimer_even_when_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("pennytune.cli._interactive", lambda state: True)
    cfg = tmp_path / "c.toml"
    result = runner.invoke(
        app,
        ["--config", str(cfg), "init", "--identity", "X x@y.com", "--profile", "hold"],
        input="no thanks\n",
    )
    assert result.exit_code == 3  # displayed, but the user did not acknowledge
    assert FULL_DISCLAIMER in result.output


def test_flag_setup_emits_affirmation_not_silent(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    result = runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "X x@y.com",
            "--i-understand-the-risks",
        ],
    )
    assert result.exit_code == 0, result.output
    # The flag path affirms the acknowledgment and points at the full text
    # rather than silently flipping the bit.
    assert "--i-understand-the-risks" in result.output
    assert "pennytune disclaimer" in result.output
    assert "NOT investment advice" in result.output


def test_quiet_inspect_still_carries_short_disclaimer(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    result = runner.invoke(
        app, ["--config", str(cfg), "--offline", "--quiet", "inspect", "AAA"]
    )
    assert result.exit_code == 0, result.output
    # Even under --quiet, no human-readable analysis output omits the one-liner.
    assert "Not investment advice" in result.output


def test_scan_offline_makes_no_network_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pennytune.providers.http import SafeHttpClient

    cfg = tmp_path / "c.toml"
    _init(cfg)

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("network call attempted under --offline")

    monkeypatch.setattr(SafeHttpClient, "get_json", _boom)
    result = runner.invoke(app, ["--config", str(cfg), "--offline", "scan", "AAA"])
    assert result.exit_code == 0, result.output  # zero network → graceful empty


def test_scan_renders_table_and_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pennytune import cli
    from pennytune import scan as scan_mod
    from pennytune.features.universe import UniverseCandidate

    cfg = tmp_path / "c.toml"
    out = tmp_path / "out"
    _init(cfg)
    runner.invoke(app, ["--config", str(cfg), "config", "set", "output_dir", str(out)])

    class _FixtureProvider:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            return scan_mod.RawEvidence(
                ticker=candidate.ticker,
                sic_sector="3674",
                sic_code=3674,
                market_cap=60_000_000.0,
                revenue_growth=0.30 if candidate.ticker == "AAA" else 0.10,
                sentiment_compound=0.5,
            )

    monkeypatch.setattr(
        cli, "_make_evidence_provider", lambda config, state: _FixtureProvider()
    )

    result = runner.invoke(
        app, ["--config", str(cfg), "scan", "AAA", "BBB", "--top", "5"]
    )
    assert result.exit_code == 0, result.output
    assert "AAA" in result.output
    assert "Wrote" in result.output
    assert list(out.glob("scan_*.csv"))  # full set exported


def test_inspect_renders_breakdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pennytune import cli
    from pennytune import scan as scan_mod
    from pennytune.features.universe import UniverseCandidate

    cfg = tmp_path / "c.toml"
    _init(cfg)

    class _FixtureProvider:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            return scan_mod.RawEvidence(
                ticker=candidate.ticker,
                sic_sector="3674",
                sic_code=3674,
                revenue_growth=0.2,
                sentiment_compound=0.3,
            )

    monkeypatch.setattr(
        cli, "_make_evidence_provider", lambda config, state: _FixtureProvider()
    )
    result = runner.invoke(app, ["--config", str(cfg), "inspect", "aaa"])
    assert result.exit_code == 0, result.output
    assert "AAA" in result.output
    assert "composite" in result.output.lower()


def test_inspect_json_outputs_breakdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pennytune import cli
    from pennytune import scan as scan_mod
    from pennytune.features.universe import UniverseCandidate

    cfg = tmp_path / "c.toml"
    _init(cfg)

    class _FixtureProvider:
        def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
            return scan_mod.RawEvidence(
                ticker=candidate.ticker,
                sic_sector="3674",
                sic_code=3674,
                revenue_growth=0.2,
                sentiment_compound=0.3,
            )

    monkeypatch.setattr(
        cli, "_make_evidence_provider", lambda config, state: _FixtureProvider()
    )
    result = runner.invoke(app, ["--config", str(cfg), "--json", "inspect", "aaa"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["inspect"]["ticker"] == "AAA"
    assert "_disclaimer" in payload
    assert "Tune out the noise." not in result.output  # no banner in machine output


def test_scan_quiet_suppresses_decoration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pennytune import cli
    from pennytune import scan as scan_mod
    from pennytune.features.universe import UniverseCandidate

    cfg = tmp_path / "c.toml"
    _init(cfg)

    class _FixtureProvider:
        def gather(self, c: UniverseCandidate) -> scan_mod.RawEvidence:
            return scan_mod.RawEvidence(
                ticker=c.ticker, sic_sector="3674", sic_code=3674, revenue_growth=0.2
            )

    monkeypatch.setattr(
        cli, "_make_evidence_provider", lambda config, state: _FixtureProvider()
    )
    result = runner.invoke(app, ["--config", str(cfg), "--quiet", "scan", "AAA"])
    assert result.exit_code == 0, result.output
    assert "Universe " not in result.output  # freshness header decoration suppressed
    assert "ranked candidates" not in result.output  # table title suppressed


def test_scan_flags_map_to_request_and_filters() -> None:
    from pennytune import cli
    from pennytune.cli import GlobalState
    from pennytune.config import load_config

    cfg = load_config()  # default hold/penny
    state = GlobalState(profile="trader")  # global --profile override
    request, filters, preset_name = cli._resolve_scan_config(
        cfg,
        state,
        preset="broad",
        exchange="nasdaq",
        top=25,
        sort="growth",
        exclude_flagged=True,
        require_insider_buying=True,
    )
    assert preset_name == "broad"
    assert request.profile_name == "trader"  # --profile wins over the saved hold
    assert request.top_n == 25 and request.sort == "growth"
    assert request.exclude_flagged and request.require_insider_buying
    assert filters.exchange == "nasdaq"  # the only universe filter
    # The broad preset weights the up-market risk modules in.
    assert request.preset_bundle["goodwill_impairment"] > 0


def test_scan_bad_sort_is_usage_error(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    _init(cfg)
    result = runner.invoke(
        app, ["--config", str(cfg), "--offline", "scan", "--sort", "bogus"]
    )
    assert result.exit_code == 2  # invalid --sort → usage error


# ---- evidence provider wiring (live fundamentals + dilution + SIC) ----------
#
# These exercise the provider selection + the composed live mapping with stubs,
# so they make no network calls.


class _StubClient:
    """A SafeHttpClient stand-in; get_json returns a canned payload (or errors)."""

    def __init__(self, payload: Any = None) -> None:
        self._payload = payload
        self.closed = False

    def get_json(self, url: str, **kwargs: Any) -> Any:
        if self._payload is None:
            raise AssertionError("unexpected network fetch")
        return self._payload

    def close(self) -> None:
        self.closed = True


# Minimal companyfacts with one fiscal year so the real parser yields a period.
_CF_ONE_FY: dict[str, Any] = {
    "entityName": "Full Co",
    "facts": {
        "us-gaap": {
            "Assets": {
                "units": {
                    "USD": [
                        {
                            "end": "2024-12-31",
                            "val": 1_000_000,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2025-02-01",
                        }
                    ]
                }
            },
            "Revenues": {
                "units": {
                    "USD": [
                        {
                            "start": "2024-01-01",
                            "end": "2024-12-31",
                            "val": 500_000,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2025-02-01",
                        }
                    ]
                }
            },
        }
    },
}


class _StubFundamentals:
    """Stands in for EdgarFundamentalsProvider.fetch_companyfacts."""

    def __init__(
        self, companyfacts: Any = None, error: Exception | None = None
    ) -> None:
        self._companyfacts = {} if companyfacts is None else companyfacts
        self._error = error
        self.cik: str | None = None

    def fetch_companyfacts(self, cik: str) -> Any:
        self.cik = cik
        if self._error is not None:
            raise self._error
        return self._companyfacts


class _StubDilution:
    """Stands in for EdgarDilutionProvider (submissions fetch + assembler)."""

    def __init__(self, evidence: Any, submissions: Any = None) -> None:
        self._evidence = evidence
        self._submissions = (
            submissions if submissions is not None else {"filings": {"recent": {}}}
        )
        self.cik: str | None = None
        self.revenue: Any = "unset"
        self.submissions_arg: Any = "unset"
        self.event_tape_arg: Any = "unset"

    def fetch_submissions(self, cik: str) -> Any:
        return self._submissions

    def get_dilution_evidence(
        self,
        cik: str,
        *,
        companyfacts: Any,
        submissions: Any,
        revenue: Any = None,
        now: Any = None,
        event_tape: Any = None,
    ) -> Any:
        self.cik = cik
        self.revenue = revenue
        self.submissions_arg = submissions
        self.event_tape_arg = event_tape
        return self._evidence


class _StubInsider:
    """Stands in for EdgarInsiderProvider.get_insider_evidence."""

    def __init__(self, evidence: Any) -> None:
        self._evidence = evidence
        self.cik: str | None = None
        self.submissions_arg: Any = "unset"

    def get_insider_evidence(
        self, cik: str, *, submissions: Any, now: Any = None
    ) -> Any:
        self.cik = cik
        self.submissions_arg = submissions
        return self._evidence


def _dilution_evidence(**kwargs: Any) -> Any:
    from pennytune.features.dilution import DilutionEvidence, DilutionInputs, FilingRef

    defaults: dict[str, Any] = {
        "inputs": DilutionInputs(filings=[FilingRef("S-3", "2026-01-02", "a1")]),
        "sic_code": 2836,
        "sic_sector": "Biological Products",
        "completeness": [],
    }
    defaults.update(kwargs)
    return DilutionEvidence(**defaults)


def _insider_evidence(**kwargs: Any) -> Any:
    from pennytune.features.insider import InsiderEvidence, InsiderTransaction

    defaults: dict[str, Any] = {
        "transactions": (
            InsiderTransaction(
                insider="CEO", code="P", shares=1000.0, value=5000.0, date="2026-01-10"
            ),
        ),
        "form144s": (),
        "ownership_filings": (),
        "completeness": [],
    }
    defaults.update(kwargs)
    return InsiderEvidence(**defaults)


class _StubSuspensions:
    """Stands in for EdgarSuspensionProvider.get_halt_evidence."""

    def __init__(self, evidence: Any) -> None:
        self._evidence = evidence
        self.ticker: str | None = None
        self.company: Any = None

    def get_halt_evidence(self, ticker: str, company: str, *, now: Any = None) -> Any:
        self.ticker = ticker
        self.company = company
        return self._evidence


def _halt_evidence(**kwargs: Any) -> Any:
    from pennytune.features.halts import HaltEvidence, HaltProfile

    defaults: dict[str, Any] = {"halt": HaltProfile(tier="none"), "completeness": []}
    defaults.update(kwargs)
    return HaltEvidence(**defaults)


class _StubFtd:
    """Stands in for EdgarFtdProvider.get_ftd_evidence."""

    def __init__(self, evidence: Any) -> None:
        self._evidence = evidence
        self.ticker: str | None = None

    def get_ftd_evidence(self, ticker: str, *, now: Any = None) -> Any:
        self.ticker = ticker
        return self._evidence


def _ftd_evidence(**kwargs: Any) -> Any:
    from pennytune.features.short_interest import FtdContext, FtdEvidence

    defaults: dict[str, Any] = {
        "ftd": FtdContext(present=False),
        "period": "202605a",
        "completeness": [],
    }
    defaults.update(kwargs)
    return FtdEvidence(**defaults)


def test_make_evidence_provider_offline_or_no_identity_is_degrading() -> None:
    from pennytune import cli
    from pennytune.config import default_config

    # Offline → degrading (no network), even with an identity configured.
    cfg = default_config()
    cfg.edgar_identity = "Dana Lee dana@example.com"
    offline = cli._make_evidence_provider(cfg, cli.GlobalState(offline=True))
    assert isinstance(offline, cli._DegradingEvidenceProvider)
    # Online but no identity → still degrading (the init gate also blocks this).
    no_id = cli._make_evidence_provider(
        default_config(), cli.GlobalState(offline=False)
    )
    assert isinstance(no_id, cli._DegradingEvidenceProvider)


def test_make_evidence_provider_online_is_live_and_uses_identity() -> None:
    from pennytune import cli
    from pennytune.config import default_config

    cfg = default_config()
    cfg.edgar_identity = "Dana Lee dana@example.com"
    provider = cli._make_evidence_provider(cfg, cli.GlobalState(offline=False))
    assert isinstance(provider, cli._LiveEvidenceProvider)
    # The configured identity is the on-the-wire User-Agent of the live client.
    assert provider._client._user_agent == "Dana Lee dana@example.com"
    provider.close()


def test_live_provider_maps_fundamentals_dilution_sic_insider_and_events() -> None:
    from datetime import UTC, datetime, timedelta

    from pennytune import cli
    from pennytune.features.universe import UniverseCandidate

    # Clock-independent recent dates so the 8-K signals fall inside the window.
    today = datetime.now(UTC).date()
    d1 = (today - timedelta(days=10)).isoformat()
    d2 = (today - timedelta(days=20)).isoformat()
    submissions = {
        "sic": "1",
        "filings": {
            "recent": {
                "form": ["8-K", "8-K", "10-Q"],
                "filingDate": [d1, d2, d2],
                "accessionNumber": ["e1", "e2", "e3"],
                "items": ["3.01,9.01", "4.02", ""],  # delisting + restatement
            }
        },
    }
    fundamentals = _StubFundamentals(_CF_ONE_FY)
    dil_ev = _dilution_evidence(
        completeness=["SIC suppressed (submissions carry no SIC)"]
    )
    dilution = _StubDilution(dil_ev, submissions=submissions)
    ins_ev = _insider_evidence()
    insider = _StubInsider(ins_ev)
    halt_ev = _halt_evidence()
    suspensions = _StubSuspensions(halt_ev)
    from pennytune.features.short_interest import FtdContext

    ftd_ev = _ftd_evidence(
        ftd=FtdContext(present=True, total_fails=5000.0, window_count=2)
    )
    ftd = _StubFtd(ftd_ev)
    stubs = (fundamentals, dilution, insider, suspensions, ftd, _StubClient())
    provider = cli._LiveEvidenceProvider(*stubs)  # type: ignore[arg-type]
    ev = provider.gather(UniverseCandidate("AAA", "AAA", "0000000001", "Nasdaq"))

    # fundamentals = live (real parser ran over the companyfacts)
    assert ev.period_t is not None and ev.period_t.total_assets == 1_000_000
    # dilution + SIC = live
    assert ev.dilution is dil_ev.inputs
    assert ev.sic_code == 2836 and ev.sic_sector == "Biological Products"
    assert dilution.cik == "0000000001" and dilution.revenue == 500_000
    # insider = live, code-P buy maps through
    assert ev.insider_transactions is ins_ev.transactions
    assert ev.insider_transactions[0].code == "P"
    # 8-K events = live: the tape carries the red-flag signals
    assert ev.event_tape is not None
    assert ev.event_tape.signals.has_delisting_notice is True  # 3.01
    assert ev.event_tape.signals.auditor_or_restatement_count == 1  # 4.02
    # 3.01 → delisting (fed the SAME tape), and the tape un-gates dilution
    assert ev.delisting is not None and ev.delisting.event_tape is ev.event_tape
    assert dilution.event_tape_arg is ev.event_tape
    assert any("red-flag 8-K items" in note for note in ev.completeness)
    # trading-suspension check = live, matched by the companyfacts company name
    assert ev.halt is halt_ev.halt
    assert suspensions.ticker == "AAA" and suspensions.company == "Full Co"
    # fails-to-deliver = live CONTEXT (matched by symbol), surfaced not scored
    assert ev.ftd is ftd_ev.ftd and ev.ftd.present is True
    assert ftd.ticker == "AAA"
    assert any("fails-to-deliver context" in note for note in ev.completeness)
    # the SAME submissions payload is shared by all three live slices (one fetch)
    assert dilution.submissions_arg is insider.submissions_arg
    assert ev.market_cap is None  # still no live price (news/GDELT removed)


def test_live_provider_degrades_when_companyfacts_unavailable() -> None:
    from pennytune import cli
    from pennytune.features.universe import UniverseCandidate
    from pennytune.providers.base import ProviderError

    fundamentals = _StubFundamentals(error=ProviderError("HTTP 404 from companyfacts"))
    dilution = _StubDilution(_dilution_evidence())
    insider = _StubInsider(_insider_evidence())
    suspensions = _StubSuspensions(_halt_evidence())
    ftd = _StubFtd(_ftd_evidence())
    stubs = (fundamentals, dilution, insider, suspensions, ftd, _StubClient())
    provider = cli._LiveEvidenceProvider(*stubs)  # type: ignore[arg-type]
    ev = provider.gather(UniverseCandidate("ZZZ", "ZZZ", "0000000009", "Nasdaq"))
    assert ev.period_t is None  # suppressed, not fabricated
    assert ev.dilution is None and ev.sic_code is None  # whole name degraded
    assert ev.insider_transactions == () and ev.halt is None and ev.ftd is None
    # nothing attempted once companyfacts failed
    assert dilution.cik is None and insider.cik is None
    assert suspensions.ticker is None and ftd.ticker is None
    assert any("companyfacts unavailable" in note for note in ev.completeness)


def test_live_provider_resolves_cik_via_sec_map_for_inspect() -> None:
    from pennytune import cli
    from pennytune.features.universe import UniverseCandidate

    fundamentals = _StubFundamentals(_CF_ONE_FY)
    dilution = _StubDilution(_dilution_evidence())
    insider = _StubInsider(_insider_evidence())
    suspensions = _StubSuspensions(_halt_evidence())
    ftd = _StubFtd(_ftd_evidence())
    # inspect builds a candidate with no CIK → resolve via the SEC exchange map.
    sec_map = {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [[1, "Apple", "AAA", "Nasdaq"]],
    }
    stubs = (
        fundamentals,
        dilution,
        insider,
        suspensions,
        ftd,
        _StubClient(sec_map),
    )
    provider = cli._LiveEvidenceProvider(*stubs)  # type: ignore[arg-type]
    ev = provider.gather(UniverseCandidate("aaa", "aaa"))  # lower-case, no CIK
    assert fundamentals.cik == "0000000001"  # resolved + zero-padded
    assert ev.period_t is not None and ev.sic_code == 2836
    assert insider.cik == "0000000001"
    # suspension matched by entityName; FTD keyed by ticker
    assert suspensions.company == "Full Co" and ftd.ticker == "aaa"


def test_live_provider_degrades_when_ticker_has_no_cik() -> None:
    from pennytune import cli
    from pennytune.features.universe import UniverseCandidate

    fundamentals = _StubFundamentals(_CF_ONE_FY)
    dilution = _StubDilution(_dilution_evidence())
    insider = _StubInsider(_insider_evidence())
    suspensions = _StubSuspensions(_halt_evidence())
    ftd = _StubFtd(_ftd_evidence())
    empty_map = {"fields": ["cik", "name", "ticker", "exchange"], "data": []}
    stubs = (
        fundamentals,
        dilution,
        insider,
        suspensions,
        ftd,
        _StubClient(empty_map),
    )
    provider = cli._LiveEvidenceProvider(*stubs)  # type: ignore[arg-type]
    ev = provider.gather(UniverseCandidate("NOPE", "NOPE"))
    assert ev.period_t is None and ev.dilution is None
    assert fundamentals.cik is None  # never fetched without a CIK
    assert insider.cik is None and suspensions.ticker is None and ftd.ticker is None
    assert any("no SEC CIK" in note for note in ev.completeness)
