"""Quantitative/forensic scoring tests. Hand-computed from fixtures."""

import math
from typing import Any

import pandas as pd
import pytest

from pennytune.features.quant_scores import (
    PeriodFinancials,
    accruals,
    adjusted_ebitda,
    altman_bre,
    altman_z,
    beneish_m,
    cash_runway,
    dechow_f,
    ev_valuation,
    is_financials_sic,
    montier_c,
    piotroski_f,
    sector_size_percentiles,
    up_market_modules,
)


def test_lease_pension_adjusted_ebitda_suppress_then_adjust() -> None:
    base = PeriodFinancials(ebit=100.0, depreciation=20.0)  # EBITDA = 120
    # Suppress-not-impute: no lease/pension disclosed → no adjusted figure.
    assert adjusted_ebitda(base) is None
    adjusted = PeriodFinancials(
        ebit=100.0,
        depreciation=20.0,
        operating_lease_expense=30.0,
        pension_expense=10.0,
    )
    assert adjusted_ebitda(adjusted) == 160.0  # 120 + 30 + 10
    # Surfaced in the up-market module so EV/leverage is capital-structure-comparable.
    result = up_market_modules(
        PeriodFinancials(
            ebit=100.0,
            depreciation=20.0,
            total_debt=400.0,
            cash=40.0,
            operating_lease_expense=30.0,
        )
    )
    assert "lease_pension_adjusted_ebitda" in result.components
    assert "net_debt_to_adjusted_ebitda" in result.components


# ---- Altman Z'' -------------------------------------------------------------


def test_altman_z_safe_zone_and_bre() -> None:
    p = PeriodFinancials(
        current_assets=500,
        current_liabilities=200,
        retained_earnings=400,
        ebit=120,
        total_assets=1000,
        book_equity=600,
        total_liabilities=400,
    )
    result = altman_z(p)
    assert result.value is not None
    # 6.56*0.3 + 3.26*0.4 + 6.72*0.12 + 1.05*1.5
    assert result.value == pytest.approx(5.6534, abs=1e-3)
    assert "zone:safe" in result.flags
    assert altman_bre(result.value) == ("AAA", "minimal")  # EMS = 5.6534 + 3.25 > 8.15


def test_altman_z_distress_and_default_rating() -> None:
    p = PeriodFinancials(
        current_assets=100,
        current_liabilities=300,
        retained_earnings=-500,
        ebit=-50,
        total_assets=1000,
        book_equity=-100,
        total_liabilities=1100,
    )
    result = altman_z(p)
    assert result.value is not None and result.value < 1.1
    assert "zone:distress" in result.flags
    rating, pd_tier = altman_bre(result.value)
    assert rating == "D"
    assert pd_tier == "default"


def test_altman_suppressed_not_imputed_when_missing() -> None:
    result = altman_z(PeriodFinancials(current_assets=500, current_liabilities=200))
    assert result.computable is False
    assert result.value is None  # NOT 0
    assert "total_assets" in result.missing


# ---- Beneish M --------------------------------------------------------------

_BENEISH_T = PeriodFinancials(
    receivables=120,
    revenue=1000,
    cogs=600,
    current_assets=500,
    net_ppe=300,
    total_assets=1000,
    depreciation=50,
    sga=100,
    current_liabilities=200,
    long_term_debt=100,
    net_income=80,
    operating_cash_flow=60,
)
_BENEISH_T1 = PeriodFinancials(
    receivables=100,
    revenue=900,
    cogs=540,
    current_assets=450,
    net_ppe=280,
    total_assets=900,
    depreciation=45,
    sga=90,
    current_liabilities=180,
    long_term_debt=90,
    net_income=70,
    operating_cash_flow=65,
)


def test_beneish_subindices_and_composite_clean() -> None:
    result = beneish_m(_BENEISH_T, _BENEISH_T1)
    assert result.components["DSRI"] == pytest.approx(0.12 / (100 / 900))
    assert result.components["SGI"] == pytest.approx(1000 / 900)
    assert result.components["TATA"] == pytest.approx(0.02)
    assert result.value == pytest.approx(-2.1935, abs=1e-3)
    assert "possible-manipulation" not in result.flags  # below the -1.78 cutoff


def test_beneish_flags_manipulation_on_high_accruals() -> None:
    manipulator = PeriodFinancials(
        receivables=120,
        revenue=1000,
        cogs=600,
        current_assets=500,
        net_ppe=300,
        total_assets=1000,
        depreciation=50,
        sga=100,
        current_liabilities=200,
        long_term_debt=100,
        net_income=200,
        operating_cash_flow=20,  # TATA = 0.18
    )
    result = beneish_m(manipulator, _BENEISH_T1)
    assert result.components["TATA"] == pytest.approx(0.18)
    assert result.value is not None and result.value > -1.78
    assert "possible-manipulation" in result.flags


# ---- Dechow F ---------------------------------------------------------------


def test_dechow_f_above_normal_and_issuance_indicator() -> None:
    t2 = PeriodFinancials(
        total_assets=800,
        receivables=80,
        inventory=100,
        cash=50,
        net_ppe=200,
        total_liabilities=300,
        total_debt=100,
        net_income=40,
        revenue=700,
    )
    t1 = PeriodFinancials(
        total_assets=900,
        receivables=100,
        inventory=110,
        cash=60,
        net_ppe=220,
        total_liabilities=350,
        total_debt=110,
        net_income=50,
        revenue=800,
    )
    t = PeriodFinancials(
        total_assets=1000,
        receivables=120,
        inventory=120,
        cash=70,
        net_ppe=240,
        total_liabilities=400,
        total_debt=120,
        net_income=60,
        revenue=900,
    )
    result = dechow_f(t, t1, t2, issuance=True)
    assert result.computable is True
    assert result.components["issuance"] == 1.0  # set from 8-K 3.02 activity
    assert result.components["rsst"] == pytest.approx(50 / 950, abs=1e-4)
    assert 1.0 < (result.value or 0) < 1.85
    assert "misstatement-risk-above-normal" in result.flags


def test_dechow_suppressed_without_t2_history() -> None:
    t = PeriodFinancials(
        total_assets=1000,
        receivables=120,
        inventory=120,
        cash=70,
        net_ppe=240,
        total_liabilities=400,
        total_debt=120,
        net_income=60,
        revenue=900,
    )
    t1 = PeriodFinancials(
        total_assets=900,
        receivables=100,
        inventory=110,
        cash=60,
        net_ppe=220,
        total_liabilities=350,
        total_debt=110,
        net_income=50,
        revenue=800,
    )
    result = dechow_f(t, t1, PeriodFinancials(), issuance=False)
    assert result.computable is False
    assert "t-2" in result.note


# ---- Montier C / Piotroski F ------------------------------------------------


def test_montier_c_counts_lit_flags() -> None:
    t = PeriodFinancials(
        net_income=100,
        operating_cash_flow=20,
        receivables=200,
        revenue=1000,
        inventory=300,
        cogs=500,
        current_assets=600,
        depreciation=20,
        gross_ppe=400,
        total_assets=1300,
    )
    t1 = PeriodFinancials(
        net_income=80,
        operating_cash_flow=70,
        receivables=120,
        revenue=900,
        inventory=200,
        cogs=480,
        current_assets=450,
        depreciation=30,
        gross_ppe=380,
        total_assets=1000,
    )
    result = montier_c(t, t1)
    assert result.computable is True
    assert result.value is not None and result.value >= 4
    assert "ni_ocf_divergence_growing" in result.flags
    assert "high_asset_growth" in result.flags  # 1300/1000 - 1 = 0.30 > 0.10


def test_piotroski_strong_and_weak() -> None:
    strong_t = PeriodFinancials(
        net_income=100,
        operating_cash_flow=120,
        total_assets=1000,
        long_term_debt=50,
        current_assets=600,
        current_liabilities=200,
        shares_outstanding=1000,
        revenue=1100,
        cogs=440,
    )
    strong_t1 = PeriodFinancials(
        net_income=50,
        operating_cash_flow=40,
        total_assets=900,
        long_term_debt=100,
        current_assets=450,
        current_liabilities=300,
        shares_outstanding=1000,
        revenue=900,
        cogs=450,
    )
    strong = piotroski_f(strong_t, strong_t1)
    assert strong.value is not None and strong.value >= 7
    assert "strong" in strong.flags
    assert "value-universe-signal" in strong.flags

    weak_t = PeriodFinancials(
        net_income=-50,
        operating_cash_flow=-60,
        total_assets=1000,
        long_term_debt=200,
        current_assets=300,
        current_liabilities=400,
        shares_outstanding=1200,
        revenue=500,
        cogs=400,
    )
    weak = piotroski_f(weak_t, strong_t1)
    assert weak.value is not None and weak.value <= 2
    assert "weak" in weak.flags


# ---- accruals / runway ------------------------------------------------------


def test_accruals_ratio_and_sloan_both_forms() -> None:
    t = PeriodFinancials(
        net_income=80,
        operating_cash_flow=60,
        total_assets=1000,
        current_assets=500,
        cash=100,
        current_liabilities=200,
        depreciation=50,
    )
    t1 = PeriodFinancials(
        net_income=70,
        operating_cash_flow=65,
        total_assets=900,
        current_assets=450,
        cash=80,
        current_liabilities=180,
        depreciation=45,
    )
    result = accruals(t, t1)
    assert result.value == pytest.approx(0.02)  # (80-60)/1000
    assert result.components["sloan_cash_flow"] == pytest.approx(20 / 950)
    # ncwc_t = (500-100)-200 = 200; ncwc_t1 = (450-80)-180 = 190; (10 - 50)/950
    assert result.components["sloan_balance_sheet"] == pytest.approx((10 - 50) / 950)


def test_cash_runway_and_financing_cliff() -> None:
    healthy = cash_runway(6_000_000, -1_000_000, prior_quarterly_ocf=-800_000)
    assert healthy.value == pytest.approx(6.0)
    assert "burn-accelerating" in healthy.flags  # 1.0M > 0.8M
    assert "financing-cliff" not in healthy.flags

    cliff = cash_runway(2_000_000, -1_000_000)
    assert cliff.value == pytest.approx(2.0)
    assert "financing-cliff" in cliff.flags  # < 4 quarters

    generating = cash_runway(1_000_000, 500_000)
    assert generating.value == math.inf
    assert "cash-generating" in generating.flags


# ---- EV / FCF valuation (tier-safe) -----------------------------------------


def test_ev_ebitda_fallback_to_ev_sales_when_ebitda_negative() -> None:
    p = PeriodFinancials(
        total_debt=1_400_000,
        cash=6_000_000,
        revenue=3_100_000,
        ebit=-2_000_000,
        depreciation=500_000,
        operating_cash_flow=-2_000_000,
        capex=200_000,
    )
    result = ev_valuation(p, market_cap=40_000_000, sic=2836)  # biotech, EBITDA < 0
    assert result.components["enterprise_value"] == pytest.approx(35_400_000)
    assert result.components["ev_to_sales"] == pytest.approx(35_400_000 / 3_100_000)
    assert "ev-ebitda-not-meaningful" in result.flags
    assert "ev-sales-fallback" in result.flags
    assert "ev_to_ebitda" not in result.components


def test_ev_ebitda_computed_when_positive() -> None:
    p = PeriodFinancials(
        total_debt=1_400_000,
        cash=6_000_000,
        revenue=3_100_000,
        ebit=4_000_000,
        depreciation=1_000_000,
    )
    result = ev_valuation(p, market_cap=40_000_000, sic=2836)
    assert result.components["ev_to_ebitda"] == pytest.approx(35_400_000 / 5_000_000)


def test_ev_ebitda_suppressed_for_financials() -> None:
    assert is_financials_sic(6022) is True  # state commercial bank
    p = PeriodFinancials(
        total_debt=1_400_000,
        cash=6_000_000,
        revenue=3_100_000,
        ebit=4_000_000,
        depreciation=1_000_000,
    )
    result = ev_valuation(p, market_cap=40_000_000, sic=6022)
    assert "ev-ebitda-suppressed-financials" in result.flags
    assert "out-of-model-financials" in result.flags
    assert "ev_to_ebitda" not in result.components


# ---- sector/size percentile + up-market -------------------------------------


def test_sector_size_percentiles() -> None:
    frame = pd.DataFrame(
        {
            "sic_sector": ["tech", "tech", "tech", "util"],
            "size_bucket": ["micro", "micro", "micro", "micro"],
            "ev_to_sales": [10.0, 20.0, 30.0, 5.0],
        }
    )
    pct = sector_size_percentiles(frame, "ev_to_sales")
    assert pct.tolist() == pytest.approx([1 / 3, 2 / 3, 1.0, 1.0])


def test_up_market_modules_on_large_cap() -> None:
    p = PeriodFinancials(
        total_assets=10_000_000_000,
        goodwill=3_000_000_000,
        intangibles=1_000_000_000,
        goodwill_impairment=500_000_000,
        total_debt=8_000_000_000,
        cash=1_000_000_000,
        ebit=1_000_000_000,
        depreciation=500_000_000,
        interest_expense=900_000_000,
        sbc=600_000_000,
        revenue=4_000_000_000,
    )
    result: Any = up_market_modules(p, ev_ebitda_sector_percentile=0.85)
    assert result.components["goodwill_intangibles_pct"] == pytest.approx(0.40)
    assert "goodwill-impairment" in result.flags
    assert "high-leverage" in result.flags  # net debt 7B / EBITDA 1.5B ≈ 4.67 > 4
    assert "weak-interest-coverage" in result.flags  # 1.0B / 0.9B ≈ 1.11 < 1.5
    assert "high-sbc-dilution" in result.flags  # 0.6B / 4.0B = 15% > 10%
    assert "multiple-compression-risk" in result.flags  # percentile 0.85 >= 0.80
