"""End-to-end scan-pipeline tests - fixture-driven, no network.

Exercises :func:`pennytune.scan.run_scan` over a fixture universe + evidence
provider: the full pipeline, composite scoring, preset-aware reweighting (penny
vs broad), profile switching, per-ticker failure isolation, graceful
degradation, the hard gates, and FTD-is-context-not-score.
"""

from __future__ import annotations

import pytest

from pennytune.config import Config
from pennytune.features.delisting import DelistingInputs
from pennytune.features.dilution import DilutionInputs, ShareCountPoint
from pennytune.features.halts import HaltProfile
from pennytune.features.insider import InsiderTransaction
from pennytune.features.quant_scores import PeriodFinancials
from pennytune.features.short_interest import FtdContext
from pennytune.features.universe import UniverseCandidate
from pennytune.profiles import get_profile
from pennytune.scan import (
    RawEvidence,
    ScanRequest,
    compute_signals,
    degraded_evidence,
    run_scan,
)

# ---- fixtures ----------------------------------------------------------------


def _period(
    *, scale: float = 1.0, healthy: bool = True, **kw: float
) -> PeriodFinancials:
    """A fully-populated fiscal period so the quant scores are computable."""
    base: dict[str, float | None] = dict(
        total_assets=1000.0 * scale,
        current_assets=600.0 * scale,
        current_liabilities=200.0 * scale,
        cash=300.0 * scale,
        receivables=120.0 * scale,
        inventory=80.0 * scale,
        net_ppe=300.0 * scale,
        gross_ppe=400.0 * scale,
        total_liabilities=(300.0 if healthy else 950.0) * scale,
        total_debt=(100.0 if healthy else 600.0) * scale,
        long_term_debt=(80.0 if healthy else 500.0) * scale,
        retained_earnings=(200.0 if healthy else -400.0) * scale,
        book_equity=(700.0 if healthy else 50.0) * scale,
        revenue=900.0 * scale,
        cogs=500.0 * scale,
        sga=150.0 * scale,
        depreciation=40.0 * scale,
        ebit=(120.0 if healthy else -60.0) * scale,
        net_income=(90.0 if healthy else -90.0) * scale,
        operating_cash_flow=(110.0 if healthy else -50.0) * scale,
        capex=30.0 * scale,
        interest_expense=10.0 * scale,
        shares_outstanding=1000.0 * scale,
        goodwill=50.0 * scale,
        intangibles=30.0 * scale,
        goodwill_impairment=None,
        sbc=20.0 * scale,
    )
    base.update(kw)
    return PeriodFinancials(**base)


def _candidate(ticker: str) -> UniverseCandidate:
    return UniverseCandidate(
        ticker=ticker, name=ticker, cik="0000000001", exchange="Nasdaq"
    )


def _evidence_good(ticker: str) -> RawEvidence:
    """A cheap, growing, financially healthy name with insider buying."""
    return RawEvidence(
        ticker=ticker,
        sic_sector="3674",
        sic_code=3674,
        market_cap=60_000_000.0,
        current_price=0.80,
        financials_period="2026-Q1",
        financials_filed="2026-05-08",
        period_t=_period(),
        period_t1=_period(scale=0.8),  # smaller a year ago → growth + rising metrics
        revenue_growth=0.35,
        sentiment_compound=0.6,
        insider_transactions=(
            InsiderTransaction("CEO", "P", 100_000, 80_000, "2026-05-20"),
            InsiderTransaction("CFO", "P", 60_000, 48_000, "2026-05-21"),
            InsiderTransaction("DIR", "P", 40_000, 32_000, "2026-05-22"),
        ),
    )


def _evidence_weak(ticker: str) -> RawEvidence:
    """An expensive, distressed name (high EV/Sales, distress Z″, no insider buys)."""
    return RawEvidence(
        ticker=ticker,
        sic_sector="3674",
        sic_code=3674,
        market_cap=250_000_000.0,  # same micro bucket as GOOD, but pricier per $ sales
        current_price=0.40,
        financials_period="2026-Q1",
        financials_filed="2026-05-09",
        period_t=_period(healthy=False),
        period_t1=_period(healthy=False, scale=1.1),  # shrinking
        revenue_growth=-0.20,
        sentiment_compound=-0.4,
        insider_transactions=(
            InsiderTransaction("CEO", "S", 200_000, 160_000, "2026-05-20"),
        ),
    )


def _evidence_upmarket_and_delisting(ticker: str) -> RawEvidence:
    """Carries BOTH a penny-native penalty (delisting) and up-market overlays."""
    period = _period(
        healthy=False,
        goodwill_impairment=120.0,  # → goodwill-impairment flag
        total_debt=800.0,
        long_term_debt=700.0,
        cash=10.0,
        ebit=20.0,
        interest_expense=40.0,  # coverage < 1.5 → weak-interest-coverage
        sbc=200.0,  # sbc/revenue > 0.10 → high-sbc-dilution
        revenue=900.0,
    )
    return RawEvidence(
        ticker=ticker,
        sic_sector="3674",
        sic_code=3674,
        market_cap=70_000_000.0,
        current_price=0.30,
        period_t=period,
        period_t1=_period(healthy=False),
        revenue_growth=-0.05,
        delisting=DelistingInputs(current_price=0.30, deficiency_notice=True),
    )


class FixtureProvider:
    """Evidence provider backed by a fixture map; unknown tickers raise (→ failure)."""

    def __init__(self, mapping: dict[str, RawEvidence]) -> None:
        self._mapping = mapping

    def gather(self, candidate: UniverseCandidate) -> RawEvidence:
        evidence = self._mapping.get(candidate.ticker)
        if evidence is None:
            raise KeyError(f"no evidence for {candidate.ticker}")
        return evidence


def _request(preset: str = "penny", profile: str = "hold", **kw: object) -> ScanRequest:
    cfg = Config()
    prof = get_profile(profile)
    bundle = cfg.presets[preset].model_dump()
    return ScanRequest(
        preset_name=preset,
        profile_name=profile,
        positive_weights=dict(prof.weights),
        penalty_magnitudes=dict(prof.penalties),
        preset_bundle=bundle,
        guardrails=prof.guardrails,
        **kw,  # type: ignore[arg-type]
    )


# ---- end-to-end ranked list --------------------------------------------------


def test_end_to_end_ranked_list_is_sane() -> None:
    candidates = [_candidate("GOOD"), _candidate("WEAK")]
    provider = FixtureProvider(
        {"GOOD": _evidence_good("GOOD"), "WEAK": _evidence_weak("WEAK")}
    )
    report = run_scan(candidates, provider, _request())

    assert report.scanned == 2
    assert not report.failures
    tickers = [b.ticker for b in report.result.ranked]
    # The cheap/strong/insider-buying name outranks the expensive/distressed one.
    assert tickers[0] == "GOOD"
    good = report.result.ranked[0]
    assert good.positive_contributions["valuation"] > 0
    assert good.positive_contributions["insider"] > 0
    # The weak name carries a distress penalty (Altman distress zone).
    weak = next(b for b in report.result.ranked if b.ticker == "WEAK")
    assert "distress" in weak.penalty_contributions


def test_reproducible_given_same_inputs() -> None:
    candidates = [_candidate("GOOD"), _candidate("WEAK")]
    mapping = {"GOOD": _evidence_good("GOOD"), "WEAK": _evidence_weak("WEAK")}
    first = run_scan(candidates, FixtureProvider(mapping), _request())
    second = run_scan(candidates, FixtureProvider(mapping), _request())
    assert [b.ticker for b in first.result.ranked] == [
        b.ticker for b in second.result.ranked
    ]
    assert [round(b.composite, 6) for b in first.result.ranked] == [
        round(b.composite, 6) for b in second.result.ranked
    ]


# ---- preset-aware reweighting (penny-native vs up-market) --------------------


def test_penny_vs_broad_reweights_risk_modules() -> None:
    candidates = [_candidate("RISK")]
    provider = FixtureProvider({"RISK": _evidence_upmarket_and_delisting("RISK")})

    penny = run_scan(candidates, provider, _request(preset="penny")).result
    broad = run_scan(candidates, provider, _request(preset="broad")).result
    penny_b = penny.full[0]
    broad_b = broad.full[0]

    # Penny: the penny-native delisting penalty is live; up-market modules are
    # dormant - shown as "n/a for this preset", never a silent pass.
    assert "delisting" in penny_b.penalty_contributions
    assert "goodwill_impairment" in penny_b.na_modules
    assert "goodwill_impairment" not in penny_b.penalty_contributions

    # Broad: up-market overlays weight in; the penny-native delisting penalty is
    # de-emphasized (preset weight 0.1 → a smaller contribution than under penny).
    assert "goodwill_impairment" in broad_b.penalty_contributions
    assert (
        broad_b.penalty_contributions["delisting"]
        < penny_b.penalty_contributions["delisting"]
    )


# ---- profile switching changes the ranking -----------------------------------


def test_profiles_change_rankings() -> None:
    # SENT: strong sentiment, thin growth; VALU: cheap + strong growth, low sentiment.
    sent = RawEvidence(
        ticker="SENT",
        sic_sector="3674",
        sic_code=3674,
        market_cap=200_000_000.0,
        period_t=_period(),
        period_t1=_period(scale=0.95),
        revenue_growth=0.05,
        sentiment_compound=0.95,
    )
    valu = RawEvidence(
        ticker="VALU",
        sic_sector="3674",
        sic_code=3674,
        market_cap=60_000_000.0,  # same micro bucket as SENT, cheaper per $ sales
        period_t=_period(),
        period_t1=_period(scale=0.8),
        revenue_growth=0.30,
        sentiment_compound=-0.1,
    )
    candidates = [_candidate("SENT"), _candidate("VALU")]
    provider = FixtureProvider({"SENT": sent, "VALU": valu})

    trader = run_scan(candidates, provider, _request(profile="trader")).result
    hold = run_scan(candidates, provider, _request(profile="hold")).result

    # The two profiles weight sentiment vs valuation/health differently, so the
    # SENT-vs-VALU gap moves - proving the weighting actually changes outcomes.
    trader_lookup = {b.ticker: b.composite for b in trader.ranked}
    hold_lookup = {b.ticker: b.composite for b in hold.ranked}
    trader_gap = trader_lookup["SENT"] - trader_lookup["VALU"]
    hold_gap = hold_lookup["SENT"] - hold_lookup["VALU"]
    assert trader_gap > hold_gap  # trader favors SENT more than hold does


def test_high_return_profile_carries_guardrails() -> None:
    report = run_scan(
        [_candidate("GOOD")],
        FixtureProvider({"GOOD": _evidence_good("GOOD")}),
        _request(profile="high-return"),
    )
    assert report.guardrails
    assert any("pump-and-dump" in g for g in report.guardrails)


# ---- hard gates --------------------------------------------------------------


def test_active_suspension_gates_to_high_risk() -> None:
    evidence = _evidence_good("SUSP")
    evidence.halt = HaltProfile(tier="suspended", hard_exclude=True)
    report = run_scan(
        [_candidate("SUSP")],
        FixtureProvider({"SUSP": evidence}),
        _request(),
    )
    assert not report.result.ranked
    assert [b.ticker for b in report.result.high_risk] == ["SUSP"]
    assert report.result.high_risk[0].gated


def test_disclosed_determination_gates() -> None:
    evidence = _evidence_good("DELI")
    evidence.delisting = DelistingInputs(determination_disclosed=True)
    report = run_scan(
        [_candidate("DELI")],
        FixtureProvider({"DELI": evidence}),
        _request(),
    )
    assert report.result.high_risk and report.result.high_risk[0].ticker == "DELI"


# ---- fails-to-deliver is context only (never scored) -------------------------


def test_ftd_is_context_not_scored() -> None:
    evidence = _evidence_good("GOOD")
    evidence.ftd = FtdContext(present=True, persistent=True, window_count=2)
    report = run_scan(
        [_candidate("GOOD")],
        FixtureProvider({"GOOD": evidence}),
        _request(),
    )
    breakdown = report.result.full[0]
    assert "short_interest" not in breakdown.penalty_contributions
    assert "short_interest_ftd" not in breakdown.penalty_contributions
    # …but the FTD settlement-stress context is retained for inspect/export.
    assert report.signals["GOOD"].ftd is not None


# ---- resilience: one failure never aborts the scan ---------------------------


def test_one_ticker_failure_does_not_abort() -> None:
    candidates = [_candidate("GOOD"), _candidate("MISSING")]
    provider = FixtureProvider({"GOOD": _evidence_good("GOOD")})  # MISSING absent
    report = run_scan(candidates, provider, _request())
    assert report.scanned == 1
    assert [t for t, _ in report.failures] == ["MISSING"]
    assert [b.ticker for b in report.result.ranked] == ["GOOD"]


def test_partial_failure_threshold() -> None:
    # 3 of 4 fail (>25%) → partial-failure signal, but results still produced.
    candidates = [_candidate(t) for t in ("GOOD", "A", "B", "C")]
    provider = FixtureProvider({"GOOD": _evidence_good("GOOD")})
    report = run_scan(candidates, provider, _request())
    assert report.partial_failure
    assert report.scanned == 1


# ---- graceful degradation: provider down → completeness flag -----------------


def test_degraded_evidence_still_completes_with_flag() -> None:
    candidate = _candidate("DOWN")

    class DownProvider:
        def gather(self, c: UniverseCandidate) -> RawEvidence:
            return degraded_evidence(c, "provider down")

    report = run_scan([candidate], DownProvider(), _request())
    assert report.scanned == 1  # still produced a result
    assert "DOWN" in report.completeness_flags
    assert any("degraded" in f for f in report.completeness_flags["DOWN"])


def test_compute_signals_suppresses_missing_inputs() -> None:
    # Suppress-not-impute: a name with no fundamentals scores no positives, flagged.
    signals = compute_signals(
        RawEvidence(ticker="BARE", news_available=False), no_news=False
    )
    assert signals.ev_to_sales is None
    assert signals.altman_z is None
    assert signals.sentiment_subscore is None
    assert any("suppressed" in note for note in signals.completeness)


# ---- --top and --sort --------------------------------------------------------


def test_top_n_limits_display_but_exports_full_set() -> None:
    candidates = [_candidate("GOOD"), _candidate("WEAK")]
    provider = FixtureProvider(
        {"GOOD": _evidence_good("GOOD"), "WEAK": _evidence_weak("WEAK")}
    )
    report = run_scan(candidates, provider, _request(top_n=1))
    assert len(report.result.top) == 1
    assert len(report.result.full) == 2  # full set always available for export


def test_sort_by_valuation() -> None:
    candidates = [_candidate("GOOD"), _candidate("WEAK")]
    provider = FixtureProvider(
        {"GOOD": _evidence_good("GOOD"), "WEAK": _evidence_weak("WEAK")}
    )
    report = run_scan(candidates, provider, _request(sort="valuation"))
    valuations = [
        b.positive_contributions.get("valuation", 0.0) for b in report.result.ranked
    ]
    assert valuations == sorted(valuations, reverse=True)


# ---- filter flags ------------------------------------------------------------


def test_require_insider_buying_filters() -> None:
    candidates = [_candidate("GOOD"), _candidate("WEAK")]
    provider = FixtureProvider(
        {"GOOD": _evidence_good("GOOD"), "WEAK": _evidence_weak("WEAK")}
    )
    report = run_scan(candidates, provider, _request(require_insider_buying=True))
    kept = {b.ticker for b in report.result.full}
    assert "GOOD" in kept  # cluster code-P buying
    assert "WEAK" not in kept
    assert any(t == "WEAK" for t, _ in report.excluded_by_filter)


def test_no_news_suppresses_sentiment() -> None:
    report = run_scan(
        [_candidate("GOOD")],
        FixtureProvider({"GOOD": _evidence_good("GOOD")}),
        _request(no_news=True),
    )
    breakdown = report.result.full[0]
    assert breakdown.positive_contributions["sentiment"] == 0.0


def test_exclude_flagged_drops_critical_and_gated() -> None:
    suspended = _evidence_good("SUSP")
    suspended.halt = HaltProfile(tier="suspended", hard_exclude=True)  # → a hard gate
    candidates = [_candidate("GOOD"), _candidate("WEAK"), _candidate("SUSP")]
    provider = FixtureProvider(
        {
            "GOOD": _evidence_good("GOOD"),  # clean
            "WEAK": _evidence_weak("WEAK"),  # distress = a critical penalty
            "SUSP": suspended,  # gated
        }
    )
    report = run_scan(candidates, provider, _request(exclude_flagged=True))
    kept = {b.ticker for b in report.result.full}
    assert kept == {"GOOD"}
    excluded = {t for t, _ in report.excluded_by_filter}
    assert {"WEAK", "SUSP"} <= excluded


def test_exclude_serial_splitter_filters() -> None:
    splitter = _evidence_good("SPLT")
    splitter.dilution = DilutionInputs(
        share_series=[
            ShareCountPoint("2024-12-31", 100_000_000),
            ShareCountPoint("2025-06-30", 10_000_000),  # 1-for-10
            ShareCountPoint("2025-09-30", 40_000_000),  # re-dilution after
            ShareCountPoint("2026-03-31", 8_000_000),  # 1-for-5 → serial
        ]
    )
    candidates = [_candidate("GOOD"), _candidate("SPLT")]
    provider = FixtureProvider({"GOOD": _evidence_good("GOOD"), "SPLT": splitter})
    report = run_scan(candidates, provider, _request(exclude_serial_splitter=True))
    kept = {b.ticker for b in report.result.full}
    assert "SPLT" not in kept
    assert "GOOD" in kept


def test_sort_by_risk_and_default_score() -> None:
    candidates = [_candidate("GOOD"), _candidate("WEAK")]
    provider = FixtureProvider(
        {"GOOD": _evidence_good("GOOD"), "WEAK": _evidence_weak("WEAK")}
    )
    by_risk = run_scan(candidates, provider, _request(sort="risk")).result.ranked
    # "risk" = least total penalty first → the clean name leads the distressed one.
    assert by_risk[0].ticker == "GOOD"
    risk_keys = [-sum(b.penalty_contributions.values()) for b in by_risk]
    assert risk_keys == sorted(risk_keys, reverse=True)
    by_score = run_scan(candidates, provider, _request(sort="score")).result.ranked
    composites = [b.composite for b in by_score]
    assert composites == sorted(composites, reverse=True)


def test_universe_notes_surface_in_report() -> None:
    # Universe-stage notes travel into the report so universe provenance (e.g. a
    # cache-only fallback) is explained rather than silent.
    report = run_scan(
        [_candidate("GOOD")],
        FixtureProvider({"GOOD": _evidence_good("GOOD")}),
        _request(),
        universe_notes=["universe note", "cache-only: no cached universe"],
    )
    assert any("cache-only" in note for note in report.notes)


# ---- watchlist alert banner --------------------------------------------------


def test_watchlist_alerts_surface(tmp_path: pytest.TempPathFactory) -> None:
    from pennytune.features.watchlist import Watchlist

    db = tmp_path / "wl.db"  # type: ignore[operator]
    wl = Watchlist(db_path=db)
    try:
        wl.add(["GOOD"])
        # Seed a prior high snapshot so this scan's lower score triggers an alert.
        wl.record_snapshot("GOOD", 99.0, [])
        report = run_scan(
            [_candidate("GOOD")],
            FixtureProvider({"GOOD": _evidence_good("GOOD")}),
            _request(),
            watchlist=wl,
        )
        assert any("GOOD" in alert for alert in report.watchlist_alerts)
    finally:
        wl.close()
