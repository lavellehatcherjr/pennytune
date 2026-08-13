"""XBRL tag-resolution fallbacks: derive what is derivable, disclose what is not.

A single-candidate tag list silently yields ``None`` when a filer reports the
concept under a different name. The affected metric is then suppressed, the
composite is computed from a partial balance sheet, and nothing on screen says
so. That is the suppress-at-the-join pattern one layer lower: the leaf is
honest (it returns None) and the join throws the honesty away.

These tests pin two derivations and, just as importantly, pin the disclosure
that must appear when no derivation is possible.
"""

from __future__ import annotations

from typing import Any

from pennytune.features.fundamentals import (
    _period_at_end,
    period_financials_from_companyfacts,
)

# ---- fixture helpers ---------------------------------------------------------

_END = "2025-12-31"
_START = "2025-01-01"
_ACCN = "0000000000-25-000001"


def _inst(
    val: float, *, accn: str = _ACCN, filed: str = "2026-02-10"
) -> dict[str, Any]:
    """A balance-sheet (instant) fact at ``_END``."""
    return {
        "end": _END,
        "val": val,
        "accn": accn,
        "fy": 2025,
        "fp": "FY",
        "form": "10-K",
        "filed": filed,
    }


def _dur(val: float, *, accn: str = _ACCN, filed: str = "2026-02-10") -> dict[str, Any]:
    """An income-statement (duration) fact spanning the fiscal year to ``_END``."""
    return {
        "start": _START,
        "end": _END,
        "val": val,
        "accn": accn,
        "fy": 2025,
        "fp": "FY",
        "form": "10-K",
        "filed": filed,
    }


def _facts(**concepts: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a companyfacts payload from ``TagName=[rows]`` keyword pairs."""
    return {
        "entityName": "Fixture Co",
        "facts": {
            "us-gaap": {tag: {"units": {"USD": rows}} for tag, rows in concepts.items()}
        },
    }


# ---- total liabilities -------------------------------------------------------


def test_total_liabilities_derived_when_direct_tag_absent() -> None:
    """KO's real shape: no ``us-gaap:Liabilities`` anywhere in companyfacts.

    ``LiabilitiesAndStockholdersEquity`` is the balance-sheet total (equal to
    ``Assets``), so total liabilities is that minus equity. Without this the
    whole Altman/leverage half of the model is suppressed for a large,
    perfectly well-documented filer.
    """
    period, _ = _period_at_end(
        _facts(
            Assets=[_inst(1_000.0)],
            LiabilitiesAndStockholdersEquity=[_inst(1_000.0)],
            StockholdersEquity=[_inst(400.0)],
        ),
        _END,
    )
    assert period.total_liabilities == 600.0, (
        f"total_liabilities not derived: {period.total_liabilities}"
    )


def test_direct_liabilities_tag_still_wins_over_the_derivation() -> None:
    """A reported value must never be replaced by a derived one."""
    period, _ = _period_at_end(
        _facts(
            Assets=[_inst(1_000.0)],
            Liabilities=[_inst(590.0)],  # reported
            LiabilitiesAndStockholdersEquity=[_inst(1_000.0)],
            StockholdersEquity=[_inst(400.0)],  # would derive 600.0
        ),
        _END,
    )
    assert period.total_liabilities == 590.0


def test_liabilities_derivation_requires_a_matching_period() -> None:
    """The two operands must share a period end; a stale operand must not mix."""
    other_end = {
        "end": "2024-12-31",
        "val": 300.0,
        "accn": _ACCN,
        "fy": 2024,
        "fp": "FY",
        "form": "10-K",
        "filed": "2025-02-10",
    }
    period, _ = _period_at_end(
        _facts(
            Assets=[_inst(1_000.0)],
            LiabilitiesAndStockholdersEquity=[_inst(1_000.0)],
            StockholdersEquity=[other_end],  # prior year only
        ),
        _END,
    )
    assert period.total_liabilities is None, (
        f"mixed periods to produce {period.total_liabilities}"
    )


# ---- EBIT --------------------------------------------------------------------


def test_ebit_is_suppressed_not_guessed_when_operating_income_is_absent() -> None:
    """JNJ/CVX/KLAC/BAC shape: no ``us-gaap:OperatingIncomeLoss``.

    Three candidate reconstructions were measured against filers that DO report
    an operating-income subtotal, and none is fit to ship:

    * ``Pretax + InterestExpense`` - median absolute error 7.9%, above 5% on
      28 of 47 filers. The residual is real non-operating income, not noise.
    * ``Revenues - CostsAndExpenses`` - exact where it works, but on the only
      two failers it reaches (CVX, XOM) it reproduces *pretax income* to the
      dollar, i.e. it silently drops the interest add-back precisely where the
      add-back is the whole point.
    * ``GrossProfit - OperatingExpenses`` - exact on 23/23, and computable on
      0 of the 11 filers that need it.

    These filers genuinely do not publish an operating-income subtotal. EBIT
    stays suppressed and is disclosed; a 7.9%-median guess feeding Altman's
    EBIT/TA term would be worse than an honest gap.
    """
    period, _ = _period_at_end(
        _facts(
            Assets=[_inst(1_000.0)],
            IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest=[
                _dur(180.0)
            ],
            InterestExpense=[_dur(20.0)],
        ),
        _END,
    )
    assert period.ebit is None, (
        f"EBIT was guessed from non-operating inputs: {period.ebit}"
    )


# ---- disclosure when nothing can be derived ---------------------------------


def test_underivable_inputs_are_suppressed_and_disclosed() -> None:
    """The point of the whole exercise: silence is not acceptable.

    A filer with an annual period but no liabilities concept in any form must
    leave the field None AND say which input was missing, so a reader can tell
    the composite was built from a partial balance sheet.
    """
    evidence = period_financials_from_companyfacts(
        _facts(
            Assets=[_inst(1_000.0)],
            Revenues=[_dur(900.0)],
        )
    )
    assert evidence.period_t is not None
    assert evidence.period_t.total_liabilities is None
    joined = " | ".join(evidence.completeness)
    assert "total_liabilities" in joined, (
        f"missing input never disclosed; completeness was: {evidence.completeness}"
    )


def test_disclosure_names_only_the_inputs_that_are_actually_missing() -> None:
    """A fully-populated period must not emit a missing-input line at all."""
    evidence = period_financials_from_companyfacts(
        _facts(
            Assets=[_inst(1_000.0)],
            AssetsCurrent=[_inst(600.0)],
            LiabilitiesCurrent=[_inst(200.0)],
            Liabilities=[_inst(600.0)],
            StockholdersEquity=[_inst(400.0)],
            RetainedEarningsAccumulatedDeficit=[_inst(150.0)],
            OperatingIncomeLoss=[_dur(120.0)],
            Revenues=[_dur(900.0)],
        )
    )
    joined = " | ".join(evidence.completeness)
    assert "core inputs unavailable" not in joined, (
        f"emitted a missing-input line for a complete period: {evidence.completeness}"
    )


# ---- the fiscal-year anchor ---------------------------------------------------


def test_fiscal_year_end_ignores_a_forward_dated_footnote_fact() -> None:
    """Starbucks' real failure, and it is worse than any missing tag.

    ``_fiscal_year_ends`` takes ``max()`` over the ``end`` of every us-gaap fact
    tagged ``fp=FY`` on a 10-K. Forward-looking footnote facts (expected
    restructuring cost, plan match percentages, IPO proceeds) carry a future
    ``end`` and win that max, so the period anchors on a date where no balance
    sheet exists and EVERY line item resolves to None. The company is then
    scored from a completely empty period with nothing on screen saying so.
    """
    facts = _facts(
        Assets=[_inst(1_000.0)],
        Liabilities=[_inst(600.0)],
        StockholdersEquity=[_inst(400.0)],
        Revenues=[_dur(900.0)],
        # one forward-dated footnote fact, a year past the real period end
        RestructuringAndRelatedCostExpectedCost1=[
            {
                "end": "2026-12-31",
                "val": 5.0,
                "accn": _ACCN,
                "fy": 2025,
                "fp": "FY",
                "form": "10-K",
                "filed": "2026-02-10",
            }
        ],
    )
    evidence = period_financials_from_companyfacts(facts)
    assert evidence.financials_period == _END, (
        f"anchored on a forward-dated footnote fact: {evidence.financials_period}"
    )
    assert evidence.period_t is not None
    assert evidence.period_t.total_assets == 1_000.0, (
        "the whole period came back empty because of the bad anchor"
    )


# ---- total debt ---------------------------------------------------------------


def test_total_debt_falls_back_to_long_term_plus_current() -> None:
    """``COMBINED_DEBT_TAGS`` alone fails for ~91% of filers.

    The record path already sums long-term and current debt correctly; the
    period path did not, so ``total_debt`` was None for almost everyone even
    when both components were reported.
    """
    period, _ = _period_at_end(
        _facts(
            Assets=[_inst(1_000.0)],
            LongTermDebtNoncurrent=[_inst(300.0)],
            LongTermDebtCurrent=[_inst(50.0)],
        ),
        _END,
    )
    assert period.total_debt == 350.0, f"total_debt not summed: {period.total_debt}"


def test_missing_ebit_is_named_in_the_completeness_line() -> None:
    """An underivable input must be named, not silently absent."""
    evidence = period_financials_from_companyfacts(
        _facts(
            Assets=[_inst(1_000.0)],
            Liabilities=[_inst(600.0)],
            StockholdersEquity=[_inst(400.0)],
            Revenues=[_dur(900.0)],
        )
    )
    joined = " | ".join(evidence.completeness)
    assert "ebit" in joined, (
        f"missing EBIT never disclosed; completeness was: {evidence.completeness}"
    )
