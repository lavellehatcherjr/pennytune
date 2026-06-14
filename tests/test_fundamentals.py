"""Fundamentals tests. All data is fixture companyfacts JSON."""

import json
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from pennytune.features.fundamentals import (
    FundamentalsEvidence,
    companyfacts_from_zip,
    compute_fundamentals,
    period_financials_from_companyfacts,
)
from pennytune.features.quant_scores import altman_z, piotroski_f


def _dur(
    start: str, end: str, val: float, *, form: str, filed: str, accn: str
) -> dict[str, Any]:
    return {
        "start": start,
        "end": end,
        "val": val,
        "fp": "FY",
        "form": form,
        "filed": filed,
        "accn": accn,
    }


def _inst(end: str, val: float, *, form: str, filed: str, accn: str) -> dict[str, Any]:
    return {
        "end": end,
        "val": val,
        "fp": "FY",
        "form": form,
        "filed": filed,
        "accn": accn,
    }


def _concept(unit: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"units": {unit: rows}}


# A clean, complete fixture (revenue growing, cash-burning, modest debt).
GROW: dict[str, Any] = {
    "cik": 111,
    "entityName": "Grow Co",
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": _concept(
                "USD",
                [
                    _dur(
                        "2024-01-01",
                        "2024-12-31",
                        2_200_000,
                        form="10-K",
                        filed="2025-02-15",
                        accn="A1",
                    ),
                    _dur(
                        "2025-01-01",
                        "2025-12-31",
                        3_100_000,
                        form="10-K",
                        filed="2026-02-10",
                        accn="A2",
                    ),
                ],
            ),
            "NetIncomeLoss": _concept(
                "USD",
                [
                    _dur(
                        "2025-01-01",
                        "2025-12-31",
                        -1_000_000,
                        form="10-K",
                        filed="2026-02-10",
                        accn="A2",
                    )
                ],
            ),
            "CashAndCashEquivalentsAtCarryingValue": _concept(
                "USD",
                [
                    _inst(
                        "2024-12-31",
                        9_000_000,
                        form="10-K",
                        filed="2025-02-15",
                        accn="A1",
                    ),
                    _inst(
                        "2025-12-31",
                        6_000_000,
                        form="10-K",
                        filed="2026-02-10",
                        accn="A2",
                    ),
                ],
            ),
            "LongTermDebt": _concept(
                "USD",
                [
                    _inst(
                        "2025-12-31",
                        1_400_000,
                        form="10-K",
                        filed="2026-02-10",
                        accn="A2",
                    )
                ],
            ),
            "NetCashProvidedByUsedInOperatingActivities": _concept(
                "USD",
                [
                    _dur(
                        "2025-01-01",
                        "2025-12-31",
                        -12_000_000,
                        form="10-K",
                        filed="2026-02-10",
                        accn="A2",
                    )
                ],
            ),
        },
        "dei": {
            "EntityCommonStockSharesOutstanding": _concept(
                "shares",
                [
                    _inst(
                        "2026-01-31",
                        50_000_000,
                        form="10-K",
                        filed="2026-02-10",
                        accn="A2",
                    )
                ],
            ),
        },
    },
}


def test_revenue_growth() -> None:
    rec = compute_fundamentals(GROW)
    assert rec.revenue == 3_100_000
    assert rec.revenue_prior == 2_200_000
    assert rec.revenue_growth == pytest.approx((3_100_000 - 2_200_000) / 2_200_000)
    assert [v for _, v in rec.revenue_history] == [2_200_000, 3_100_000]


def test_latest_instant_selection() -> None:
    rec = compute_fundamentals(GROW)
    assert rec.cash == 6_000_000  # 2025-12-31, not the older 2024 instant
    assert rec.total_debt == 1_400_000
    assert rec.shares_outstanding == 50_000_000


def test_burn_and_runway() -> None:
    rec = compute_fundamentals(GROW)
    assert rec.operating_cash_flow == -12_000_000
    assert rec.monthly_burn == pytest.approx(1_000_000)  # 12M annual / 12
    assert rec.runway_months == pytest.approx(6.0)  # 6M cash / 1M monthly


def test_valuation_from_price() -> None:
    rec = compute_fundamentals(GROW, current_price=0.80)
    assert rec.market_cap == pytest.approx(40_000_000)  # 0.80 x 50M shares
    assert rec.price_to_sales == pytest.approx(40_000_000 / 3_100_000)
    assert rec.enterprise_value == pytest.approx(40_000_000 + 1_400_000 - 6_000_000)
    assert rec.ev_to_sales == pytest.approx(35_400_000 / 3_100_000)


def test_evidence_is_traceable() -> None:
    rec = compute_fundamentals(GROW)
    ev = rec.evidence["revenue"]
    assert ev.tag == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert ev.form == "10-K"
    assert ev.filed == "2026-02-10"
    assert ev.accession == "A2"
    assert ev.period_end == "2025-12-31"


def test_complete_record_has_no_warning_flags() -> None:
    rec = compute_fundamentals(GROW)
    assert rec.data_completeness == 1.0
    assert "low-confidence" not in rec.flags
    assert "fundamentals-incomplete" not in rec.flags


def test_tag_fallback_when_primary_missing() -> None:
    # Primary tag (RevenueFromContractWithCustomer...) absent → falls to Revenues.
    payload: dict[str, Any] = {
        "cik": 333,
        "entityName": "Fallback Co",
        "facts": {
            "us-gaap": {
                "Revenues": _concept(
                    "USD",
                    [
                        _dur(
                            "2024-01-01",
                            "2024-12-31",
                            1_000_000,
                            form="10-K",
                            filed="2025-02-01",
                            accn="C1",
                        ),
                        _dur(
                            "2025-01-01",
                            "2025-12-31",
                            1_500_000,
                            form="10-K",
                            filed="2026-02-01",
                            accn="C2",
                        ),
                    ],
                )
            }
        },
    }
    rec = compute_fundamentals(payload)
    assert rec.revenue == 1_500_000
    assert rec.evidence["revenue"].tag == "Revenues"


def test_sparse_data_low_confidence_and_no_silent_zero() -> None:
    payload: dict[str, Any] = {
        "cik": 222,
        "entityName": "Sparse Co",
        "facts": {
            "us-gaap": {
                "Revenues": _concept(
                    "USD",
                    [
                        _dur(
                            "2025-01-01",
                            "2025-12-31",
                            500_000,
                            form="10-K",
                            filed="2026-03-01",
                            accn="B1",
                        )
                    ],
                )
            }
        },
    }
    rec = compute_fundamentals(payload)
    assert rec.revenue == 500_000
    # Missing inputs are None, never silently zero (suppress-not-impute).
    assert rec.cash is None
    assert rec.operating_cash_flow is None
    assert rec.shares_outstanding is None
    assert rec.runway_months is None
    assert rec.revenue_growth is None
    assert "low-confidence" in rec.flags
    assert "limited-history" in rec.flags
    assert "fundamentals-incomplete" in rec.flags
    assert rec.data_completeness == pytest.approx(0.25)


def test_companyfacts_from_zip(tmp_path: Path) -> None:
    zip_path = tmp_path / "companyfacts.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("CIK0000000111.json", json.dumps(GROW))
    loaded = companyfacts_from_zip(zip_path, "111")
    assert loaded["entityName"] == "Grow Co"
    rec = compute_fundamentals(loaded, current_price=0.80)
    assert rec.revenue == 3_100_000
    assert rec.cik == "0000000111"


# ---- companyfacts -> PeriodFinancials (the live-scored fundamentals seam) ----


def _dur_row(
    end: str, val: float, *, form: str = "10-K", filed: str | None = None
) -> dict[str, Any]:
    """An annual (fiscal-year) duration fact ending at ``end``."""
    e = date.fromisoformat(end)
    return {
        "start": (e - timedelta(days=364)).isoformat(),
        "end": end,
        "val": val,
        "fp": "FY",
        "form": form,
        "filed": filed or (e + timedelta(days=60)).isoformat(),
        "accn": f"acc-{end}",
    }


def _inst_row(
    end: str, val: float, *, form: str = "10-K", filed: str | None = None
) -> dict[str, Any]:
    """A balance-sheet instant fact as of ``end``."""
    e = date.fromisoformat(end)
    return {
        "end": end,
        "val": val,
        "fp": "FY",
        "form": form,
        "filed": filed or (e + timedelta(days=60)).isoformat(),
        "accn": f"acc-{end}",
    }


def _usd_dur(mapping: dict[str, float]) -> dict[str, Any]:
    return _concept("USD", [_dur_row(e, v) for e, v in mapping.items()])


def _usd_inst(mapping: dict[str, float]) -> dict[str, Any]:
    return _concept("USD", [_inst_row(e, v) for e, v in mapping.items()])


# A complete two-year Dec-FYE filer (improving fundamentals) → every quant model
# the scorer consumes is computable from the parsed periods.
FULL: dict[str, Any] = {
    "cik": 909,
    "entityName": "Full Co",
    "facts": {
        "us-gaap": {
            "Assets": _usd_inst({"2023-12-31": 20_000_000, "2024-12-31": 24_000_000}),
            "AssetsCurrent": _usd_inst(
                {"2023-12-31": 12_000_000, "2024-12-31": 15_000_000}
            ),
            "LiabilitiesCurrent": _usd_inst(
                {"2023-12-31": 5_000_000, "2024-12-31": 5_500_000}
            ),
            "Liabilities": _usd_inst(
                {"2023-12-31": 9_000_000, "2024-12-31": 9_500_000}
            ),
            "RetainedEarningsAccumulatedDeficit": _usd_inst(
                {"2023-12-31": 4_000_000, "2024-12-31": 5_200_000}
            ),
            "StockholdersEquity": _usd_inst(
                {"2023-12-31": 11_000_000, "2024-12-31": 14_500_000}
            ),
            "CashAndCashEquivalentsAtCarryingValue": _usd_inst(
                {"2023-12-31": 3_000_000, "2024-12-31": 4_000_000}
            ),
            "AccountsReceivableNetCurrent": _usd_inst(
                {"2023-12-31": 2_000_000, "2024-12-31": 2_200_000}
            ),
            "InventoryNet": _usd_inst(
                {"2023-12-31": 2_500_000, "2024-12-31": 2_800_000}
            ),
            "PropertyPlantAndEquipmentNet": _usd_inst(
                {"2023-12-31": 5_000_000, "2024-12-31": 5_500_000}
            ),
            "LongTermDebt": _usd_inst(
                {"2023-12-31": 3_000_000, "2024-12-31": 2_500_000}
            ),
            "Revenues": _usd_dur({"2023-12-31": 10_000_000, "2024-12-31": 13_000_000}),
            "CostOfGoodsAndServicesSold": _usd_dur(
                {"2023-12-31": 6_000_000, "2024-12-31": 7_200_000}
            ),
            "OperatingIncomeLoss": _usd_dur(
                {"2023-12-31": 1_000_000, "2024-12-31": 1_600_000}
            ),
            "NetIncomeLoss": _usd_dur({"2023-12-31": 500_000, "2024-12-31": 1_200_000}),
            "NetCashProvidedByUsedInOperatingActivities": _usd_dur(
                {"2023-12-31": 800_000, "2024-12-31": 1_600_000}
            ),
            "SellingGeneralAndAdministrativeExpense": _usd_dur(
                {"2023-12-31": 2_500_000, "2024-12-31": 3_000_000}
            ),
        },
        "dei": {
            # Cover-page shares are dated ~6 weeks after each fiscal-year-end.
            "EntityCommonStockSharesOutstanding": _concept(
                "shares",
                [
                    _inst_row("2024-02-15", 10_000_000),
                    _inst_row("2025-02-15", 10_000_000),
                ],
            ),
        },
    },
}


def test_period_financials_two_years_all_models_computable() -> None:
    fe = period_financials_from_companyfacts(FULL)
    assert fe.financials_period == "2024-12-31"
    assert fe.period_t is not None and fe.period_t1 is not None
    # latest fiscal year's line items, aligned to the fiscal-year-end
    assert fe.period_t.total_assets == 24_000_000
    assert fe.period_t.revenue == 13_000_000
    assert fe.period_t.cogs == 7_200_000
    assert fe.period_t.shares_outstanding == 10_000_000  # cover-date share match
    assert fe.revenue_growth == pytest.approx(0.30)
    # the quant models the scorer runs are all computable from the periods
    assert altman_z(fe.period_t).computable
    pf = piotroski_f(fe.period_t, fe.period_t1)
    assert pf.computable and pf.value == 9.0  # every check passes → strong


def test_period_financials_anchors_on_fye_not_stale_tag() -> None:
    """A June-FYE filer whose current revenue moved to a different XBRL tag.

    Mirrors the live U.S. Global Investors (GROW) shape: ``Revenues`` carries
    only stale years; current revenue is under ``...IncludingAssessedTax``. The
    parser must anchor on the latest real fiscal-year-end and pick the current
    revenue, never the stale ``Revenues`` series.
    """
    payload: dict[str, Any] = {
        "cik": 754811,
        "entityName": "June FYE Co",
        "facts": {
            "us-gaap": {
                "Assets": _usd_inst(
                    {"2024-06-30": 40_000_000, "2025-06-30": 48_000_000}
                ),
                "Revenues": _usd_dur(
                    {"2011-06-30": 30_000_000, "2012-06-30": 25_000_000}
                ),  # stale
                "RevenueFromContractWithCustomerIncludingAssessedTax": _usd_dur(
                    {"2024-06-30": 11_000_000, "2025-06-30": 8_500_000}
                ),
            }
        },
    }
    fe = period_financials_from_companyfacts(payload)
    assert fe.financials_period == "2025-06-30"  # not 2012, not a cover date
    assert fe.period_t is not None and fe.period_t.revenue == 8_500_000  # current
    assert fe.revenue_growth == pytest.approx((8_500_000 - 11_000_000) / 11_000_000)


def test_period_financials_ignores_dei_cover_date_as_fye() -> None:
    """dei cover-page facts carry fp=FY/10-K but are dated at filing, not FYE."""
    payload: dict[str, Any] = {
        "cik": 1,
        "entityName": "Cover Co",
        "facts": {
            "us-gaap": {"Assets": _usd_inst({"2024-12-31": 5_000_000})},
            "dei": {
                "EntityCommonStockSharesOutstanding": _concept(
                    "shares",
                    [_inst_row("2025-02-20", 7_000_000)],  # cover date, fp=FY
                )
            },
        },
    }
    fe = period_financials_from_companyfacts(payload)
    assert fe.financials_period == "2024-12-31"  # the real FYE, not 2025-02-20
    assert fe.period_t is not None
    assert fe.period_t.total_assets == 5_000_000
    assert fe.period_t.shares_outstanding == 7_000_000  # still matched within window


def test_period_financials_no_period_is_suppressed_not_imputed() -> None:
    # Only quarterly data (no annual 10-K period) → fundamentals suppressed.
    payload: dict[str, Any] = {
        "cik": 2,
        "entityName": "Quarterly Only Co",
        "facts": {
            "us-gaap": {
                "Revenues": _concept(
                    "USD",
                    [
                        {
                            "start": "2024-01-01",
                            "end": "2024-03-31",
                            "val": 1_000_000,
                            "fp": "Q1",
                            "form": "10-Q",
                            "filed": "2024-05-01",
                            "accn": "q1",
                        }
                    ],
                )
            }
        },
    }
    fe = period_financials_from_companyfacts(payload)
    assert isinstance(fe, FundamentalsEvidence)
    assert fe.period_t is None and fe.period_t1 is None
    assert fe.revenue_growth is None
    assert any("suppressed" in note for note in fe.completeness)


def test_period_financials_single_year_limits_history() -> None:
    payload: dict[str, Any] = {
        "cik": 3,
        "entityName": "One Year Co",
        "facts": {
            "us-gaap": {
                "Assets": _usd_inst({"2024-12-31": 8_000_000}),
                "Revenues": _usd_dur({"2024-12-31": 2_000_000}),
            }
        },
    }
    fe = period_financials_from_companyfacts(payload)
    assert fe.period_t is not None and fe.period_t1 is None
    assert fe.revenue_growth is None  # no prior year → suppressed, not fabricated
    assert any("one annual period" in note for note in fe.completeness)
