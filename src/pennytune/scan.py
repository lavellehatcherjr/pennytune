"""End-to-end scan pipeline orchestration.

Wires every feature into the complete funnel:

* **Candidate set.** A curated list of tickers (named explicitly or read from
  the watchlist) is passed in here. PennyTune ranks the names you choose; there
  is no whole-universe build and no price/size filtering.
* **Gather evidence.** An injected :class:`EvidenceProvider` yields a
  :class:`RawEvidence` bundle per survivor (fundamentals periods, dilution
  inputs, 8-K event tape, insider transactions, fails-to-deliver
  settlement-stress context, SEC trading-suspension status). One ticker failing
  never aborts the scan; a provider being down degrades to flagged,
  lower-completeness evidence rather than failing.
* **Compute every signal.** The pure fundamentals, dilution-risk, delisting,
  suspension, insider, and forensic scoring functions run over the evidence;
  valuation/growth/fundamental-momentum/financial-health are scored as
  **sector- and size-relative percentiles**, never absolute cutoffs. (No price
  technicals - no price history is fetched or used beyond the snapshot.)
* **Score, gate, rank.** Signals are assembled into
  :class:`scoring.ScoreInputs` with **preset-aware penalty weighting** and the
  two hard gates, then ranked; fails-to-deliver are **context only**,
  never added to the score.

``run_scan`` is a pure function of its inputs (reproducible): the same
candidates + evidence + weights yield the same ranking. ``--offline`` makes no
network calls (the provider reads only cache).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from pennytune import freshness as fresh
from pennytune.features.delisting import (
    DelistingInputs,
    DelistingProfile,
    compute_delisting,
)
from pennytune.features.dilution import (
    DilutionInputs,
    DilutionProfile,
    compute_dilution,
)
from pennytune.features.events import EventTape
from pennytune.features.halts import HaltProfile
from pennytune.features.insider import (
    Form144,
    InsiderProfile,
    InsiderTransaction,
    InstitutionalPosition,
    OwnershipFiling,
    compute_insider_signal,
)
from pennytune.features.manipulation import (
    ManipulationInputs,
    ManipulationProfile,
)
from pennytune.features.quant_scores import (
    PeriodFinancials,
    ScoreResult,
    altman_z,
    beneish_m,
    ev_valuation,
    is_financials_sic,
    piotroski_f,
    sector_size_percentiles,
    up_market_modules,
)
from pennytune.features.short_interest import FtdContext
from pennytune.features.universe import UNIVERSE_NOTE, UniverseCandidate
from pennytune.freshness import FreshnessReport
from pennytune.scoring import (
    Gates,
    Penalty,
    PositiveSubScores,
    RankedResult,
    ScoreBreakdown,
    ScoreInputs,
    percentile_to_subscore,
    rank_candidates,
    score_candidate,
)

if TYPE_CHECKING:
    from pennytune.features.watchlist import Watchlist

__all__ = [
    "RawEvidence",
    "ComputedSignals",
    "EvidenceProvider",
    "ScanRequest",
    "ScanReport",
    "degraded_evidence",
    "size_bucket",
    "compute_signals",
    "run_scan",
    "PARTIAL_FAILURE_THRESHOLD",
    "CRITICAL_PENALTY_MODULES",
]

# Above this share of survivors failing to enrich, the scan still writes its
# results but signals a partial failure (the partial-failure exit code).
PARTIAL_FAILURE_THRESHOLD = 0.25

# Penalty modules that make a name "flagged" for --exclude-flagged / the red
# glyph (the gates are handled separately and always quarantine).
CRITICAL_PENALTY_MODULES = frozenset(
    {"delisting", "distress", "manipulation", "beneish", "halt_suspension"}
)

_BENEISH_FLAG = -1.78  # Beneish M above this → possible manipulation

# String severities / tiers → a [0, 1] severity for the weighted penalty.
_SEVERITY_SCALE: dict[str, float] = {
    "none": 0.0,
    "low": 0.34,
    "medium": 0.67,
    "high": 1.0,
}
_DELIST_TIER: dict[str, float] = {
    "none": 0.0,
    "watch": 0.25,
    "deficiency": 0.5,
    "imminent": 0.75,
    "determination": 1.0,
}
_HALT_TIER: dict[str, float] = {"none": 0.0, "suspended": 1.0}
_CONF_SCALE: dict[str, float] = {"low": 0.5, "medium": 0.75, "high": 1.0}

# Metric → whether a higher raw value is "better" for the positive sub-score.
_POSITIVE_METRICS: dict[str, bool] = {
    "ev_to_sales": False,  # cheaper (lower EV/Sales) = higher valuation sub-score
    "revenue_growth": True,
    "piotroski": True,
    "altman_z": True,
}
_METRIC_TO_SUBSCORE: dict[str, str] = {
    "ev_to_sales": "valuation",
    "revenue_growth": "growth",
    "piotroski": "fundamental_momentum",
    "altman_z": "fin_health",
}


# ---- evidence + computed-signal containers ----------------------------------


@dataclass
class RawEvidence:
    """Per-ticker parsed inputs for signal computation (what the fetch boundary yields).

    Pure data - fully constructible from fixtures, so the whole pipeline is
    testable with no network. Any field left ``None`` is *suppressed*, not
    imputed: the affected signal contributes nothing and is noted under
    completeness (never silently scored as zero/pass).
    """

    ticker: str
    sic_sector: str = ""
    sic_code: int | None = None
    market_cap: float | None = None
    current_price: float | None = None
    financials_period: str = ""
    financials_filed: str = ""
    period_t: PeriodFinancials | None = None
    period_t1: PeriodFinancials | None = None
    revenue_growth: float | None = None
    dilution: DilutionInputs | None = None
    manipulation: ManipulationInputs | None = None
    delisting: DelistingInputs | None = None
    halt: HaltProfile | None = None
    insider_transactions: tuple[InsiderTransaction, ...] = ()
    form144s: tuple[Form144, ...] = ()
    ownership_filings: tuple[OwnershipFiling, ...] = ()
    institutional: tuple[InstitutionalPosition, ...] = ()
    event_tape: EventTape | None = None
    sentiment_compound: float | None = None
    news_available: bool = True
    gdelt_used: bool = False  # retained inert (no news source feeds it now)
    ftd: FtdContext | None = None
    completeness: list[str] = field(default_factory=list)


@dataclass
class ComputedSignals:
    """Per-ticker computed feature outputs (for scoring + `inspect`/export)."""

    ticker: str
    sic_sector: str = ""
    size_bucket: str = "unknown"
    # Raw positive metrics (None = suppressed → no positive credit, flagged).
    ev_to_sales: float | None = None
    revenue_growth: float | None = None
    piotroski: float | None = None
    altman_z: float | None = None
    sentiment_subscore: float | None = None
    insider_subscore: float = 0.0
    # Feature profiles / scores retained for penalties, gates, and evidence.
    dilution: DilutionProfile | None = None
    manipulation: ManipulationProfile | None = None
    delisting: DelistingProfile | None = None
    halt: HaltProfile | None = None
    insider: InsiderProfile | None = None
    up_market: ScoreResult | None = None
    beneish_m: float | None = None
    beneish_flag: bool = False
    distress_zone: str | None = None  # safe | grey | distress
    out_of_model: bool = False
    event_tape: EventTape | None = None
    gdelt_used: bool = False
    ftd: FtdContext | None = None  # CONTEXT ONLY, never scored
    serial_splitter: bool = False
    insider_buying: bool = False
    completeness: list[str] = field(default_factory=list)


class EvidenceProvider(Protocol):
    """Evidence boundary: yield parsed evidence for one survivor.

    Implementations may raise to signal a total per-ticker failure (counted, not
    fatal), or return :func:`degraded_evidence` to keep the name with a
    completeness flag when a source is down (graceful degradation on a
    partial failure).
    """

    def gather(self, candidate: UniverseCandidate) -> RawEvidence: ...


@dataclass
class ScanRequest:
    """Resolved scan parameters: scoring config (strategy profile + universe
    preset) plus the scan filter flags."""

    preset_name: str = "penny"
    profile_name: str = "hold"
    positive_weights: dict[str, float] = field(default_factory=dict)
    penalty_magnitudes: dict[str, float] = field(default_factory=dict)
    preset_bundle: dict[str, float] = field(default_factory=dict)
    top_n: int | None = 10
    sort: str = "score"
    exclude_flagged: bool = False
    exclude_serial_splitter: bool = False
    require_insider_buying: bool = False
    no_news: bool = False
    guardrails: tuple[str, ...] = ()


@dataclass
class ScanReport:
    """Everything the CLI needs to render the header, table, exports, and exit."""

    result: RankedResult
    signals: dict[str, ComputedSignals] = field(default_factory=dict)
    preset_name: str = "penny"
    profile_name: str = "hold"
    universe_counts: dict[str, int] = field(default_factory=dict)
    universe_from_cache: bool = False
    freshness_lines: list[str] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)
    excluded_by_filter: list[tuple[str, str]] = field(default_factory=list)
    completeness_flags: dict[str, list[str]] = field(default_factory=dict)
    watchlist_alerts: list[str] = field(default_factory=list)
    guardrails: tuple[str, ...] = ()
    # Source attributions to ship in output AND exports (currently always
    # empty; retained for the export path).
    attributions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=lambda: [UNIVERSE_NOTE])

    @property
    def scanned(self) -> int:
        """Number of survivors that produced a score (ranked + high-risk)."""
        return len(self.result.full)

    @property
    def partial_failure(self) -> bool:
        """True when the failed-enrichment share exceeds the threshold (exit 1)."""
        total = self.scanned + len(self.failures)
        if total == 0:
            return False
        return len(self.failures) / total > PARTIAL_FAILURE_THRESHOLD


# ---- helpers ----------------------------------------------------------------


def size_bucket(market_cap: float | None) -> str:
    """Coarse size bucket for sector/size-relative percentiles."""
    if market_cap is None:
        return "unknown"
    if market_cap < 50_000_000:
        return "nano"
    if market_cap < 300_000_000:
        return "micro"
    if market_cap < 2_000_000_000:
        return "small"
    if market_cap < 10_000_000_000:
        return "mid"
    return "large"


def degraded_evidence(candidate: UniverseCandidate, reason: str) -> RawEvidence:
    """Minimal, completeness-flagged evidence for a name whose source is down.

    The SEC universe carries no price/market-cap/sector, so those evidence
    fields stay unset (suppressed) until the per-ticker filing fetch supplies
    them; they are never imputed.
    """
    return RawEvidence(
        ticker=candidate.ticker,
        news_available=False,
        completeness=[f"degraded: {reason}"],
    )


def _altman_zone(z: float | None) -> str | None:
    if z is None:
        return None
    return "distress" if z < 1.1 else "safe" if z > 2.6 else "grey"


def _insider_subscore(profile: InsiderProfile) -> float:
    """Map the insider signal to a [0, 1] positive sub-score (conviction-aware)."""
    base = {"bullish": 1.0, "neutral": 0.3, "bearish": 0.0}.get(profile.net_signal, 0.3)
    if profile.cluster_buy:
        base = max(base, 0.8)
    return round(base * _CONF_SCALE.get(profile.confidence, 0.5), 4)


def compute_signals(evidence: RawEvidence, *, no_news: bool) -> ComputedSignals:
    """Run the pure feature functions over one ticker's evidence."""
    completeness = list(evidence.completeness)
    t, t1 = evidence.period_t, evidence.period_t1

    ev_to_sales: float | None = None
    altman_value: float | None = None
    piotroski_value: float | None = None
    beneish_value: float | None = None
    beneish_flag = False
    up_market: ScoreResult | None = None
    out_of_model = is_financials_sic(evidence.sic_code)

    if t is not None:
        ev = ev_valuation(t, market_cap=evidence.market_cap, sic=evidence.sic_code)
        if ev.computable:
            ev_to_sales = ev.components.get("ev_to_sales")
        else:
            completeness.append("valuation suppressed (EV/Sales unavailable)")
        if "out-of-model-financials" in ev.flags:
            out_of_model = True
        altman = altman_z(t)
        altman_value = altman.value if altman.computable else None
        if altman_value is None:
            completeness.append("Altman Z″ suppressed")
        up_market = up_market_modules(t)
    else:
        completeness.append("fundamentals suppressed (no filed period)")

    if t is not None and t1 is not None:
        piotroski_score = piotroski_f(t, t1)
        piotroski_value = piotroski_score.value if piotroski_score.computable else None
        beneish = beneish_m(t, t1)
        if beneish.computable:
            beneish_value = beneish.value
            beneish_flag = "possible-manipulation" in beneish.flags
    if evidence.revenue_growth is None:
        completeness.append("growth suppressed (no revenue trend)")

    sentiment_subscore: float | None = None
    if no_news or not evidence.news_available or evidence.sentiment_compound is None:
        completeness.append("sentiment suppressed (news unavailable)")
    else:
        sentiment_subscore = round((evidence.sentiment_compound + 1.0) / 2.0, 4)

    dilution = compute_dilution(evidence.dilution) if evidence.dilution else None
    # Structural manipulation-susceptibility is not wired to the live evidence
    # provider (no ManipulationInputs are built from real filings), so it never
    # contributes a penalty; the field stays for config/back-compat.
    manipulation = None
    delisting = compute_delisting(evidence.delisting) if evidence.delisting else None
    insider = compute_insider_signal(
        evidence.insider_transactions,
        form144s=evidence.form144s,
        ownership_filings=evidence.ownership_filings,
        institutional=evidence.institutional,
    )

    return ComputedSignals(
        ticker=evidence.ticker,
        sic_sector=evidence.sic_sector,
        size_bucket=size_bucket(evidence.market_cap),
        ev_to_sales=ev_to_sales,
        revenue_growth=evidence.revenue_growth,
        piotroski=piotroski_value,
        altman_z=altman_value,
        sentiment_subscore=sentiment_subscore,
        insider_subscore=_insider_subscore(insider),
        dilution=dilution,
        manipulation=manipulation,
        delisting=delisting,
        halt=evidence.halt,
        insider=insider,
        up_market=up_market,
        beneish_m=beneish_value,
        beneish_flag=beneish_flag,
        distress_zone=_altman_zone(altman_value),
        out_of_model=out_of_model,
        event_tape=evidence.event_tape,
        gdelt_used=evidence.gdelt_used,
        ftd=evidence.ftd,
        serial_splitter=bool(dilution and dilution.splits.serial),
        insider_buying=insider.insider_buying,
        completeness=completeness,
    )


def _percentiles(signals: Sequence[ComputedSignals]) -> dict[str, dict[str, float]]:
    """Sector/size-relative percentile of each positive metric (NaN = absent)."""
    out: dict[str, dict[str, float]] = {s.ticker: {} for s in signals}
    if not signals:
        return out
    import pandas as pd

    frame = pd.DataFrame(
        [
            {
                "ticker": s.ticker,
                "sic_sector": s.sic_sector or "?",
                "size_bucket": s.size_bucket or "?",
                "ev_to_sales": s.ev_to_sales,
                "revenue_growth": s.revenue_growth,
                "piotroski": s.piotroski,
                "altman_z": s.altman_z,
            }
            for s in signals
        ]
    )
    for metric in _POSITIVE_METRICS:
        ranked = sector_size_percentiles(frame, metric)
        for position, ticker in enumerate(frame["ticker"]):
            value = ranked.iloc[position]
            if pd.notna(value):
                out[str(ticker)][metric] = float(value)
    return out


def _positive_subscores(
    signals: ComputedSignals, percentiles: dict[str, float]
) -> PositiveSubScores:
    """Map percentiles + direct signals to [0, 1] positive sub-scores."""
    positives = PositiveSubScores()
    for metric, higher_better in _POSITIVE_METRICS.items():
        if metric in percentiles:
            setattr(
                positives,
                _METRIC_TO_SUBSCORE[metric],
                percentile_to_subscore(
                    percentiles[metric], higher_is_better=higher_better
                ),
            )
    if signals.sentiment_subscore is not None:
        positives.sentiment = signals.sentiment_subscore
    positives.insider = signals.insider_subscore
    return positives


def _penalties(signals: ComputedSignals) -> dict[str, Penalty]:
    """Assemble the weighted penalty overlays (severity × confidence) for
    composite scoring."""
    penalties: dict[str, Penalty] = {}

    if signals.dilution is not None:
        sev = _SEVERITY_SCALE.get(signals.dilution.severity, 0.0)
        if sev > 0:
            penalties["dilution"] = Penalty(severity=sev)
    if signals.delisting is not None:
        sev = _DELIST_TIER.get(signals.delisting.tier, 0.0)
        if sev > 0:
            penalties["delisting"] = Penalty(severity=sev)
    if signals.halt is not None:
        sev = _HALT_TIER.get(signals.halt.tier, 0.0)
        if sev > 0:
            penalties["halt_suspension"] = Penalty(severity=sev)

    if signals.insider is not None:
        profile = signals.insider
        if profile.net_signal == "bearish" or profile.form144_overhang:
            sev = 0.6 if profile.net_signal == "bearish" else 0.3
            if profile.form144_overhang:
                sev = min(1.0, sev + 0.2)
            penalties["insider_selling"] = Penalty(
                severity=sev, confidence=_CONF_SCALE.get(profile.confidence, 0.5)
            )

    if signals.distress_zone in ("distress", "grey"):
        sev = 1.0 if signals.distress_zone == "distress" else 0.5
        conf = 0.5 if signals.out_of_model else 1.0
        penalties["distress"] = Penalty(severity=sev, confidence=conf)
    if signals.beneish_flag and signals.beneish_m is not None:
        sev = min(1.0, 0.5 + max(0.0, signals.beneish_m - _BENEISH_FLAG) * 0.3)
        conf = 0.5 if signals.out_of_model else 1.0
        penalties["beneish"] = Penalty(severity=sev, confidence=conf)

    penalties.update(_up_market_penalties(signals.up_market))
    return penalties


def _up_market_penalties(up: ScoreResult | None) -> dict[str, Penalty]:
    """Up-market overlays. Dormant under penny (preset weight 0 → 'n/a')."""
    if up is None:
        return {}
    flags = set(up.flags)
    penalties: dict[str, Penalty] = {}
    if "goodwill-impairment" in flags:
        penalties["goodwill_impairment"] = Penalty(severity=0.7)
    leverage = 0.4 * ("high-leverage" in flags) + 0.4 * (
        "weak-interest-coverage" in flags
    )
    if leverage > 0:
        penalties["leverage_coverage"] = Penalty(severity=min(1.0, leverage))
    if "high-sbc-dilution" in flags:
        sbc = up.components.get("sbc_pct_revenue", 0.10)
        penalties["sbc_dilution"] = Penalty(severity=min(1.0, sbc / 0.20))
    if "multiple-compression-risk" in flags:
        penalties["multiple_compression"] = Penalty(severity=0.6)
    return penalties


def _gates(signals: ComputedSignals) -> Gates:
    """The two hard gates: active SEC trading suspension + delisting determination.

    Intraday trading-halt status is not gated here — the tool carries no live
    halt feed; that check is the user's own broker lookup (see TRADEABILITY_NOTE).
    """
    halt_tier = signals.halt.tier if signals.halt else "none"
    return Gates(
        active_suspension=halt_tier == "suspended",
        disclosed_determination=bool(
            signals.delisting and signals.delisting.hard_exclude
        ),
    )


def _to_score_inputs(
    signals: ComputedSignals, percentiles: dict[str, float]
) -> ScoreInputs:
    return ScoreInputs(
        ticker=signals.ticker,
        sic_sector=signals.sic_sector,
        positives=_positive_subscores(signals, percentiles),
        penalties=_penalties(signals),
        gates=_gates(signals),
    )


def _filter_reason(signals: ComputedSignals, request: ScanRequest) -> str | None:
    """Pre-ranking exclusion reasons from the scan filter flags (None = keep)."""
    if request.exclude_serial_splitter and signals.serial_splitter:
        return "serial reverse-splitter (--exclude-serial-splitter)"
    if request.require_insider_buying and not signals.insider_buying:
        return "no recent insider buying (--require-insider-buying)"
    return None


def _is_flagged(breakdown: ScoreBreakdown) -> bool:
    """A name is 'flagged' if gated or carrying a critical penalty overlay."""
    return breakdown.gated or bool(
        set(breakdown.penalty_contributions) & CRITICAL_PENALTY_MODULES
    )


def _sort_value(breakdown: ScoreBreakdown, sort: str) -> float:
    if sort == "growth":
        return breakdown.positive_contributions.get("growth", 0.0)
    if sort == "valuation":
        return breakdown.positive_contributions.get("valuation", 0.0)
    if sort == "sentiment":
        return breakdown.positive_contributions.get("sentiment", 0.0)
    if sort == "risk":  # least total penalty first
        return -sum(breakdown.penalty_contributions.values())
    return breakdown.composite


def _resort(result: RankedResult, sort: str, top_n: int | None) -> RankedResult:
    if sort == "score":
        return result
    ranked = sorted(result.ranked, key=lambda b: (-_sort_value(b, sort), b.ticker))
    return RankedResult(
        ranked=ranked,
        high_risk=result.high_risk,
        top=ranked[:top_n] if top_n is not None else ranked,
        sector_ranks=result.sector_ranks,
    )


def _stamp_freshness(
    report_freshness: FreshnessReport,
    signals: Sequence[ComputedSignals],
    evidence: Sequence[RawEvidence],
    *,
    now: datetime | None,
    from_cache: bool,
) -> None:
    """Add the filings/news, financials, and 13F as-of stamps."""
    report_freshness.stamp(fresh.filings_news(now, from_cache=from_cache))
    period = next((e.financials_period for e in evidence if e.financials_period), "")
    filed = next((e.financials_filed for e in evidence if e.financials_filed), "")
    if period:
        report_freshness.stamp(
            fresh.financials(period, filed or "n/a", from_cache=from_cache)
        )
    if any(s.insider and s.insider.institutional_accumulation for s in signals):
        report_freshness.stamp(
            fresh.institutional_13f("latest filed", from_cache=from_cache)
        )


def run_scan(
    candidates: Sequence[UniverseCandidate],
    provider: EvidenceProvider,
    request: ScanRequest,
    *,
    universe_counts: dict[str, int] | None = None,
    freshness: FreshnessReport | None = None,
    watchlist: Watchlist | None = None,
    universe_from_cache: bool = False,
    universe_notes: list[str] | None = None,
    now: datetime | None = None,
) -> ScanReport:
    """Run the evidence -> signals -> scoring pipeline over a built universe and
    return a complete report."""
    report_freshness = freshness or FreshnessReport()

    # gather evidence; one ticker's failure never aborts the scan.
    gathered: list[RawEvidence] = []
    failures: list[tuple[str, str]] = []
    for candidate in candidates:
        try:
            gathered.append(provider.gather(candidate))
        except Exception as exc:  # provider-level per-ticker failure (counted)
            failures.append((candidate.ticker, str(exc)))

    # compute every signal, then cross-sectional percentiles.
    signals = [compute_signals(ev, no_news=request.no_news) for ev in gathered]
    percentiles = _percentiles(signals)
    signals_by_ticker = {s.ticker: s for s in signals}

    # score, apply the filter flags, gate, and rank.
    breakdowns: list[ScoreBreakdown] = []
    excluded: list[tuple[str, str]] = []
    for sig in signals:
        reason = _filter_reason(sig, request)
        if reason is not None:
            excluded.append((sig.ticker, reason))
            continue
        breakdown = score_candidate(
            _to_score_inputs(sig, percentiles.get(sig.ticker, {})),
            positive_weights=request.positive_weights,
            penalty_magnitudes=request.penalty_magnitudes,
            preset_bundle=request.preset_bundle,
        )
        if request.exclude_flagged and _is_flagged(breakdown):
            excluded.append((sig.ticker, "critical flag (--exclude-flagged)"))
            continue
        breakdowns.append(breakdown)

    result = _resort(
        rank_candidates(breakdowns, top_n=request.top_n),
        request.sort,
        request.top_n,
    )

    _stamp_freshness(
        report_freshness,
        signals,
        gathered,
        now=now,
        from_cache=universe_from_cache,
    )

    watchlist_alerts: list[str] = []
    if watchlist is not None:
        for breakdown in result.full:
            if watchlist.is_watched(breakdown.ticker):
                flags = sorted(breakdown.penalty_contributions) + breakdown.gate_reasons
                watchlist.record_snapshot(
                    breakdown.ticker, breakdown.composite, flags, now=now
                )
        watchlist_alerts = watchlist.alerts()

    completeness = {
        ticker: sig.completeness
        for ticker, sig in signals_by_ticker.items()
        if sig.completeness
    }
    attributions: list[str] = []
    return ScanReport(
        result=result,
        signals=signals_by_ticker,
        preset_name=request.preset_name,
        profile_name=request.profile_name,
        universe_counts=universe_counts or {},
        universe_from_cache=universe_from_cache,
        freshness_lines=report_freshness.render_lines(),
        failures=failures,
        excluded_by_filter=excluded,
        completeness_flags=completeness,
        watchlist_alerts=watchlist_alerts,
        guardrails=request.guardrails,
        attributions=attributions,
        # Carry the universe-stage notes (e.g. the --sector missing-data /
        # no-match messages) so a narrowed/empty universe is explained.
        notes=list(universe_notes) if universe_notes is not None else [UNIVERSE_NOTE],
    )
