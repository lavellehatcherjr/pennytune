"""Acceptance tests for the evidence gate: no evidence must never outrank real risk.

The ranking engine exists to surface the riskiest names in a set, so a candidate
for which nothing could be fetched must never place above one whose penalties
were actually computed from filings.

The no-evidence candidate here is built with :func:`pennytune.scan.degraded_evidence`,
which is the exact object the live provider returns for a ticker whose CIK cannot
be resolved - i.e. this reproduces the production path, not a synthetic one.
"""

from __future__ import annotations

from pennytune.config import Config
from pennytune.features.insider import InsiderTransaction
from pennytune.features.quant_scores import PeriodFinancials
from pennytune.features.universe import UniverseCandidate
from pennytune.profiles import get_profile
from pennytune.scan import (
    RawEvidence,
    ScanRequest,
    compute_signals,
    degraded_evidence,
    run_scan,
)

_ALL_PROFILES = ("trader", "hold", "high-return", "custom")
_ALL_PRESETS = ("penny", "micro", "small-cap-value", "broad", "custom")


def _distressed_period(scale: float = 1.0) -> PeriodFinancials:
    """A balance sheet deep in the Altman distress zone."""
    return PeriodFinancials(
        total_assets=1000.0 * scale,
        current_assets=200.0 * scale,
        current_liabilities=900.0 * scale,
        cash=10.0 * scale,
        receivables=60.0 * scale,
        inventory=40.0 * scale,
        net_ppe=300.0 * scale,
        gross_ppe=400.0 * scale,
        total_liabilities=1400.0 * scale,
        total_debt=900.0 * scale,
        long_term_debt=700.0 * scale,
        retained_earnings=-800.0 * scale,
        book_equity=-400.0 * scale,
        revenue=500.0 * scale,
        cogs=450.0 * scale,
        sga=200.0 * scale,
        depreciation=40.0 * scale,
        ebit=-150.0 * scale,
        net_income=-200.0 * scale,
        operating_cash_flow=-120.0 * scale,
        capex=20.0 * scale,
        interest_expense=60.0 * scale,
        shares_outstanding=1000.0 * scale,
        goodwill=50.0 * scale,
        intangibles=30.0 * scale,
        goodwill_impairment=None,
        sbc=20.0 * scale,
    )


def _candidate(ticker: str) -> UniverseCandidate:
    return UniverseCandidate(
        ticker=ticker, name=ticker, cik="0000000001", exchange="Nasdaq"
    )


def _evidence_risky(ticker: str) -> RawEvidence:
    """A fully analyzed, genuinely distressed name.

    Shaped like a real micro-cap: one filed period (so Piotroski cannot
    compute), no revenue trend, a distressed balance sheet, insider selling.
    That combination is what makes the inversion visible, because the analyzed
    name loses its two-period positives and carries penalties while a
    no-evidence name keeps a free imputed insider credit.
    """
    return RawEvidence(
        ticker=ticker,
        sic_sector="7830",
        sic_code=7830,
        financials_period="2026-Q1",
        financials_filed="2026-05-09",
        period_t=_distressed_period(),
        period_t1=None,  # one period only -> Piotroski/Beneish suppressed
        revenue_growth=None,  # no revenue trend -> growth suppressed
        insider_transactions=(
            InsiderTransaction("CEO", "S", 200_000, 160_000, "2026-05-20"),
        ),
    )


class _Provider:
    def __init__(self, mapping: dict[str, RawEvidence]) -> None:
        self._mapping = mapping

    def gather(self, candidate: UniverseCandidate) -> RawEvidence:
        return self._mapping[candidate.ticker]


def _request(preset: str = "penny", profile: str = "trader") -> ScanRequest:
    cfg = Config()
    prof = get_profile(profile)
    return ScanRequest(
        preset_name=preset,
        profile_name=profile,
        positive_weights=dict(prof.weights),
        penalty_magnitudes=dict(prof.penalties),
        preset_bundle=cfg.presets[preset].model_dump(),
        guardrails=prof.guardrails,
    )


def _scan(preset: str = "penny", profile: str = "trader"):  # type: ignore[no-untyped-def]
    """Run the production pipeline over one no-evidence and one risky name."""
    nodata_candidate = _candidate("ZZZZNOTAREAL")
    mapping = {
        "ZZZZNOTAREAL": degraded_evidence(nodata_candidate, "no CIK for ZZZZNOTAREAL"),
        "RISKY": _evidence_risky("RISKY"),
    }
    return run_scan(
        [nodata_candidate, _candidate("RISKY")],
        _Provider(mapping),
        _request(preset, profile),
    )


def _composites(report) -> dict[str, float]:  # type: ignore[no-untyped-def]
    return {b.ticker: b.composite for b in report.result.full}


# ---- the acceptance criterion -------------------------------------------------


def test_no_evidence_name_does_not_outrank_analyzed_risky_name() -> None:
    """A name with nothing fetched must not rank above one whose dilution and
    distress penalties were actually computed.
    """
    report = _scan()
    order = [b.ticker for b in report.result.ranked]

    assert "RISKY" in order, "the analyzed name must appear in the ranked list"
    if "ZZZZNOTAREAL" in order:
        assert order.index("RISKY") < order.index("ZZZZNOTAREAL"), (
            f"INVERSION: a name with no evidence outranks an analyzed distressed "
            f"name. ranked order={order}, composites={_composites(report)}"
        )


def test_no_evidence_name_receives_no_positive_credit() -> None:
    """No fetched evidence must yield no positive contribution of any kind.

    The insider sub-score is the easiest leak: mapping an empty transaction
    tuple to neutral pays 0.15 for having no insider record at all.
    """
    report = _scan()
    scored = [b for b in report.result.full if b.ticker == "ZZZZNOTAREAL"]
    if not scored:
        # Preferred outcome: the evidence gate kept it out of the scored set
        # entirely, and said so explicitly rather than dropping it silently.
        reasons = dict(report.excluded_by_filter)
        assert "ZZZZNOTAREAL" in reasons, (
            "a name with no evidence vanished without being reported as excluded"
        )
        assert "not assessed" in reasons["ZZZZNOTAREAL"]
        return
    assert not any(v > 0 for v in scored[0].positive_contributions.values()), (
        f"a name with zero evidence received positive credit: "
        f"{scored[0].positive_contributions}"
    )


def test_no_evidence_signals_do_not_impute_an_insider_subscore() -> None:
    """Unit-level guard on the same leak, at the signal layer."""
    candidate = _candidate("ZZZZNOTAREAL")
    signals = compute_signals(degraded_evidence(candidate, "no CIK"), no_news=False)
    assert signals.insider_subscore in (None, 0.0), (
        f"insider_subscore imputed from an empty transaction list: "
        f"{signals.insider_subscore}"
    )


def test_inversion_holds_across_every_profile_and_preset() -> None:
    """No profile/preset combination avoids the inversion, so none can mask it."""
    failures: list[str] = []
    for profile in _ALL_PROFILES:
        for preset in _ALL_PRESETS:
            report = _scan(preset=preset, profile=profile)
            order = [b.ticker for b in report.result.ranked]
            if "ZZZZNOTAREAL" not in order:
                continue
            if "RISKY" not in order:
                continue
            if order.index("ZZZZNOTAREAL") < order.index("RISKY"):
                failures.append(f"{profile}/{preset}: {order} {_composites(report)}")
    assert not failures, "inversion present in:\n" + "\n".join(failures)


def test_analyzed_healthy_name_still_outranks_analyzed_distressed_name() -> None:
    """Guard against over-correcting: real discrimination must survive."""
    healthy = RawEvidence(
        ticker="HEALTHY",
        sic_sector="7830",
        sic_code=7830,
        financials_period="2026-Q1",
        period_t=PeriodFinancials(
            total_assets=1000.0,
            current_assets=700.0,
            current_liabilities=150.0,
            cash=400.0,
            receivables=120.0,
            inventory=80.0,
            net_ppe=300.0,
            gross_ppe=400.0,
            total_liabilities=250.0,
            total_debt=80.0,
            long_term_debt=60.0,
            retained_earnings=400.0,
            book_equity=750.0,
            revenue=900.0,
            cogs=450.0,
            sga=150.0,
            depreciation=40.0,
            ebit=200.0,
            net_income=150.0,
            operating_cash_flow=180.0,
            capex=30.0,
            interest_expense=8.0,
            shares_outstanding=1000.0,
            goodwill=50.0,
            intangibles=30.0,
            goodwill_impairment=None,
            sbc=20.0,
        ),
        period_t1=None,
        revenue_growth=0.25,
    )
    mapping = {"HEALTHY": healthy, "RISKY": _evidence_risky("RISKY")}
    report = run_scan(
        [_candidate("HEALTHY"), _candidate("RISKY")],
        _Provider(mapping),
        _request(),
    )
    order = [b.ticker for b in report.result.ranked]
    composites = _composites(report)
    assert composites["HEALTHY"] > composites["RISKY"], (
        f"a healthy analyzed name must outrank a distressed analyzed name: "
        f"{composites} order={order}"
    )
