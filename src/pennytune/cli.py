"""PennyTune command-line interface.

Wires the Typer application, the global flags, the startup banner, and every
command screen. ``init`` collects only the SEC EDGAR identity, a default
strategy profile, and the risk acknowledgment - there are NO API keys anywhere
(init records only the EDGAR identity and the acknowledgment, never keys).
``scan``/``inspect`` refuse to run until the identity and acknowledgment exist
(exit 3), then drive the end-to-end pipeline: ``scan`` builds the universe
and runs :func:`pennytune.scan.run_scan` (evidence, signals, scoring) with the
resolved ``--preset`` / ``--profile`` and the scan filter flags, rendering the
data-freshness header, the watchlist banner, the ranked table, and exporting
the full set; ``inspect`` renders one ticker's decomposed score. The universe
degrades to a valid empty result on outage/offline (graceful
degradation when offline); the evidence provider is injectable -
all evidence categories are fetched live from SEC EDGAR - fundamentals,
dilution, SIC, insider, 8-K events, trading-suspensions and fails-to-deliver
(companyfacts + submissions + full-text + Form 4/5 XML + the suspension list +
the FTD bulk file) - while ``--offline`` falls back to the degrading provider
entirely.

Note: ``from __future__ import annotations`` is intentionally NOT used (Typer
resolves parameter hints at runtime; concrete ``Annotated[...]`` is most robust).
"""

import json
import sqlite3
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from importlib import metadata
from pathlib import Path
from typing import Annotated, Any, cast

import typer
from pydantic import ValidationError

from pennytune import __version__, banner, output, paths
from pennytune import scan as scan_mod
from pennytune.config import (
    Config,
    Filters,
    apply_preset,
    apply_profile,
    flatten,
    get_value,
    load_config,
    redact_identity,
    save_config,
    set_value,
    validate_edgar_identity,
)
from pennytune.disclaimer import EXPORT_HEADER, FULL_DISCLAIMER, SHORT_DISCLAIMER
from pennytune.exit_codes import ExitCode
from pennytune.features.delisting import DelistingInputs
from pennytune.features.dilution import EdgarDilutionProvider, parse_efts_hits
from pennytune.features.events import (
    EventTape,
    build_event_tape,
    comment_letter_activity,
    parse_submissions_8k_events,
)
from pennytune.features.fundamentals import (
    EdgarFundamentalsProvider,
    period_financials_from_companyfacts,
)
from pennytune.features.halts import EdgarSuspensionProvider
from pennytune.features.insider import EdgarInsiderProvider
from pennytune.features.short_interest import EdgarFtdProvider, FtdEvidence
from pennytune.features.universe import (
    SEC_UNIVERSE_URL,
    EdgarListing,
    UniverseCandidate,
    parse_edgar_exchange_map,
)
from pennytune.features.watchlist import Watchlist
from pennytune.profiles import get_profile
from pennytune.providers.base import ProviderError
from pennytune.providers.http import SafeHttpClient
from pennytune.ratelimit import RateLimiter
from pennytune.scan import NOT_ASSESSED_REASON, ScanReport, ScanRequest, run_scan
from pennytune.scoring import POSITIVE_KEYS


def _force_utf8_streams() -> None:
    """Make stdout/stderr encode as UTF-8 so the non-ASCII characters used in
    the UI and the disclaimer never raise ``UnicodeEncodeError`` on a cp1252
    (Windows) console.

    Called at import time so it is in effect for every entry path - the
    ``pennytune`` console script (``pennytune.cli:app``), ``python -m
    pennytune``, and the eager ``--version`` / ``--disclaimer`` options that run
    before the Typer callback body. Guarded with ``getattr`` because pytest's
    captured streams may not expose ``reconfigure``.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


_force_utf8_streams()

__all__ = ["app", "main"]

DUE_DILIGENCE_NOTE = (
    "PennyTune surfaces SEC-filing evidence for your own due diligence; it does "
    "not fetch live prices, assess tradeability (bid-ask spread, liquidity), or "
    "evaluate intraday trading-halt status. Verify current price, tradeability, "
    "and halt status yourself in a brokerage."
)

# Shown on the non-interactive `--i-understand-the-risks` setup path so the flag
# never silently flips the acknowledgment bit: it affirms what is being accepted
# and points at the full text (interactive setup displays it in full instead).
RISK_FLAG_AFFIRMATION = (
    "================================================================\n"
    "RISK ACKNOWLEDGMENT (--i-understand-the-risks)\n"
    "By passing --i-understand-the-risks you affirm that you have read\n"
    "and agree to the full PennyTune disclaimer (all 14 sections): a\n"
    "research/educational tool only, NOT investment advice; penny stocks\n"
    "carry extreme risk up to TOTAL LOSS; third-party data may be\n"
    "inaccurate or delayed; verify against primary sources; use entirely\n"
    "at your own risk.\n"
    "Read the complete disclaimer any time:  pennytune disclaimer\n"
    "================================================================"
)

# Lookback for the continued-listing full-text probe. Matches the 8-K event
# tape's own recency window so the two delisting routes agree on "recent".
_DELISTING_FTS_DAYS = 180

_CORE_DEPENDENCIES: tuple[str, ...] = (
    "pandas",
    "numpy",
    "pyarrow",
    "edgartools",
    "typer",
    "rich",
    "pyfiglet",
    "pydantic",
    "platformdirs",
    "tomli-w",
    "pyrate-limiter",
    "tenacity",
    "defusedxml",
    "requests",
)

# Provider table for `sources` (all no-key, per the data-source policy).
_SOURCES: tuple[dict[str, str], ...] = (
    {
        "source": "SEC EDGAR",
        "role": "universe + fundamentals/filings/insider",
        "key": "n/a (User-Agent)",
        "limit": "10 req/sec",
        "domains": "data.sec.gov, efts.sec.gov, www.sec.gov",
    },
    {
        "source": "SEC FTD/suspensions",
        "role": "fails-to-deliver / trading suspensions",
        "key": "n/a",
        "limit": "twice-monthly / as-published",
        "domains": "sec.gov",
    },
)


@dataclass
class GlobalState:
    """Global flags, parsed once and shared via the Typer context."""

    profile: str | None = None
    config_path: str | None = None
    offline: bool = False
    json_output: bool = False
    quiet: bool = False
    yes: bool = False
    no_color: bool = False
    verbose: bool = False


def _format_versions() -> str:
    lines = [f"PennyTune {__version__}", "", "Pinned dependencies:"]
    for dist in _CORE_DEPENDENCIES:
        try:
            installed = metadata.version(dist)
        except metadata.PackageNotFoundError:
            installed = "(not installed)"
        lines.append(f"  {dist} {installed}")
    return "\n".join(lines)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(_format_versions())
        raise typer.Exit()


def _disclaimer_callback(value: bool) -> None:
    if value:
        typer.echo(FULL_DISCLAIMER)
        raise typer.Exit()


app = typer.Typer(
    name="pennytune",
    help=(
        "PennyTune - a free, no-API-key CLI forensic due-diligence tool for "
        "US-listed micro-caps. It surfaces the risk signals and forensic flags "
        "in a company's SEC filings so you can assess it yourself. Research and "
        "educational tool only; not investment advice. It fetches no live prices "
        "and does not assess tradeability."
    ),
    no_args_is_help=False,
    add_completion=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile", help="Strategy preset (trader|hold|high-return|custom)."
        ),
    ] = None,
    config_path: Annotated[
        str | None, typer.Option("--config", help="Use an alternate config file.")
    ] = None,
    offline: Annotated[
        bool, typer.Option("--offline", help="No network; degraded (no live fetch).")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Machine-readable output to stdout.")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", help="Suppress progress/decoration.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", help="Assume 'yes' to confirmations (CI).")
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option(
            "--no-color",
            help="Disable color. (The NO_COLOR environment variable is not read.)",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Name why each ticker failed to enrich (on stderr).",
        ),
    ] = False,
    show_version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print version + pinned deps and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    show_disclaimer: Annotated[
        bool,
        typer.Option(
            "--disclaimer",
            help="Print the full legal disclaimer and exit.",
            callback=_disclaimer_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Global flags shared by every command."""
    ctx.obj = GlobalState(
        profile=profile,
        config_path=config_path,
        offline=offline,
        json_output=json_output,
        quiet=quiet,
        yes=yes,
        no_color=no_color,
        verbose=verbose,
    )
    if ctx.invoked_subcommand is None:
        _maybe_banner(ctx.obj)
        typer.echo(ctx.get_help())


# ---- shared helpers ---------------------------------------------------------


def _state(ctx: typer.Context) -> GlobalState:
    return ctx.obj if isinstance(ctx.obj, GlobalState) else GlobalState()


def _config_path(ctx: typer.Context) -> Path | None:
    state = _state(ctx)
    return Path(state.config_path) if state.config_path else None


def _maybe_banner(state: GlobalState) -> None:
    if banner.should_show_banner(
        is_tty=sys.stdout.isatty(),
        no_color=state.no_color,
        quiet=state.quiet,
        json_output=state.json_output,
    ):
        typer.echo(banner.render_banner(no_color=state.no_color), nl=False)


def _interactive(state: GlobalState) -> bool:
    """Prompt only at a real interactive TTY (never piped/CI), and not --yes/--quiet."""
    return sys.stdin.isatty() and not (state.yes or state.quiet)


def _load_config(path: Path | None) -> Config:
    """Load config, or exit 3 naming the file that could not be read.

    Every caller goes through here. An unguarded ``load_config`` turns any
    invalid config - hand edit, version skew, partial write - into a traceback
    and exit 1, which ``exit_codes`` reserves for "results are still written".
    Nothing recovers such a config through the CLI, so the message has to name
    the file to fix or delete.
    """
    try:
        return load_config(path)
    # UnicodeDecodeError is a ValueError, not an OSError, so a config carrying a
    # stray non-UTF-8 byte slips past the obvious catch tuple.
    except (
        ValidationError,
        tomllib.TOMLDecodeError,
        OSError,
        UnicodeDecodeError,
    ) as exc:
        target = path or paths.config_file()
        typer.echo(f"Cannot read config file {target}", err=True)
        typer.echo(f"  {exc}", err=True)
        typer.echo(
            "Correct the file or delete it and re-run `pennytune init`.", err=True
        )
        raise typer.Exit(code=int(ExitCode.CONFIG_ERROR)) from None


def _require_ready(ctx: typer.Context) -> Config:
    """Load config and refuse to scan/inspect until init is complete (exit 3)."""
    cfg = _load_config(_config_path(ctx))
    if not cfg.edgar_identity:
        typer.echo(
            "EDGAR identity not set. Run: pennytune init --identity 'Name email'",
            err=True,
        )
        raise typer.Exit(code=int(ExitCode.CONFIG_ERROR))
    if not cfg.risk_acknowledged:
        typer.echo(
            "Risk not acknowledged. Run: pennytune init --i-understand-the-risks",
            err=True,
        )
        raise typer.Exit(code=int(ExitCode.CONFIG_ERROR))
    return cfg


# ---- init -------------------------------------------------------------------


@app.command()
def init(
    ctx: typer.Context,
    identity: Annotated[
        str | None,
        typer.Option(
            "--identity",
            help="SEC EDGAR identity: 'Name email' (a request header, not a key).",
        ),
    ] = None,
    default_profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            help="Default strategy profile (trader|hold|high-return|custom).",
        ),
    ] = None,
    i_understand: Annotated[
        bool,
        typer.Option(
            "--i-understand-the-risks",
            help="Record the risk acknowledgment non-interactively.",
        ),
    ] = False,
) -> None:
    """Interactive first-time setup: EDGAR identity + profile + risk acknowledgment."""
    state = _state(ctx)
    _maybe_banner(state)
    typer.echo("PennyTune setup — all data is free and requires no API keys.")
    path = _config_path(ctx)
    cfg = _load_config(path)

    if identity is None:
        # Same non-interactive guard as the profile/risk steps: under
        # --i-understand-the-risks (scripted) require --identity explicitly
        # rather than prompting, so init can never hang on an unreadable stdin.
        if _interactive(state) and not i_understand:
            identity = typer.prompt("SEC EDGAR identity (Name email)")
        else:
            typer.echo("Missing --identity (required).", err=True)
            raise typer.Exit(code=int(ExitCode.CONFIG_ERROR))
    try:
        identity = validate_edgar_identity(identity)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=int(ExitCode.CONFIG_ERROR)) from None
    cfg.edgar_identity = identity

    # Fall back to the STORED profile, never a literal. Defaulting to "hold" here
    # turns a re-run to change an email address into a silent reset of every
    # weight and penalty. Reading cfg.profile lets a stored "custom" reach
    # apply_profile's `name != "custom"` guard, which is what preserves tuning.
    stored_profile = cfg.profile
    chosen = default_profile
    if chosen is None:
        # --i-understand-the-risks marks a scripted/non-interactive run (it also
        # bypasses the risk-ack prompt below); take the default profile without
        # prompting so init never blocks on an unreadable stdin - e.g. on Windows,
        # where isatty() reports True even when no interactive input is available.
        chosen = (
            typer.prompt("Default profile", default=stored_profile)
            if _interactive(state) and not i_understand
            else stored_profile
        )
    try:
        apply_profile(cfg, chosen)
    except ValueError as exc:
        typer.echo(f"Invalid profile: {exc}", err=True)
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR)) from None
    # Announce a real profile change, matching what `config set profile` prints.
    # A silent reset of the user's weights is how this goes unnoticed.
    if chosen != stored_profile and chosen != "custom":
        typer.echo(f"Profile {stored_profile} -> {chosen}")
        typer.echo(f"(weights and penalties reset to the {chosen} profile)")

    acknowledged = i_understand
    if not acknowledged and _interactive(state):
        # Show the full disclaimer FIRST, then take the acknowledgment, so the
        # "I UNDERSTAND" confirmation follows an actual reading of the complete
        # text (Section 12 requires the user to have read the entire disclaimer).
        typer.echo("")
        typer.echo(FULL_DISCLAIMER)
        typer.echo("")
        typed = typer.prompt('Risk acknowledgment — type "I UNDERSTAND" to proceed')
        acknowledged = typed.strip() == "I UNDERSTAND"
    if not acknowledged:
        typer.echo(
            "Risk not acknowledged. Re-run with --i-understand-the-risks.",
            err=True,
        )
        raise typer.Exit(code=int(ExitCode.CONFIG_ERROR))
    if i_understand:
        # The flag bypasses the interactive prompt (automation/CI); never flip
        # the acknowledgment bit silently — affirm it and point at the full text.
        typer.echo(RISK_FLAG_AFFIRMATION)
    cfg.risk_acknowledged = True

    saved = _save_config_or_exit(cfg, path)
    typer.echo(f"Saved config to {saved}")
    typer.echo("Run `pennytune scan` to start.")


# ---- scan pipeline wiring --------------------------------------------------

_SORT_CHOICES = ("score", "growth", "valuation", "risk")
_EXPORT_EXT = {"csv": "csv", "parquet": "parquet", "json": "json", "markdown": "md"}


class _DegradingEvidenceProvider:
    """Fallback evidence provider used offline (and before identity is set).

    Makes no network calls: each survivor is returned as completeness-flagged
    evidence rather than fabricating signals. Tests inject a fixture provider to
    exercise the full scoring/render path offline.
    """

    reason = "offline — no live data fetched; run without --offline for live SEC data"

    def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
        return scan_mod.degraded_evidence(candidate, self.reason)


def _ftd_context_note(ftd: FtdEvidence) -> str | None:
    """Surface fails-to-deliver as settlement-stress CONTEXT (never a verdict)."""
    context = ftd.ftd
    if context is None or not context.present:
        return None
    span = "persistent" if context.persistent else "single-window"
    return (
        f"fails-to-deliver context ({span}): {context.total_fails:,.0f} fails over "
        f"{context.window_count} settlement window(s) in SEC file {ftd.period} — "
        "lagged settlement-stress context, not evidence of manipulation"
    )


def _red_flag_8k_note(tape: EventTape) -> str | None:
    """A completeness line surfacing red-flag 8-K items (inspect visibility).

    Recent (windowed) material events — 3.01 delisting (→ delisting), 1.03,
    5.02, 2.03/2.04 — are tagged ``recent``; the auditor/restatement count is
    taken from the full filing history (``on file``) because that is what
    actually un-gates the dilution detections (a restatement is a persistent
    forensic flag, unlike a cured delisting deficiency).
    """
    s = tape.signals
    parts: list[str] = []
    if s.has_delisting_notice:
        parts.append("3.01 delisting-deficiency (recent)")
    if s.has_bankruptcy:
        parts.append("1.03 bankruptcy (recent)")
    if s.officer_change_count:
        parts.append(f"5.02 officer-change×{s.officer_change_count} (recent)")
    if s.covenant_or_obligation_count:
        parts.append(f"2.03/2.04 obligation×{s.covenant_or_obligation_count} (recent)")
    # 4.01 and 4.02 are counted separately here even though the dilution module
    # treats either as un-gating. An auditor change is routine; a 4.02 is the
    # issuer stating its own prior financials cannot be relied upon, and a
    # combined count hides the difference.
    auditor_change = tape.item_counts.get("4.01", 0)
    if auditor_change:
        parts.append(f"4.01 auditor-change×{auditor_change} (on file)")
    non_reliance = tape.item_counts.get("4.02", 0)
    if non_reliance:
        parts.append(
            f"4.02 non-reliance on previously issued financials×{non_reliance} "
            "(on file)"
        )
    return "red-flag 8-K items — " + "; ".join(parts) if parts else None


class _LiveEvidenceProvider:
    """Evidence provider: fundamentals + dilution + SIC + insider + 8-K events.

    For each survivor this fetches ``companyfacts`` once (fundamentals AND the
    dilution share-count series) and ``submissions`` once (shared by dilution -
    filing list + SIC - insider - the Form 4/5, 144 and 13D/G index - and 8-K
    events - the item codes), then runs one best-effort EFTS toxic probe and
    fetches each recent Form 4/5 ownership XML for its transaction codes — all
    through the hardened HTTP client using the configured EDGAR ``User-Agent``.
    The 8-K event tape un-gates the dilution auditor/restatement detections and
    drives the 3.01 delisting deficiency (fed to ``delisting``, never
    double-counted). The SEC trading-suspension list (one cached fetch) gates an
    active/recent suspension (matched by company name); the bi-monthly
    fails-to-deliver bulk file (one cached fetch) adds settlement-stress context
    (matched by symbol, never scored). This is the complete SEC-EDGAR evidence.
    Suppress-not-impute: a missing CIK or unavailable companyfacts degrades the
    name honestly; a submissions / EFTS / Form-4 / suspension-list / FTD-file
    failure degrades only its slice.
    """

    def __init__(
        self,
        fundamentals: EdgarFundamentalsProvider,
        dilution: EdgarDilutionProvider,
        insider: EdgarInsiderProvider,
        suspensions: EdgarSuspensionProvider,
        ftd: EdgarFtdProvider,
        client: SafeHttpClient,
    ) -> None:
        self._fundamentals = fundamentals
        self._dilution = dilution
        self._insider = insider
        self._suspensions = suspensions
        self._ftd = ftd
        self._client = client
        self._ticker_cik: dict[str, EdgarListing] | None = None

    def _resolve_cik(self, candidate: UniverseCandidate) -> str | None:
        """Use the universe-supplied CIK, else resolve the ticker via SEC."""
        if candidate.cik:
            return candidate.cik
        if self._ticker_cik is None:  # inspect path: no universe was loaded
            payload = cast(
                dict[str, Any],
                self._client.get_json(SEC_UNIVERSE_URL, provider="edgar"),
            )
            self._ticker_cik = parse_edgar_exchange_map(payload)
        listing = self._ticker_cik.get(candidate.ticker.upper())
        return listing.cik if listing else None

    def gather(self, candidate: UniverseCandidate) -> scan_mod.RawEvidence:
        cik = self._resolve_cik(candidate)
        if not cik:
            return scan_mod.degraded_evidence(
                candidate, "no SEC CIK for ticker (cannot fetch EDGAR data)"
            )
        try:
            # One companyfacts fetch feeds BOTH fundamentals and the dilution
            # share-count series.
            facts_json = self._fundamentals.fetch_companyfacts(cik)
        except ProviderError as exc:
            return scan_mod.degraded_evidence(
                candidate, f"companyfacts unavailable: {exc}"
            )
        fundamentals = period_financials_from_companyfacts(facts_json)
        revenue = fundamentals.period_t.revenue if fundamentals.period_t else None
        now = datetime.now(UTC)
        # One submissions fetch shared by dilution (filings + SIC) and insider
        # (the Form 4/5, 144 and 13D/G index); each slice degrades on its own.
        try:
            submissions: dict[str, Any] | None = self._dilution.fetch_submissions(cik)
        except ProviderError:
            submissions = None
        # 8-K events from the SAME submissions (item codes are in submissions —
        # no extra fetch). The tape un-gates the dilution 4.01/4.02/5.03/5.06
        # detections and drives the 3.01 delisting deficiency — no double-count:
        # 3.01 feeds delisting only, never dilution.
        event_tape = None
        delisting_inputs = None
        delisting_notes: list[str] = []
        if submissions is not None:
            event_tape = build_event_tape(
                parse_submissions_8k_events(submissions), cik=cik, now=now
            )
            # Item 3.01 is the tagged route, but a material minority of issuers
            # disclose continued-listing trouble under 8.01/7.01 instead. Probe
            # full text only when no tagged notice already fired: it saves a
            # request on the common case and cannot double-count.
            full_text_deficiency = False
            if not event_tape.signals.has_delisting_notice:
                window = (
                    (now - timedelta(days=_DELISTING_FTS_DAYS)).date().isoformat(),
                    now.date().isoformat(),
                )
                try:
                    hits = self._dilution.full_text_search(
                        EdgarDilutionProvider.DELISTING_EFTS_QUERY,
                        forms=EdgarDilutionProvider.DELISTING_EFTS_FORMS,
                        ciks=cik,
                        dates=window,
                    )
                    full_text_deficiency = bool(parse_efts_hits(hits))
                except ProviderError as exc:
                    delisting_notes.append(
                        f"delisting full-text scan degraded (EFTS: {exc})"
                    )
            delisting_inputs = DelistingInputs(
                event_tape=event_tape, full_text_deficiency=full_text_deficiency
            )
        dilution = self._dilution.get_dilution_evidence(
            cik,
            companyfacts=facts_json,
            submissions=submissions,
            revenue=revenue,
            now=now,
            event_tape=event_tape,
        )
        insider = self._insider.get_insider_evidence(
            cik, submissions=submissions, now=now
        )
        # SEC trading-suspension check against the once-fetched list, matched by
        # company name (the list has no ticker). The gate (unchanged) fires only
        # on an active/recent suspension; "not on the list" is clean, not
        # degraded; "could not fetch the list" is degraded and flagged.
        company_name = str(facts_json.get("entityName", "")) or candidate.name
        halt = self._suspensions.get_halt_evidence(
            candidate.ticker, company_name, now=now
        )
        # Fails-to-deliver settlement-stress CONTEXT from the once-fetched bulk
        # file, matched by symbol. Never gated or scored; "no fails" is clean
        # (not degraded); an unfetchable file is degraded and flagged.
        ftd = self._ftd.get_ftd_evidence(candidate.ticker, now=now)
        completeness = [
            *fundamentals.completeness,
            *delisting_notes,
            *dilution.completeness,
            *insider.completeness,
            *halt.completeness,
            *ftd.completeness,
        ]
        red_flags = _red_flag_8k_note(event_tape) if event_tape is not None else None
        if red_flags is not None:
            completeness.append(red_flags)
        ftd_note = _ftd_context_note(ftd)
        if ftd_note is not None:
            completeness.append(ftd_note)
        # Staff correspondence off the submissions index already in hand. No
        # extra request, and nothing downstream reads it: it is a line for the
        # reader, not an input.
        if submissions is not None:
            letters = comment_letter_activity(submissions, now=now)
            if letters is not None:
                completeness.append(letters.note())
        return scan_mod.RawEvidence(
            ticker=candidate.ticker,
            sic_code=dilution.sic_code,
            sic_sector=dilution.sic_sector,
            financials_period=fundamentals.financials_period,
            financials_filed=fundamentals.financials_filed,
            period_t=fundamentals.period_t,
            period_t1=fundamentals.period_t1,
            revenue_growth=fundamentals.revenue_growth,
            dilution=dilution.inputs,
            delisting=delisting_inputs,
            insider_transactions=insider.transactions,
            form144s=insider.form144s,
            ownership_filings=insider.ownership_filings,
            event_tape=event_tape,
            halt=halt.halt,
            ftd=ftd.ftd,
            completeness=completeness,
        )

    def close(self) -> None:
        self._client.close()


def _make_evidence_provider(
    cfg: Config, state: GlobalState
) -> scan_mod.EvidenceProvider:
    """Build the evidence provider (overridable in tests).

    Online with a configured identity: all evidence categories come from LIVE
    SEC EDGAR data — fundamentals, dilution, SIC, insider, 8-K events,
    trading-suspensions, and fails-to-deliver. Offline — or before an EDGAR
    identity is set — the degrading default, which makes no network calls.
    """
    if state.offline or not cfg.edgar_identity:
        return _DegradingEvidenceProvider()
    limiter = RateLimiter({"edgar": cfg.rate_limits.edgar_rps})
    # The configured EDGAR identity IS the SEC-required User-Agent on the wire.
    client = SafeHttpClient(limiter=limiter, user_agent=cfg.edgar_identity)
    return _LiveEvidenceProvider(
        EdgarFundamentalsProvider(client),
        EdgarDilutionProvider(client),
        EdgarInsiderProvider(client),
        EdgarSuspensionProvider(client),
        EdgarFtdProvider(client),
        client,
    )


def _close_provider(provider: object) -> None:
    """Release a provider's resources if it owns any (live client)."""
    closer = getattr(provider, "close", None)
    if callable(closer):
        closer()


def _resolve_scan_config(
    cfg: Config,
    state: GlobalState,
    *,
    preset: str | None = None,
    exchange: str | None = None,
    top: int = 10,
    sort: str = "score",
    exclude_flagged: bool = False,
    exclude_serial_splitter: bool = False,
    require_insider_buying: bool = False,
    no_news: bool = False,
) -> tuple[ScanRequest, Filters, str]:
    """Compose the strategy profile, the universe preset, and the scan flags."""
    if sort not in _SORT_CHOICES:
        typer.echo(
            f"Invalid --sort {sort!r}; choose from {list(_SORT_CHOICES)}", err=True
        )
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR))

    profile_name = state.profile or cfg.profile
    preset_name = preset or cfg.preset
    # Profile/preset bundles are applied at *set* time (`init` / `config set`),
    # so the saved config already holds the right weights. Only re-apply when the
    # user EXPLICITLY passes --profile/--preset for this run - otherwise a
    # hand-tuned `config set weights.x` would be silently clobbered.
    try:
        if state.profile is not None:
            apply_profile(cfg, state.profile)
        if preset is not None:
            apply_preset(cfg, preset)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR)) from None

    if exchange is not None:
        try:
            cfg.filters.exchange = exchange  # type: ignore[assignment]
        except ValidationError as exc:
            typer.echo(f"Invalid --exchange value: {exc}", err=True)
            raise typer.Exit(code=int(ExitCode.USAGE_ERROR)) from None

    bundle = cfg.presets[preset_name].model_dump() if preset_name in cfg.presets else {}
    request = ScanRequest(
        preset_name=preset_name,
        profile_name=profile_name,
        positive_weights=cfg.weights.model_dump(),
        penalty_magnitudes=cfg.penalties.model_dump(),
        preset_bundle=bundle,
        top_n=top,
        sort=sort,
        exclude_flagged=exclude_flagged,
        exclude_serial_splitter=exclude_serial_splitter,
        require_insider_buying=require_insider_buying,
        no_news=no_news,
        guardrails=get_profile(profile_name).guardrails,
    )
    return request, cfg.filters, preset_name


def _open_watchlist() -> Watchlist | None:
    try:
        return Watchlist()
    except Exception:  # watchlist is best-effort; never block a scan on it
        return None


def _watchlist_db_path() -> Path:
    return paths.data_dir() / "pennytune.db"


def _open_watchlist_or_exit() -> Watchlist:
    """Open the watchlist DB, or exit 3 naming the file that could not be used.

    Same shape as :func:`_load_config`. The ``watch`` commands are the watchlist,
    so unlike a scan they cannot degrade past a broken database. Corrupt, locked
    and directory-shaped db files all land here.
    """
    try:
        return Watchlist()
    except (sqlite3.Error, OSError) as exc:
        target = _watchlist_db_path()
        typer.echo(f"Cannot use watchlist database {target}", err=True)
        typer.echo(f"  {exc}", err=True)
        typer.echo(
            "Correct the file or delete it; it is recreated on next use.", err=True
        )
        raise typer.Exit(code=int(ExitCode.CONFIG_ERROR)) from None


def _save_config_or_exit(cfg: Config, path: Path | None) -> Path:
    """Persist the config, or exit 3 naming the file that could not be written."""
    try:
        return save_config(cfg, path)
    except OSError as exc:
        target = path or paths.config_file()
        typer.echo(f"Cannot write config file {target}", err=True)
        typer.echo(f"  {exc}", err=True)
        typer.echo("Check the path and its permissions, then re-run.", err=True)
        raise typer.Exit(code=int(ExitCode.CONFIG_ERROR)) from None


def _universe_header(report: ScanReport) -> str:
    bits = [f"preset={report.preset_name}", f"profile={report.profile_name}"]
    counts = report.universe_counts
    if counts:
        selected = counts.get("selected", "?")
        bits.append(f"{selected} ticker(s)")
    return "Scan set  " + "  ".join(bits)


def _render_scan(
    report: ScanReport, state: GlobalState, degraded_note: str | None
) -> None:
    """Render the watchlist banner, freshness header, table, and footer."""
    if report.watchlist_alerts:
        typer.echo("Watchlist alerts:")
        for alert in report.watchlist_alerts:
            typer.echo(f"  ! {alert}")
    if not state.quiet:
        typer.echo(_universe_header(report))
        for line in report.freshness_lines:
            typer.echo(f"  {line}")
        for note in report.notes:
            typer.echo(f"  note: {note}")
        if degraded_note:
            typer.echo(f"  degraded: {degraded_note}")
    typer.echo(
        output.render_console(
            report.result, no_color=state.no_color, quiet=state.quiet
        ),
        nl=False,
    )
    if not state.quiet:
        if report.completeness_flags:
            reduced = len(report.completeness_flags)
            typer.echo(f"{reduced} name(s) with reduced data completeness.")
        if report.failures:
            shown = ", ".join(ticker for ticker, _ in report.failures[:10])
            typer.echo(f"{len(report.failures)} ticker(s) failed to enrich: {shown}")
        # A name the fetch boundary could not measure is excluded from ranking
        # rather than scored; say so, so it is never silently dropped.
        not_assessed = [
            ticker
            for ticker, reason in report.excluded_by_filter
            if reason == NOT_ASSESSED_REASON
        ]
        if not_assessed:
            shown = ", ".join(not_assessed[:10])
            typer.echo(
                f"{len(not_assessed)} name(s) NOT ASSESSED (no SEC evidence "
                f"fetched; not scored, not ranked): {shown}"
            )
        for guardrail in report.guardrails:
            typer.echo(f"  guardrail: {guardrail}")
        for attribution in report.attributions:
            typer.echo(attribution)
    typer.echo(DUE_DILIGENCE_NOTE)


def _scan_json(report: ScanReport, degraded_note: str | None) -> str:
    payload = {
        "_disclaimer": EXPORT_HEADER,
        "results": output.result_to_records(report.result),
        "meta": {
            "preset": report.preset_name,
            "profile": report.profile_name,
            "universe_counts": report.universe_counts,
            "universe_from_cache": report.universe_from_cache,
            "freshness": report.freshness_lines,
            "failures": [{"ticker": t, "reason": r} for t, r in report.failures],
            "excluded_by_filter": [
                {"ticker": t, "reason": r} for t, r in report.excluded_by_filter
            ],
            "completeness_flags": report.completeness_flags,
            "watchlist_alerts": report.watchlist_alerts,
            "guardrails": list(report.guardrails),
            "attributions": list(report.attributions),
            "fundamental_screener_note": DUE_DILIGENCE_NOTE,
            "notes": report.notes,
            "degraded": degraded_note,
            "partial_failure": report.partial_failure,
        },
    }
    return json.dumps(payload, indent=2, default=str)


def _report_failure_reasons(report: ScanReport, state: GlobalState) -> None:
    """Under --verbose, name WHY each ticker failed to enrich.

    Without this the console reports only how many tickers failed, which makes a
    total SEC outage and a mistyped ticker read identically. Goes to stderr so a
    ``--json`` payload on stdout stays parseable. Safe to print: provider
    exceptions carry the request URL and status, and the EDGAR identity travels
    in the User-Agent header, never in the message.
    """
    if not state.verbose or not report.failures:
        return
    typer.echo(f"{len(report.failures)} ticker(s) failed to enrich:", err=True)
    for ticker, reason in report.failures:
        typer.echo(f"  {ticker}: {reason}", err=True)


def _validate_export_format(fmt: str | None) -> None:
    """Reject a bad --format before anything is fetched, exactly like --sort.

    Validating inside ``_maybe_export`` is too late: it runs after the scan, so a
    bad format costs a full SEC round-trip first, and its ``scanned == 0`` early
    return skips the check entirely.
    """
    if fmt is not None and fmt not in _EXPORT_EXT:
        typer.echo(
            f"Invalid --format {fmt!r}; choose from {list(_EXPORT_EXT)}", err=True
        )
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR))


def _maybe_export(
    report: ScanReport, cfg: Config, state: GlobalState, fmt_override: str | None
) -> None:
    """Write the FULL ranked set to the outputs dir (always, regardless of --top)."""
    if report.scanned == 0:
        return
    fmt = fmt_override or cfg.output_format
    if fmt not in _EXPORT_EXT:
        typer.echo(
            f"Invalid --format {fmt!r}; choose from {list(_EXPORT_EXT)}", err=True
        )
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR))
    out_dir = Path(cfg.output_dir) if cfg.output_dir else paths.results_dir()
    stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    path = out_dir / f"scan_{stamp}.{_EXPORT_EXT[fmt]}"
    try:
        written = output.export(
            report.result, path, fmt, attributions=report.attributions
        )
    except OSError as exc:
        # The destination is the user's own choice (``output_dir``, else
        # ./results), so an unwritable path is a usage problem. Exit 1 is wrong
        # here: it promises results were written when nothing was.
        typer.echo(f"Cannot write export to {path}", err=True)
        typer.echo(f"  {exc}", err=True)
        typer.echo(
            "Set a writable directory with: pennytune config set output_dir <dir>",
            err=True,
        )
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR)) from None
    if not state.quiet:
        # Under --json stdout is the payload and nothing else may touch it, so
        # the confirmation goes to stderr rather than being dropped.
        typer.echo(f"Wrote {written}", err=state.json_output)


_MAX_SCAN_TICKERS = 100


def _curated_candidates(tickers: list[str] | None) -> list[UniverseCandidate]:
    """Resolve scan's candidate set from explicit tickers or the watchlist.

    PennyTune does NOT scan the whole ~7,500-name SEC-listed universe (an egress
    hazard, and meaningless without price data): scan ranks the names you choose,
    capped at 100 to stay polite to SEC EDGAR.
    """
    if tickers:
        symbols = [t.strip().upper() for t in tickers if t.strip()]
    else:
        # Guarded, not best-effort: with no explicit tickers the watchlist is the
        # input, so an unreadable database has to say so. Falling through to
        # "the watchlist is empty" points at a different problem with a
        # different fix.
        wl = _open_watchlist_or_exit()
        try:
            symbols = [t for t, _ in wl.list_tickers()]
        except (sqlite3.Error, OSError) as exc:
            typer.echo(
                f"Cannot read watchlist database {_watchlist_db_path()}", err=True
            )
            typer.echo(f"  {exc}", err=True)
            raise typer.Exit(code=int(ExitCode.CONFIG_ERROR)) from None
        finally:
            wl.close()
        if not symbols:
            typer.echo(
                "No tickers given and the watchlist is empty. Pass tickers "
                "(pennytune scan AAA BBB) or add some with `pennytune watch add`.",
                err=True,
            )
            raise typer.Exit(code=int(ExitCode.USAGE_ERROR))
    deduped = list(dict.fromkeys(symbols))  # preserve order, drop duplicates
    if len(deduped) > _MAX_SCAN_TICKERS:
        typer.echo(
            f"Refusing to scan {len(deduped)} tickers (max {_MAX_SCAN_TICKERS}); "
            "trim the list to stay polite to SEC EDGAR.",
            err=True,
        )
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR))
    return [UniverseCandidate(ticker=s, name=s) for s in deduped]


@app.command()
def scan(
    ctx: typer.Context,
    tickers: Annotated[
        list[str] | None,
        typer.Argument(
            help="Tickers to rank (e.g. `scan AAA BBB`); omit to rank your watchlist."
        ),
    ] = None,
    preset: Annotated[
        str | None,
        typer.Option(
            "--preset",
            help="Risk-weighting preset (penny|micro|small-cap-value|broad|custom).",
        ),
    ] = None,
    exclude_flagged: Annotated[
        bool, typer.Option("--exclude-flagged", help="Drop names with critical flags.")
    ] = False,
    exclude_serial_splitter: Annotated[
        bool,
        typer.Option(
            "--exclude-serial-splitter", help="Drop serial reverse-splitters."
        ),
    ] = False,
    require_insider_buying: Annotated[
        bool,
        typer.Option(
            "--require-insider-buying", help="Keep only recent insider buying."
        ),
    ] = False,
    top: Annotated[
        int, typer.Option("--top", help="How many ranked names to display.")
    ] = 10,
    sort: Annotated[
        str,
        typer.Option("--sort", help="score|growth|valuation|risk."),
    ] = "score",
    export_format: Annotated[
        str | None,
        typer.Option(
            "--format", help="Export file format (csv|parquet|json|markdown)."
        ),
    ] = None,
) -> None:
    """Rank a curated set of tickers by their SEC-filing risk signals.

    Pass tickers (``pennytune scan AAA BBB``) or omit them to rank your
    watchlist; at most 100 per run. PennyTune fetches no live prices and never
    scans the whole market - it ranks the names YOU choose. Positive quality
    sub-scores are graded against fixed published anchors (the Piotroski 0-9
    scale, the Altman Z-double-prime zones, fixed EV/Sales and revenue-growth
    bands), so a name scores the same whichever peers share the run and scores
    are comparable across runs. The ranking of a small curated set is still
    driven mainly by the risk/penalty signals (dilution, distress, delisting,
    insider selling), which is what surfaces the riskiest names in your set.
    """
    state = _state(ctx)
    cfg = _require_ready(ctx)
    _validate_export_format(export_format)
    candidates = _curated_candidates(tickers)
    request = _resolve_scan_config(
        cfg,
        state,
        preset=preset,
        top=top,
        sort=sort,
        exclude_flagged=exclude_flagged,
        exclude_serial_splitter=exclude_serial_splitter,
        require_insider_buying=require_insider_buying,
    )[0]
    provider = _make_evidence_provider(cfg, state)
    watchlist = _open_watchlist()
    try:
        report = run_scan(
            candidates,
            provider,
            request,
            universe_counts={"selected": len(candidates)},
            watchlist=watchlist,
            universe_notes=[],
        )
    finally:
        if watchlist is not None:
            watchlist.close()
        _close_provider(provider)

    # --json changes the shape of stdout and nothing else. The export still runs
    # and a partial failure still exits 1; returning early here would make
    # --format a no-op and hand a green exit code to a total SEC outage.
    if state.json_output:
        typer.echo(_scan_json(report, None))
    else:
        _render_scan(report, state, None)
    _report_failure_reasons(report, state)
    _maybe_export(report, cfg, state, export_format)
    if report.partial_failure:
        typer.echo(
            f"Warning: {len(report.failures)} ticker(s) failed to enrich.", err=True
        )
        raise typer.Exit(code=int(ExitCode.PARTIAL_FAILURE))


# ---- inspect ----------------------------------------------------------------


def _exit_for_inspect(report: ScanReport, state: GlobalState) -> None:
    """Give ``inspect`` the failure exit path it never had.

    Without this a script cannot tell a real breakdown from a ticker that
    resolved to nothing. Where the line falls:

    * breakdown produced -> 0, however heavily suppressed. A NOT ASSESSED row
      backed by a real lookup is a finding, not an error.
    * ``--offline`` -> 0 regardless. No lookup was attempted, so "no evidence"
      is what the flag means, and ``scan --offline`` agrees.
    * fetch boundary raised -> 1, matching what ``scan`` returns for the same
      ticker under the same fault. The two must not disagree.
    * live lookup produced nothing, nothing failed -> 2. The ticker names no SEC
      filer, which is a property of the argument, not the network.
    """
    if report.result.full or state.offline:
        return
    if report.failures:
        raise typer.Exit(code=int(ExitCode.PARTIAL_FAILURE))
    raise typer.Exit(code=int(ExitCode.USAGE_ERROR))


def _render_inspect(ticker: str, report: ScanReport) -> None:
    """Render the full additive composite-score breakdown for one ticker."""
    records = output.result_to_records(report.result)
    signals = report.signals.get(ticker)
    if not records:
        typer.echo(f"{ticker}: no evidence could be assembled.")
        if signals and signals.completeness:
            for note in signals.completeness:
                typer.echo(f"  completeness: {note}")
        return
    record = records[0]
    typer.echo(
        f"{ticker}  composite {record['composite']}  sector {record['sic_sector']}"
    )
    suppressed = set(record.get("suppressed") or ())
    typer.echo("Positive contributions:")
    for key, value in record["positive_contributions"].items():
        # A contributor that could not be computed reads +0.000, exactly like
        # one that was computed and came out zero. Say which it was.
        mark = "   not computed" if key in suppressed else ""
        typer.echo(f"  + {key:22s} {value:+.3f}{mark}")
    if record["penalty_contributions"]:
        typer.echo("Penalty overlays:")
        for key, value in record["penalty_contributions"].items():
            typer.echo(f"  - {key:22s} {value:+.3f}")
    # A penalty that never ran contributes no key at all - identical to one
    # that ran and found nothing. One consolidated line names the difference.
    unchecked = sorted(suppressed - set(POSITIVE_KEYS))
    if unchecked:
        typer.echo(f"not checked (no data): {', '.join(unchecked)}")
    if record["na_modules"]:
        typer.echo(f"n/a for this preset: {', '.join(record['na_modules'])}")
    if record["gated"]:
        typer.echo(f"[X] GATED: {'; '.join(record['gate_reasons'])}")
    if signals is not None:
        if signals.ftd is not None and signals.ftd.present:
            typer.echo("Fails-to-deliver present (context only).")
        for note in signals.completeness:
            typer.echo(f"  completeness: {note}")
    for note in record["notes"]:
        typer.echo(f"  note: {note}")


@app.command()
def inspect(
    ctx: typer.Context,
    ticker: Annotated[str, typer.Argument(help="Ticker symbol to inspect.")],
) -> None:
    """Full, evidence-backed breakdown for one ticker (the score, decomposed)."""
    state = _state(ctx)
    cfg = _require_ready(ctx)
    # Strip before upper-casing, matching `_curated_candidates`. A trailing space
    # off a copy-paste otherwise resolves to no CIK, and the user is told a real
    # company has no SEC filings.
    symbol = ticker.strip().upper()
    request, _filters, _preset = _resolve_scan_config(cfg, state, top=1)
    provider = _make_evidence_provider(cfg, state)
    candidate = UniverseCandidate(ticker=symbol, name=symbol)
    try:
        report = run_scan([candidate], provider, request)
    finally:
        _close_provider(provider)

    _report_failure_reasons(report, state)
    if state.json_output:
        records = output.result_to_records(report.result)
        record: dict[str, Any] = records[0] if records else {"ticker": symbol}
        record["completeness"] = report.completeness_flags.get(symbol, [])
        typer.echo(
            json.dumps({"_disclaimer": EXPORT_HEADER, "inspect": record}, indent=2)
        )
        _exit_for_inspect(report, state)
        return
    # The one-line disclaimer is unconditional (matching scan), so no
    # human-readable analysis is ever emitted without it; the longer
    # due-diligence note stays quiet-gated.
    typer.echo(SHORT_DISCLAIMER)
    if not state.quiet:
        typer.echo(DUE_DILIGENCE_NOTE)
    _render_inspect(symbol, report)
    _exit_for_inspect(report, state)


# ---- sources ----------------------------------------------------------------


@app.command()
def sources(ctx: typer.Context) -> None:
    """Show data sources, free-tier limits, and which domains are contacted."""
    state = _state(ctx)
    if state.json_output:
        typer.echo(json.dumps({"sources": list(_SOURCES)}, indent=2))
        return
    for src in _SOURCES:
        typer.echo(
            f"{src['source']:20s} {src['role']:32s} key={src['key']:18s} {src['limit']}"
        )
        typer.echo(f"  domains: {src['domains']}")
    typer.echo("")
    typer.echo(
        "Sources are no-key and PennyTune uses no API keys: SEC data is U.S. "
        "government public domain."
    )
    typer.echo(
        "No live prices are fetched (no technicals/spread); intraday "
        "trading-halt status is not evaluated — verify it in your broker."
    )


# ---- config (get | set) -----------------------------------------------------

config_app = typer.Typer(help="View/edit configuration and scoring weights.")


@config_app.command("get")
def config_get(
    ctx: typer.Context,
    key: Annotated[
        str | None,
        typer.Argument(help="Dotted key, e.g. weights.valuation (omit for all)."),
    ] = None,
) -> None:
    """Print configuration settings (the EDGAR email is redacted)."""
    cfg = _load_config(_config_path(ctx))
    if key is None:
        for name, value in sorted(flatten(cfg).items()):
            shown = (
                redact_identity(cfg.edgar_identity)
                if name == "edgar_identity"
                else value
            )
            typer.echo(f"{name} = {shown}")
        return
    try:
        value = get_value(cfg, key)
    except KeyError:
        typer.echo(f"Unknown config key: {key}", err=True)
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR)) from None
    shown = redact_identity(cfg.edgar_identity) if key == "edgar_identity" else value
    typer.echo(f"{key} = {shown}")


@config_app.command("set")
def config_set(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Dotted key, e.g. weights.growth.")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Set a configuration value (validates ranges; rejects unknown keys)."""
    path = _config_path(ctx)
    cfg = _load_config(path)
    try:
        old = get_value(cfg, key)
    except KeyError:
        typer.echo(f"Unknown config key: {key}", err=True)
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR)) from None
    try:
        set_value(cfg, key, value)
    except (ValueError, ValidationError) as exc:
        typer.echo(f"Invalid value for {key}: {exc}", err=True)
        raise typer.Exit(code=int(ExitCode.USAGE_ERROR)) from None
    _save_config_or_exit(cfg, path)
    new = get_value(cfg, key)
    typer.echo(f"Updated {key}: {old} -> {new}")
    if key == "profile" and value != "custom":
        typer.echo(f"(weights and penalties reset to the {value} profile)")
    if key == "preset" and value != "custom":
        typer.echo(f"(risk-weighting bundle set from the {value} preset)")


app.add_typer(config_app, name="config")


# ---- watch (add | list | rm) ------------------------------------------------

watch_app = typer.Typer(help="Manage the persistent watchlist.")


@watch_app.command("add")
def watch_add(
    ctx: typer.Context,
    tickers: Annotated[list[str], typer.Argument(help="Tickers to add.")],
) -> None:
    """Add tickers to the watchlist."""
    wl = _open_watchlist_or_exit()
    try:
        added = wl.add(tickers)
        typer.echo(f"Added {len(added)} tickers. Watchlist: {len(wl.list_tickers())}.")
    finally:
        wl.close()


@watch_app.command("list")
def watch_list(ctx: typer.Context) -> None:
    """List watched tickers with last score, delta, and open alerts."""
    wl = _open_watchlist_or_exit()
    try:
        entries = wl.list_entries()
        if not entries:
            typer.echo("Watchlist is empty.")
            return
        for entry in entries:
            score = "—" if entry.last_score is None else f"{entry.last_score:.1f}"
            delta = "—" if entry.score_delta is None else f"{entry.score_delta:+.1f}"
            alerts = "; ".join(entry.alerts) if entry.alerts else "-"
            added = entry.added_at[:10]
            row = f"{entry.ticker:8s} {added}  score {score}  delta {delta}"
            typer.echo(f"{row}  {alerts}")
    finally:
        wl.close()


@watch_app.command("rm")
def watch_rm(
    ctx: typer.Context,
    tickers: Annotated[list[str], typer.Argument(help="Tickers to remove.")],
) -> None:
    """Remove tickers from the watchlist."""
    wl = _open_watchlist_or_exit()
    try:
        removed = wl.remove(tickers)
        typer.echo(
            f"Removed {len(removed)} tickers. Watchlist: {len(wl.list_tickers())}."
        )
    finally:
        wl.close()


app.add_typer(watch_app, name="watch")


# ---- disclaimer -------------------------------------------------------------


@app.command()
def disclaimer() -> None:
    """Print the full legal disclaimer (also shown on first run)."""
    typer.echo(FULL_DISCLAIMER)


if __name__ == "__main__":
    app()
