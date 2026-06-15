"""Quantitative scoring: distress, earnings quality, strength & valuation.

Pure pandas/numpy math on the EDGAR financial-statement line items the
fundamentals pipeline already pulls (plus market cap from the profile feed).
No new data sources. The scan/inspect composite consumes Altman Z″ (with the
Altman→bond-rating mapping), Beneish M (+ 8 sub-indices), Piotroski F, EV/FCF
valuation (tier-safe), the up-market risk modules, and sector/size-relative
percentiles. Dechow F (Model 1), Montier C, Sloan accruals, and
cash-runway/financing-cliff are implemented and unit-tested but not wired into
the composite.

SUPPRESS, DO NOT IMPUTE: when a required input is missing/zero/invalid the
affected score is suppressed and marked incomplete - never computed with zeros
imputed. Each result carries a data-completeness indicator and these models are
weighted signals with labeled limitations, never hard gates (approximate for
micro-caps - confirm in filings).

Verified constants (2026-06-12): Beneish coefficients + 8 sub-indices; Dechow
Model-1 logit + 0.0037 base rate; Altman Z″ (non-manufacturer) with the BRE
mapping taken on the Emerging-Market scale (EMS = Z″ + 3.25).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

__all__ = [
    "PeriodFinancials",
    "ScoreResult",
    "MODELS_CAVEAT",
    "altman_z",
    "altman_bre",
    "beneish_m",
    "dechow_f",
    "montier_c",
    "piotroski_f",
    "accruals",
    "cash_runway",
    "ev_valuation",
    "up_market_modules",
    "is_financials_sic",
    "sector_size_percentiles",
    "ebitda",
    "adjusted_ebitda",
]

MODELS_CAVEAT = "models approximate for micro-caps — confirm in filings"
_DECHOW_BASE_RATE = 0.0037
_BENEISH_FLAG = -1.78


@dataclass
class PeriodFinancials:
    """One fiscal period's XBRL line items (any may be None → suppressed)."""

    total_assets: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    cash: float | None = None
    receivables: float | None = None
    inventory: float | None = None
    net_ppe: float | None = None
    gross_ppe: float | None = None
    total_liabilities: float | None = None
    total_debt: float | None = None
    long_term_debt: float | None = None
    retained_earnings: float | None = None
    book_equity: float | None = None
    revenue: float | None = None
    cogs: float | None = None
    sga: float | None = None
    depreciation: float | None = None
    ebit: float | None = None
    net_income: float | None = None
    operating_cash_flow: float | None = None
    capex: float | None = None
    interest_expense: float | None = None
    shares_outstanding: float | None = None
    goodwill: float | None = None
    intangibles: float | None = None
    goodwill_impairment: float | None = None
    sbc: float | None = None
    operating_lease_expense: float | None = None  # post-ASC842 lease addback
    pension_expense: float | None = None  # pension/OPEB adjustment


@dataclass
class ScoreResult:
    name: str
    value: float | None = None
    computable: bool = False
    components: dict[str, float] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    note: str = ""


def _missing(**fields: float | None) -> list[str]:
    return [name for name, value in fields.items() if value is None]


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def ebitda(period: PeriodFinancials) -> float | None:
    if period.ebit is None or period.depreciation is None:
        return None
    return period.ebit + period.depreciation


def adjusted_ebitda(period: PeriodFinancials) -> float | None:
    """EBITDA adjusted for operating-lease and pension expense.

    Post-ASC842/IFRS16, capitalized operating leases and pension items make
    raw EV/EBITDA non-comparable across capital structures; this adds them back.
    Returns ``None`` unless EBITDA is computable AND at least one adjustment is
    present (suppress-not-impute - never fabricate a zero adjustment).
    """
    base = ebitda(period)
    if base is None:
        return None
    lease, pension = period.operating_lease_expense, period.pension_expense
    if lease is None and pension is None:
        return None
    return base + (lease or 0.0) + (pension or 0.0)


def _debt(period: PeriodFinancials) -> float | None:
    if period.total_debt is not None:
        return period.total_debt
    return period.long_term_debt


# ---- Altman Z'' + bond-rating equivalent ------------------------------------

# BRE table on the Emerging-Market scale (EMS = Z'' + 3.25): (min_ems, rating, pd_tier).
_BRE_TABLE: tuple[tuple[float, str, str], ...] = (
    (8.15, "AAA", "minimal"),
    (7.60, "AA", "minimal"),
    (7.00, "AA-", "low"),
    (6.40, "A", "low"),
    (5.85, "BBB", "moderate"),
    (5.65, "BBB-", "moderate"),
    (5.25, "BB+", "speculative"),
    (4.95, "BB", "speculative"),
    (4.50, "B+", "high"),
    (4.15, "B", "high"),
    (3.75, "B-", "high"),
    (3.20, "CCC+", "distressed"),
    (2.50, "CCC", "distressed"),
    (1.75, "CCC-", "distressed"),
    (float("-inf"), "D", "default"),
)


def altman_bre(z_double_prime: float) -> tuple[str, str]:
    """Map Z'' to a bond-rating equivalent + PD tier (on EMS = Z'' + 3.25)."""
    ems = z_double_prime + 3.25
    for threshold, rating, pd_tier in _BRE_TABLE:
        if ems >= threshold:
            return rating, pd_tier
    return "D", "default"


def altman_z(period: PeriodFinancials) -> ScoreResult:
    """Altman Z''-Score (non-manufacturer): zones + BRE/PD (secondary flags)."""
    missing = _missing(
        current_assets=period.current_assets,
        current_liabilities=period.current_liabilities,
        retained_earnings=period.retained_earnings,
        ebit=period.ebit,
        total_assets=period.total_assets,
        book_equity=period.book_equity,
        total_liabilities=period.total_liabilities,
    )
    if missing or not period.total_assets or not period.total_liabilities:
        return ScoreResult(
            "altman_z",
            missing=missing or ["total_assets/total_liabilities"],
            note="suppressed",
        )
    assert period.current_assets is not None and period.current_liabilities is not None
    assert period.retained_earnings is not None and period.ebit is not None
    assert period.book_equity is not None
    wc = period.current_assets - period.current_liabilities
    x1 = wc / period.total_assets
    x2 = period.retained_earnings / period.total_assets
    x3 = period.ebit / period.total_assets
    x4 = period.book_equity / period.total_liabilities
    z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
    zone = "distress" if z < 1.1 else "safe" if z > 2.6 else "grey"
    rating, pd_tier = altman_bre(z)
    return ScoreResult(
        "altman_z",
        value=z,
        computable=True,
        components={"X1_WC_TA": x1, "X2_RE_TA": x2, "X3_EBIT_TA": x3, "X4_BE_TL": x4},
        flags=[f"zone:{zone}", f"BRE:{rating}", f"PD:{pd_tier}"],
        note=MODELS_CAVEAT,
    )


# ---- Beneish M-Score + 8 sub-indices ----------------------------------------


def beneish_m(t: PeriodFinancials, t1: PeriodFinancials) -> ScoreResult:
    """Beneish M-Score; surfaces all 8 sub-indices as components."""
    dsri = _ratio(_ratio(t.receivables, t.revenue), _ratio(t1.receivables, t1.revenue))
    gm_t = _ratio(
        (t.revenue - t.cogs)
        if (t.revenue is not None and t.cogs is not None)
        else None,
        t.revenue,
    )
    gm_t1 = _ratio(
        (t1.revenue - t1.cogs)
        if (t1.revenue is not None and t1.cogs is not None)
        else None,
        t1.revenue,
    )
    gmi = _ratio(gm_t1, gm_t)
    aq_t = _soft_asset_ratio(t)
    aq_t1 = _soft_asset_ratio(t1)
    aqi = _ratio(aq_t, aq_t1)
    sgi = _ratio(t.revenue, t1.revenue)
    depi = _ratio(_dep_rate(t1), _dep_rate(t))
    sgai = _ratio(_ratio(t.sga, t.revenue), _ratio(t1.sga, t1.revenue))
    lvgi = _ratio(_leverage(t), _leverage(t1))
    tata = _ratio(
        (t.net_income - t.operating_cash_flow)
        if (t.net_income is not None and t.operating_cash_flow is not None)
        else None,
        t.total_assets,
    )

    indices = {
        "DSRI": dsri,
        "GMI": gmi,
        "AQI": aqi,
        "SGI": sgi,
        "DEPI": depi,
        "SGAI": sgai,
        "LVGI": lvgi,
        "TATA": tata,
    }
    missing = [name for name, value in indices.items() if value is None]
    if missing:
        return ScoreResult(
            "beneish_m", missing=missing, note="suppressed (needs 2 periods)"
        )
    assert dsri is not None and gmi is not None and aqi is not None and sgi is not None
    assert (
        depi is not None and sgai is not None and lvgi is not None and tata is not None
    )
    m = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )
    flags = ["possible-manipulation"] if m > _BENEISH_FLAG else []
    return ScoreResult(
        "beneish_m",
        value=m,
        computable=True,
        components={
            "DSRI": dsri,
            "GMI": gmi,
            "AQI": aqi,
            "SGI": sgi,
            "DEPI": depi,
            "SGAI": sgai,
            "LVGI": lvgi,
            "TATA": tata,
        },
        flags=flags,
        note=MODELS_CAVEAT,
    )


def _soft_asset_ratio(p: PeriodFinancials) -> float | None:
    if p.current_assets is None or p.net_ppe is None or not p.total_assets:
        return None
    return 1.0 - (p.current_assets + p.net_ppe) / p.total_assets


def _dep_rate(p: PeriodFinancials) -> float | None:
    if p.depreciation is None or p.net_ppe is None:
        return None
    denominator = p.depreciation + p.net_ppe
    return p.depreciation / denominator if denominator else None


def _leverage(p: PeriodFinancials) -> float | None:
    if p.current_liabilities is None or p.long_term_debt is None or not p.total_assets:
        return None
    return (p.current_liabilities + p.long_term_debt) / p.total_assets


# ---- Dechow F-Score (Model 1) -----------------------------------------------


def dechow_f(
    t: PeriodFinancials, t1: PeriodFinancials, t2: PeriodFinancials, *, issuance: bool
) -> ScoreResult:
    """Dechow et al. F-Score (Model 1): probability of misstatement / base rate."""
    avg_ta = _avg(t.total_assets, t1.total_assets)
    avg_ta_prior = _avg(t1.total_assets, t2.total_assets)
    noa_t = _noa(t)
    noa_t1 = _noa(t1)
    rsst = _ratio(_sub(noa_t, noa_t1), avg_ta)
    d_rec = _ratio(_sub(t.receivables, t1.receivables), avg_ta)
    d_inv = _ratio(_sub(t.inventory, t1.inventory), avg_ta)
    soft = (
        (t.total_assets - t.net_ppe - t.cash) / t.total_assets
        if (t.total_assets and t.net_ppe is not None and t.cash is not None)
        else None
    )
    cash_sales_t = _cash_sales(t.revenue, t.receivables, t1.receivables)
    cash_sales_t1 = _cash_sales(t1.revenue, t1.receivables, t2.receivables)
    d_cash_sales = _ratio(_sub(cash_sales_t, cash_sales_t1), cash_sales_t1)
    roa_t = _ratio(t.net_income, avg_ta)
    roa_t1 = _ratio(t1.net_income, avg_ta_prior)
    d_roa = _sub(roa_t, roa_t1)

    required = {
        "rsst": rsst,
        "d_receivables": d_rec,
        "d_inventory": d_inv,
        "soft_assets": soft,
        "d_cash_sales": d_cash_sales,
        "d_roa": d_roa,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        return ScoreResult(
            "dechow_f", missing=missing, note="suppressed (needs t-2 history)"
        )
    assert rsst is not None and d_rec is not None and d_inv is not None
    assert soft is not None and d_cash_sales is not None and d_roa is not None
    logit = (
        -7.893
        + 0.790 * rsst
        + 2.518 * d_rec
        + 1.191 * d_inv
        + 1.979 * soft
        + 0.171 * d_cash_sales
        - 0.932 * d_roa
        + 1.029 * (1.0 if issuance else 0.0)
    )
    prob = math.exp(logit) / (1.0 + math.exp(logit))
    f_score = prob / _DECHOW_BASE_RATE
    flags = []
    if f_score > 2.45:
        flags.append("misstatement-risk-high")
    elif f_score > 1.85:
        flags.append("misstatement-risk-substantial")
    elif f_score > 1.00:
        flags.append("misstatement-risk-above-normal")
    return ScoreResult(
        "dechow_f",
        value=f_score,
        computable=True,
        components={
            "probability": prob,
            "issuance": 1.0 if issuance else 0.0,
            "rsst": rsst,
            "d_receivables": d_rec,
            "d_inventory": d_inv,
            "soft_assets": soft,
            "d_cash_sales": d_cash_sales,
            "d_roa": d_roa,
        },
        flags=flags,
        note=MODELS_CAVEAT,
    )


def _avg(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return (a + b) / 2


def _sub(a: float | None, b: float | None) -> float | None:
    return a - b if (a is not None and b is not None) else None


def _noa(p: PeriodFinancials) -> float | None:
    debt = _debt(p)
    if (
        p.total_assets is None
        or p.cash is None
        or p.total_liabilities is None
        or debt is None
    ):
        return None
    return (p.total_assets - p.cash) - (p.total_liabilities - debt)


def _cash_sales(
    revenue: float | None, ar_t: float | None, ar_prev: float | None
) -> float | None:
    if revenue is None or ar_t is None or ar_prev is None:
        return None
    return revenue - (ar_t - ar_prev)


# ---- Montier C-Score (0-6) --------------------------------------------------


def montier_c(
    t: PeriodFinancials, t1: PeriodFinancials, *, asset_growth_threshold: float = 0.10
) -> ScoreResult:
    """Montier C-Score: 0-6 "cooking the books" checklist with the lit flags."""
    checks: dict[str, bool | None] = {
        "ni_ocf_divergence_growing": _gt(
            _sub(t.net_income, t.operating_cash_flow),
            _sub(t1.net_income, t1.operating_cash_flow),
        ),
        "dso_rising": _gt(
            _ratio(t.receivables, t.revenue), _ratio(t1.receivables, t1.revenue)
        ),
        "dsi_rising": _gt(_ratio(t.inventory, t.cogs), _ratio(t1.inventory, t1.cogs)),
        "ca_to_revenue_rising": _gt(
            _ratio(t.current_assets, t.revenue), _ratio(t1.current_assets, t1.revenue)
        ),
        "depreciation_declining": _lt(_dep_rate_gross(t), _dep_rate_gross(t1)),
        "high_asset_growth": _asset_growth_high(
            t.total_assets, t1.total_assets, asset_growth_threshold
        ),
    }
    missing = [name for name, value in checks.items() if value is None]
    if missing:
        return ScoreResult(
            "montier_c", missing=missing, note="suppressed (needs 2 periods)"
        )
    lit = {name: bool(value) for name, value in checks.items()}
    score = sum(lit.values())
    return ScoreResult(
        "montier_c",
        value=float(score),
        computable=True,
        components={name: 1.0 if v else 0.0 for name, v in lit.items()},
        flags=[name for name, v in lit.items() if v],
        note=MODELS_CAVEAT,
    )


def _gt(a: float | None, b: float | None) -> bool | None:
    return (a > b) if (a is not None and b is not None) else None


def _lt(a: float | None, b: float | None) -> bool | None:
    return (a < b) if (a is not None and b is not None) else None


def _dep_rate_gross(p: PeriodFinancials) -> float | None:
    return _ratio(p.depreciation, p.gross_ppe)


def _asset_growth_high(
    ta_t: float | None, ta_t1: float | None, threshold: float
) -> bool | None:
    growth = _ratio(_sub(ta_t, ta_t1), ta_t1)
    return (growth > threshold) if growth is not None else None


# ---- Piotroski F-Score (0-9) ------------------------------------------------


def piotroski_f(t: PeriodFinancials, t1: PeriodFinancials) -> ScoreResult:
    """Piotroski F-Score (0-9): a value-universe signal (labeled)."""
    roa_t = _ratio(t.net_income, t.total_assets)
    roa_t1 = _ratio(t1.net_income, t1.total_assets)
    checks: dict[str, bool | None] = {
        "positive_net_income": (t.net_income > 0) if t.net_income is not None else None,
        "positive_ocf": (t.operating_cash_flow > 0)
        if t.operating_cash_flow is not None
        else None,
        "roa_improved": _gt(roa_t, roa_t1),
        "ocf_gt_net_income": _gt(t.operating_cash_flow, t.net_income),
        "leverage_decreased": _lt(
            _ratio(t.long_term_debt, t.total_assets),
            _ratio(t1.long_term_debt, t1.total_assets),
        ),
        "current_ratio_improved": _gt(
            _ratio(t.current_assets, t.current_liabilities),
            _ratio(t1.current_assets, t1.current_liabilities),
        ),
        "no_share_increase": _le(t.shares_outstanding, t1.shares_outstanding),
        "gross_margin_improved": _gt(_gross_margin(t), _gross_margin(t1)),
        "asset_turnover_improved": _gt(
            _ratio(t.revenue, t.total_assets), _ratio(t1.revenue, t1.total_assets)
        ),
    }
    missing = [name for name, value in checks.items() if value is None]
    if missing:
        return ScoreResult(
            "piotroski_f", missing=missing, note="suppressed (needs 2 periods)"
        )
    lit = {name: bool(value) for name, value in checks.items()}
    score = sum(lit.values())
    flags = ["value-universe-signal"]
    if score >= 7:
        flags.append("strong")
    elif score <= 2:
        flags.append("weak")
    return ScoreResult(
        "piotroski_f",
        value=float(score),
        computable=True,
        components={name: 1.0 if v else 0.0 for name, v in lit.items()},
        flags=flags,
        note=MODELS_CAVEAT,
    )


def _le(a: float | None, b: float | None) -> bool | None:
    return (a <= b) if (a is not None and b is not None) else None


def _gross_margin(p: PeriodFinancials) -> float | None:
    if p.revenue is None or p.cogs is None or not p.revenue:
        return None
    return (p.revenue - p.cogs) / p.revenue


# ---- accruals (ratio + Sloan both forms) ------------------------------------


def accruals(t: PeriodFinancials, t1: PeriodFinancials) -> ScoreResult:
    """Accruals ratio + Sloan (1996) balance-sheet and cash-flow forms."""
    ni_minus_ocf = _sub(t.net_income, t.operating_cash_flow)
    ratio = _ratio(ni_minus_ocf, t.total_assets)
    avg_ta = _avg(t.total_assets, t1.total_assets)
    sloan_cf = _ratio(ni_minus_ocf, avg_ta)
    ncwc_t = _noncash_wc(t)
    ncwc_t1 = _noncash_wc(t1)
    sloan_bs = _ratio(
        _sub(_sub(ncwc_t, ncwc_t1), t.depreciation)
        if t.depreciation is not None
        else None,
        avg_ta,
    )
    components: dict[str, float] = {}
    if ratio is not None:
        components["accruals_ratio"] = ratio
    if sloan_cf is not None:
        components["sloan_cash_flow"] = sloan_cf
    if sloan_bs is not None:
        components["sloan_balance_sheet"] = sloan_bs
    if ratio is None:
        return ScoreResult(
            "accruals",
            missing=["net_income/operating_cash_flow/total_assets"],
            note="suppressed",
        )
    flags = ["high-accruals"] if ratio > 0.10 else []
    return ScoreResult(
        "accruals",
        value=ratio,
        computable=True,
        components=components,
        flags=flags,
        note=MODELS_CAVEAT,
    )


def _noncash_wc(p: PeriodFinancials) -> float | None:
    if p.current_assets is None or p.cash is None or p.current_liabilities is None:
        return None
    return (p.current_assets - p.cash) - p.current_liabilities


# ---- cash runway / financing cliff ------------------------------------------


def cash_runway(
    cash: float | None,
    quarterly_ocf: float | None,
    *,
    prior_quarterly_ocf: float | None = None,
    going_concern: bool = False,
    cliff_quarters: float = 4.0,
) -> ScoreResult:
    """Cash runway (quarters) + burn-deterioration → financing-cliff score."""
    if cash is None or quarterly_ocf is None:
        return ScoreResult(
            "cash_runway", missing=["cash/quarterly_ocf"], note="suppressed"
        )
    if quarterly_ocf >= 0:
        return ScoreResult(
            "cash_runway",
            value=math.inf,
            computable=True,
            flags=["cash-generating"],
            note=MODELS_CAVEAT,
        )
    burn = -quarterly_ocf
    runway = cash / burn
    flags: list[str] = []
    deterioration = (
        prior_quarterly_ocf is not None
        and prior_quarterly_ocf < 0
        and burn > -prior_quarterly_ocf
    )
    if deterioration:
        flags.append("burn-accelerating")
    financing_cliff = going_concern or runway < cliff_quarters
    if financing_cliff:
        flags.append("financing-cliff")
    return ScoreResult(
        "cash_runway",
        value=runway,
        computable=True,
        components={"quarterly_burn": burn},
        flags=flags,
        note=MODELS_CAVEAT,
    )


# ---- EV / FCF valuation (tier-safe) -----------------------------------------


def is_financials_sic(sic: int | None) -> bool:
    """True for finance/insurance/real-estate SICs (6000-6999) - EBITDA-meaningless."""
    return sic is not None and 6000 <= sic <= 6999


def ev_valuation(
    period: PeriodFinancials, *, market_cap: float | None, sic: int | None = None
) -> ScoreResult:
    """EV/Sales, EV/EBITDA (EBITDA<=0 fallback; financials suppressed), FCF yield."""
    debt = _debt(period)
    if market_cap is None or debt is None or period.cash is None:
        return ScoreResult(
            "ev_valuation", missing=["market_cap/total_debt/cash"], note="suppressed"
        )
    ev = market_cap + debt - period.cash
    components: dict[str, float] = {"enterprise_value": ev}
    flags: list[str] = []

    ev_sales = _ratio(ev, period.revenue)
    if ev_sales is not None:
        components["ev_to_sales"] = ev_sales

    ebitda_value = ebitda(period)
    if is_financials_sic(sic):
        flags.append("ev-ebitda-suppressed-financials")
        flags.append("out-of-model-financials")  # also flag Altman/Beneish out-of-model
    elif ebitda_value is None or ebitda_value <= 0:
        flags.append("ev-ebitda-not-meaningful")
        if ev_sales is not None:
            flags.append("ev-sales-fallback")
    else:
        components["ev_to_ebitda"] = ev / ebitda_value

    if period.operating_cash_flow is not None and period.capex is not None and ev:
        components["fcf_yield"] = (period.operating_cash_flow - period.capex) / ev

    return ScoreResult(
        "ev_valuation",
        value=ev_sales,
        computable=True,
        components=components,
        flags=flags,
        note=MODELS_CAVEAT,
    )


# ---- up-market risk modules -------------------------------------------------


def up_market_modules(
    t: PeriodFinancials,
    *,
    ev_ebitda_sector_percentile: float | None = None,
) -> ScoreResult:
    """Risks penny modules miss (weighted in for broad/larger-cap presets)."""
    components: dict[str, float] = {}
    flags: list[str] = []

    goodwill = (t.goodwill or 0.0) + (t.intangibles or 0.0)
    if t.total_assets and (t.goodwill is not None or t.intangibles is not None):
        components["goodwill_intangibles_pct"] = goodwill / t.total_assets
    if t.goodwill_impairment is not None and t.goodwill_impairment > 0:
        flags.append("goodwill-impairment")

    e = ebitda(t)
    net_debt = _sub(_debt(t), t.cash)
    nd_ebitda = _ratio(net_debt, e)
    if nd_ebitda is not None:
        components["net_debt_to_ebitda"] = nd_ebitda
        if nd_ebitda > 4.0:
            flags.append("high-leverage")

    # Lease/pension-adjusted EBITDA so EV/leverage is comparable across capital
    # structures (suppress-not-impute: only when an adjustment is disclosed).
    adj_e = adjusted_ebitda(t)
    if adj_e is not None:
        components["lease_pension_adjusted_ebitda"] = adj_e
        nd_adj = _ratio(net_debt, adj_e)
        if nd_adj is not None:
            components["net_debt_to_adjusted_ebitda"] = nd_adj
    coverage = _ratio(t.ebit, t.interest_expense)
    if coverage is not None:
        components["interest_coverage"] = coverage
        if coverage < 1.5:
            flags.append("weak-interest-coverage")

    sbc_rev = _ratio(t.sbc, t.revenue)
    if sbc_rev is not None:
        components["sbc_pct_revenue"] = sbc_rev
        if sbc_rev > 0.10:
            flags.append("high-sbc-dilution")

    if ev_ebitda_sector_percentile is not None:
        components["ev_ebitda_sector_percentile"] = ev_ebitda_sector_percentile
        if ev_ebitda_sector_percentile >= 0.80:
            flags.append("multiple-compression-risk")

    return ScoreResult(
        "up_market",
        computable=bool(components),
        components=components,
        flags=flags,
        note=MODELS_CAVEAT,
    )


# ---- sector/size-relative percentile ranking --------------------------------


def sector_size_percentiles(
    frame: pd.DataFrame,
    value_col: str,
    *,
    sector_col: str = "sic_sector",
    size_col: str = "size_bucket",
) -> pd.Series:
    """Percentile rank of ``value_col`` within each (SIC sector, size bucket) group.

    "Cheap"/"strong" is sector- and size-defined, so absolute multiples are not
    comparable across the band - the percentile is the honest comparison.
    """
    return frame.groupby([sector_col, size_col])[value_col].rank(pct=True)
