"""Fundamentals via the SEC EDGAR backbone.

The financial-truth layer and analytical core: it reads a company's actual
filed financials from EDGAR's XBRL ``companyfacts`` and derives the metrics that
decide whether a cheap stock is *cheap-with-substance* or *cheap-and-doomed* -
revenue and its growth, cash, debt, shares, operating cash flow, burn rate, and
the survival metric **cash runway**, plus debt-aware valuation (P/S, EV,
EV/Sales).

Design: the analytical core (:func:`compute_fundamentals`) is a pure function
over the canonical ``companyfacts`` JSON, so it is fully testable from fixtures
with no network and gives exact tag-fallback control (it records *which* XBRL
tag supplied each value). The fetch boundary
(:class:`EdgarFundamentalsProvider`) calls edgartools' ``set_identity`` (the
SEC-required identity header) and retrieves companyfacts through the hardened,
rate-limited, cached HTTP client of the data layer. EDGAR bulk
``companyfacts.zip`` is supported via :func:`companyfacts_from_zip` (preferred
at full-universe scale).

Per the suppress-not-impute rule for scoring edge cases, a missing input is
recorded as ``None`` and flagged - never silently zero-imputed.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from pennytune.features.quant_scores import PeriodFinancials
from pennytune.providers.base import FundamentalsProvider
from pennytune.providers.http import SafeHttpClient

__all__ = [
    "Evidence",
    "FundamentalsRecord",
    "FundamentalsEvidence",
    "compute_fundamentals",
    "period_financials_from_companyfacts",
    "companyfacts_from_zip",
    "EdgarFundamentalsProvider",
    "COMPANYFACTS_URL_TEMPLATE",
]

COMPANYFACTS_URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Ordered tag-fallback lists per concept for XBRL tag resilience. Each entry
# is (taxonomy, tag); the first that yields a fact wins, and the chosen tag is
# recorded in the evidence.
REVENUE_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
    ("us-gaap", "Revenues"),
    ("us-gaap", "RevenueFromContractWithCustomerIncludingAssessedTax"),
    ("us-gaap", "SalesRevenueNet"),
    ("us-gaap", "SalesRevenueGoodsNet"),
)
NET_INCOME_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "NetIncomeLoss"),
    ("us-gaap", "ProfitLoss"),
)
CASH_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
    ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
    ("us-gaap", "Cash"),
)
LONG_TERM_DEBT_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "LongTermDebtNoncurrent"),
    ("us-gaap", "LongTermDebt"),
)
CURRENT_DEBT_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "LongTermDebtCurrent"),
    ("us-gaap", "DebtCurrent"),
    ("us-gaap", "ShortTermBorrowings"),
)
COMBINED_DEBT_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "DebtLongtermAndShorttermCombinedAmount"),
)
SHARES_TAGS: tuple[tuple[str, str], ...] = (
    ("dei", "EntityCommonStockSharesOutstanding"),
    ("us-gaap", "CommonStockSharesOutstanding"),
    ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
    ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding"),
)
OCF_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
    ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
)

# ---- additional tag-fallbacks for the full PeriodFinancials line items -------
# The quant models (Altman Z'', Beneish M, Piotroski F, EV/Sales, up-market)
# need the balance-sheet/income-statement items below; the same first-match
# fallback discipline as above gives XBRL-tag resilience across filers.
TOTAL_ASSETS_TAGS: tuple[tuple[str, str], ...] = (("us-gaap", "Assets"),)
CURRENT_ASSETS_TAGS: tuple[tuple[str, str], ...] = (("us-gaap", "AssetsCurrent"),)
CURRENT_LIABILITIES_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "LiabilitiesCurrent"),
)
TOTAL_LIABILITIES_TAGS: tuple[tuple[str, str], ...] = (("us-gaap", "Liabilities"),)
RETAINED_EARNINGS_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "RetainedEarningsAccumulatedDeficit"),
)
BOOK_EQUITY_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "StockholdersEquity"),
    (
        "us-gaap",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ),
)
RECEIVABLES_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "AccountsReceivableNetCurrent"),
    ("us-gaap", "ReceivablesNetCurrent"),
)
INVENTORY_TAGS: tuple[tuple[str, str], ...] = (("us-gaap", "InventoryNet"),)
NET_PPE_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "PropertyPlantAndEquipmentNet"),
)
GROSS_PPE_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "PropertyPlantAndEquipmentGross"),
)
GOODWILL_TAGS: tuple[tuple[str, str], ...] = (("us-gaap", "Goodwill"),)
INTANGIBLES_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "IntangibleAssetsNetExcludingGoodwill"),
    ("us-gaap", "FiniteLivedIntangibleAssetsNet"),
)
EBIT_TAGS: tuple[tuple[str, str], ...] = (("us-gaap", "OperatingIncomeLoss"),)
COGS_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "CostOfRevenue"),
    ("us-gaap", "CostOfGoodsAndServicesSold"),
    ("us-gaap", "CostOfGoodsSold"),
)
SGA_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "SellingGeneralAndAdministrativeExpense"),
    ("us-gaap", "GeneralAndAdministrativeExpense"),
)
DEPRECIATION_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "DepreciationDepletionAndAmortization"),
    ("us-gaap", "DepreciationAmortizationAndAccretionNet"),
    ("us-gaap", "DepreciationAndAmortization"),
    ("us-gaap", "Depreciation"),
)
CAPEX_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
    ("us-gaap", "PaymentsToAcquireProductiveAssets"),
)
INTEREST_EXPENSE_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "InterestExpense"),
    ("us-gaap", "InterestExpenseDebt"),
    ("us-gaap", "InterestExpenseNonoperating"),
)
SBC_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "ShareBasedCompensation"),
    ("us-gaap", "AllocatedShareBasedCompensationExpense"),
)
GOODWILL_IMPAIRMENT_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "GoodwillImpairmentLoss"),
)


@dataclass
class Evidence:
    """Provenance for one extracted figure (evidence surfaced)."""

    field: str
    taxonomy: str
    tag: str
    value: float
    period_end: str
    form: str
    filed: str
    accession: str


@dataclass
class FundamentalsRecord:
    """Per-ticker fundamentals + derived metrics + provenance."""

    cik: str
    entity_name: str
    revenue: float | None = None
    revenue_prior: float | None = None
    revenue_growth: float | None = None
    revenue_history: list[tuple[str, float]] = field(default_factory=list)
    net_income: float | None = None
    cash: float | None = None
    total_debt: float | None = None
    shares_outstanding: float | None = None
    operating_cash_flow: float | None = None
    monthly_burn: float | None = None
    runway_months: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    price_to_sales: float | None = None
    ev_to_sales: float | None = None
    evidence: dict[str, Evidence] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    data_completeness: float = 0.0


# ---- pure parsing of the companyfacts JSON ----------------------------------


def _unit_facts(
    facts_json: dict[str, Any], taxonomy: str, tag: str, unit: str
) -> list[dict[str, Any]]:
    concept = (facts_json.get("facts") or {}).get(taxonomy, {}).get(tag)
    if not concept:
        return []
    units = concept.get("units") or {}
    rows = units.get(unit)
    if rows is None:  # tolerate alternate unit keys (e.g. "USD/shares")
        for key, value in units.items():
            if key.startswith(unit):
                rows = value
                break
    return [
        row
        for row in (rows or [])
        if isinstance(row, dict) and row.get("val") is not None
    ]


def _span_days(fact: dict[str, Any]) -> int | None:
    start, end = fact.get("start"), fact.get("end")
    if start and end:
        try:
            return (date.fromisoformat(end) - date.fromisoformat(start)).days
        except ValueError:
            return None
    return None


def _is_instant(fact: dict[str, Any]) -> bool:
    return "start" not in fact or fact.get("start") is None


def _is_annual(fact: dict[str, Any]) -> bool:
    span = _span_days(fact)
    if span is not None:
        return 350 <= span <= 380
    return fact.get("fp") == "FY" or fact.get("form") == "10-K"


def _is_quarterly(fact: dict[str, Any]) -> bool:
    span = _span_days(fact)
    if span is not None:
        return 80 <= span <= 100
    return fact.get("fp") in {"Q1", "Q2", "Q3", "Q4"}


def _sort_key(fact: dict[str, Any]) -> tuple[str, str]:
    return (str(fact.get("end", "")), str(fact.get("filed", "")))


def _to_evidence(
    field_name: str, taxonomy: str, tag: str, fact: dict[str, Any]
) -> Evidence:
    return Evidence(
        field=field_name,
        taxonomy=taxonomy,
        tag=tag,
        value=float(fact["val"]),
        period_end=str(fact.get("end", "")),
        form=str(fact.get("form", "")),
        filed=str(fact.get("filed", "")),
        accession=str(fact.get("accn", "")),
    )


def _extract(
    facts_json: dict[str, Any],
    field_name: str,
    candidates: tuple[tuple[str, str], ...],
    unit: str,
    kind: str,
) -> Evidence | None:
    """Tag-fallback extraction of the most recent fact of the given ``kind``."""
    classifier = {
        "instant": _is_instant,
        "annual": _is_annual,
        "quarterly": _is_quarterly,
    }.get(kind)
    for taxonomy, tag in candidates:
        rows = _unit_facts(facts_json, taxonomy, tag, unit)
        if not rows:
            continue
        matching = [r for r in rows if classifier(r)] if classifier else list(rows)
        if not matching:
            matching = list(rows)  # fall back to any period rather than miss the value
        best = max(matching, key=_sort_key)
        return _to_evidence(field_name, taxonomy, tag, best)
    return None


def _annual_series(
    facts_json: dict[str, Any],
    candidates: tuple[tuple[str, str], ...],
    unit: str = "USD",
) -> tuple[list[Evidence], str | None]:
    """Annual facts (one per fiscal-year-end, latest filing wins), oldest→newest."""
    for taxonomy, tag in candidates:
        rows = [
            r for r in _unit_facts(facts_json, taxonomy, tag, unit) if _is_annual(r)
        ]
        if not rows:
            continue
        by_end: dict[str, dict[str, Any]] = {}
        for row in rows:
            end = str(row.get("end", ""))
            if end not in by_end or _sort_key(row) > _sort_key(by_end[end]):
                by_end[end] = row
        ordered = sorted(by_end.values(), key=lambda r: str(r.get("end", "")))
        return [_to_evidence("revenue", taxonomy, tag, r) for r in ordered], tag
    return [], None


def _total_debt(facts_json: dict[str, Any]) -> Evidence | None:
    combined = _extract(facts_json, "total_debt", COMBINED_DEBT_TAGS, "USD", "instant")
    if combined is not None:
        return combined
    long_term = _extract(
        facts_json, "total_debt", LONG_TERM_DEBT_TAGS, "USD", "instant"
    )
    current = _extract(facts_json, "total_debt", CURRENT_DEBT_TAGS, "USD", "instant")
    if long_term is None and current is None:
        return None
    total = (long_term.value if long_term else 0.0) + (
        current.value if current else 0.0
    )
    primary = long_term or current
    assert primary is not None
    return Evidence(
        field="total_debt",
        taxonomy=primary.taxonomy,
        tag=primary.tag if current is None else f"{primary.tag}+current",
        value=total,
        period_end=primary.period_end,
        form=primary.form,
        filed=primary.filed,
        accession=primary.accession,
    )


def compute_fundamentals(
    facts_json: dict[str, Any],
    *,
    current_price: float | None = None,
    market_cap: float | None = None,
) -> FundamentalsRecord:
    """Derive the fundamentals record from a companyfacts JSON payload (pure)."""
    raw_cik = facts_json.get("cik")
    cik = str(raw_cik).zfill(10) if raw_cik is not None else ""
    record = FundamentalsRecord(
        cik=cik, entity_name=str(facts_json.get("entityName", ""))
    )

    # Revenue + growth (annual series).
    rev_series, _ = _annual_series(facts_json, REVENUE_TAGS)
    if rev_series:
        record.revenue = rev_series[-1].value
        record.revenue_history = [(e.period_end, e.value) for e in rev_series]
        record.evidence["revenue"] = rev_series[-1]
        if len(rev_series) >= 2:
            record.revenue_prior = rev_series[-2].value
            if record.revenue_prior:
                record.revenue_growth = (record.revenue - record.revenue_prior) / abs(
                    record.revenue_prior
                )

    for name, candidates, unit, kind in (
        ("net_income", NET_INCOME_TAGS, "USD", "annual"),
        ("cash", CASH_TAGS, "USD", "instant"),
        ("shares_outstanding", SHARES_TAGS, "shares", "instant"),
        ("operating_cash_flow", OCF_TAGS, "USD", "annual"),
    ):
        evidence = _extract(facts_json, name, candidates, unit, kind)
        if evidence is not None:
            setattr(record, name, evidence.value)
            record.evidence[name] = evidence

    debt_evidence = _total_debt(facts_json)
    if debt_evidence is not None:
        record.total_debt = debt_evidence.value
        record.evidence["total_debt"] = debt_evidence

    # Burn rate + cash runway (the survival metric). Burn is from annual OCF.
    if record.operating_cash_flow is not None and record.operating_cash_flow < 0:
        record.monthly_burn = -record.operating_cash_flow / 12.0
        if record.cash is not None and record.monthly_burn > 0:
            record.runway_months = record.cash / record.monthly_burn

    # Market cap (price x EDGAR shares) and debt-aware valuation.
    if market_cap is None and current_price is not None and record.shares_outstanding:
        market_cap = current_price * record.shares_outstanding
    record.market_cap = market_cap
    if market_cap is not None:
        if record.revenue and record.revenue > 0:
            record.price_to_sales = market_cap / record.revenue
        if record.total_debt is not None and record.cash is not None:
            record.enterprise_value = market_cap + record.total_debt - record.cash
            if record.revenue and record.revenue > 0:
                record.ev_to_sales = record.enterprise_value / record.revenue

    _flag_completeness(record, rev_series)
    return record


def _flag_completeness(record: FundamentalsRecord, rev_series: list[Evidence]) -> None:
    core = (
        record.revenue,
        record.cash,
        record.shares_outstanding,
        record.operating_cash_flow,
    )
    present = sum(1 for value in core if value is not None)
    record.data_completeness = present / len(core)
    if present < len(core):
        record.flags.append("fundamentals-incomplete")
    if record.revenue is None or record.cash is None:
        record.flags.append("low-confidence")
    if len(rev_series) < 2:
        record.flags.append("limited-history")


# ---- companyfacts -> PeriodFinancials (the scored fundamentals seam) ---------
#
# ``compute_fundamentals`` above yields the human-facing ``FundamentalsRecord``.
# The scoring models (Altman Z'', Beneish M, Piotroski F, EV/Sales,
# up-market) instead consume :class:`PeriodFinancials` for the latest two fiscal
# years. This section bridges the canonical companyfacts JSON to those two
# periods, anchoring on real fiscal-year-ends (so a June-FYE filer or a filer
# whose current revenue moved to a different XBRL tag is handled correctly) and
# aligning every balance-sheet/income line item to the same period end.


@dataclass
class FundamentalsEvidence:
    """The fundamentals slice of the per-ticker evidence, parsed from companyfacts.

    Pure data (no network). ``period_t``/``period_t1`` are the latest two
    fiscal years; any line item the filing does not disclose stays ``None``
    (suppress-not-impute). ``completeness`` carries only parser-level gaps -
    the scorer adds its own suppression notes.
    """

    entity_name: str = ""
    period_t: PeriodFinancials | None = None
    period_t1: PeriodFinancials | None = None
    revenue_growth: float | None = None
    financials_period: str = ""  # period_t fiscal-year-end (e.g. "2025-06-30")
    financials_filed: str = ""  # latest filing date backing period_t
    completeness: list[str] = field(default_factory=list)


def _fiscal_year_ends(facts_json: dict[str, Any]) -> list[str]:
    """Distinct fiscal-year-end dates (annual 10-K periods), oldest -> newest.

    Derived from ``us-gaap`` financial-statement facts whose ``fp == "FY"`` and
    form is a 10-K - their period ``end`` is the true fiscal-year-end. This is
    robust to a non-December fiscal year and to revenue/line items migrating
    between XBRL tags over a filer's history. The ``us-gaap`` restriction is
    deliberate: ``dei`` cover-page facts (e.g. shares outstanding) also carry
    ``fp == "FY"``/``10-K`` but are dated at *filing*, not fiscal-year-end, so
    including them would mis-anchor the period.
    """
    gaap = (facts_json.get("facts") or {}).get("us-gaap")
    if not isinstance(gaap, dict):
        return []
    ends: set[str] = set()
    for concept in gaap.values():
        if not isinstance(concept, dict):
            continue
        for rows in (concept.get("units") or {}).values():
            for row in rows or ():
                if (
                    isinstance(row, dict)
                    and row.get("fp") == "FY"
                    and str(row.get("form", "")).startswith("10-K")
                    and row.get("end")
                ):
                    ends.add(str(row["end"]))
    return sorted(ends)


def _fact_at_end(
    facts_json: dict[str, Any],
    candidates: tuple[tuple[str, str], ...],
    unit: str,
    end: str,
    *,
    instant: bool,
) -> tuple[float | None, str]:
    """Tag-fallback value at a specific period end (latest filing wins).

    ``instant`` selects balance-sheet point-in-time facts (no ``start``);
    otherwise an annual-duration fact (~1 fiscal year, or an FY 10-K period) is
    required - which excludes quarterly and year-to-date rows sharing the end.
    Returns ``(value, filed)``; ``(None, "")`` when nothing matches.
    """
    for taxonomy, tag in candidates:
        matching: list[dict[str, Any]] = []
        for row in _unit_facts(facts_json, taxonomy, tag, unit):
            if str(row.get("end", "")) != end:
                continue
            if _is_instant(row) != instant:
                continue
            if not instant:
                span = _span_days(row)
                annual = (span is not None and 350 <= span <= 380) or (
                    row.get("fp") == "FY"
                    and str(row.get("form", "")).startswith("10-K")
                )
                if not annual:
                    continue
            matching.append(row)
        if matching:
            best = max(matching, key=lambda r: str(r.get("filed", "")))
            return float(best["val"]), str(best.get("filed", ""))
    return None, ""


def _shares_at_end(facts_json: dict[str, Any], end: str) -> float | None:
    """Share count for the fiscal year ending ``end``.

    Cover-page share counts (``dei``) are dated at filing, not fiscal-year-end,
    so the fact nearest the period end within a sensible window is taken;
    balance-sheet share tags (which do land on the period end) are preferred.
    """
    # Cover-page share counts (``dei``) are dated at filing, not fiscal-year-end,
    # so the nearest fact within a window is taken (``SHARES_TAGS`` order applies).
    target = date.fromisoformat(end)
    for taxonomy, tag in SHARES_TAGS:
        best_key: tuple[int, str] | None = None
        best_val: float | None = None
        for row in _unit_facts(facts_json, taxonomy, tag, "shares"):
            raw_end = row.get("end")
            if not raw_end:
                continue
            try:
                delta = (date.fromisoformat(str(raw_end)) - target).days
            except ValueError:
                continue
            if not -45 <= delta <= 180:  # this fiscal year's reported count
                continue
            key = (abs(delta), str(row.get("filed", "")))
            if best_key is None or key < best_key:
                best_key, best_val = key, float(row["val"])
        if best_val is not None:
            return best_val
    return None


def _period_at_end(
    facts_json: dict[str, Any], end: str
) -> tuple[PeriodFinancials, str]:
    """Assemble one fiscal year's :class:`PeriodFinancials`, aligned to ``end``.

    Returns the period plus the latest filing date backing any of its facts.
    """
    filed_dates: list[str] = []

    def inst(candidates: tuple[tuple[str, str], ...]) -> float | None:
        value, filed = _fact_at_end(facts_json, candidates, "USD", end, instant=True)
        if filed:
            filed_dates.append(filed)
        return value

    def dur(candidates: tuple[tuple[str, str], ...]) -> float | None:
        value, filed = _fact_at_end(facts_json, candidates, "USD", end, instant=False)
        if filed:
            filed_dates.append(filed)
        return value

    period = PeriodFinancials(
        total_assets=inst(TOTAL_ASSETS_TAGS),
        current_assets=inst(CURRENT_ASSETS_TAGS),
        current_liabilities=inst(CURRENT_LIABILITIES_TAGS),
        cash=inst(CASH_TAGS),
        receivables=inst(RECEIVABLES_TAGS),
        inventory=inst(INVENTORY_TAGS),
        net_ppe=inst(NET_PPE_TAGS),
        gross_ppe=inst(GROSS_PPE_TAGS),
        total_liabilities=inst(TOTAL_LIABILITIES_TAGS),
        total_debt=inst(COMBINED_DEBT_TAGS),
        long_term_debt=inst(LONG_TERM_DEBT_TAGS),
        retained_earnings=inst(RETAINED_EARNINGS_TAGS),
        book_equity=inst(BOOK_EQUITY_TAGS),
        revenue=dur(REVENUE_TAGS),
        cogs=dur(COGS_TAGS),
        sga=dur(SGA_TAGS),
        depreciation=dur(DEPRECIATION_TAGS),
        ebit=dur(EBIT_TAGS),
        net_income=dur(NET_INCOME_TAGS),
        operating_cash_flow=dur(OCF_TAGS),
        capex=dur(CAPEX_TAGS),
        interest_expense=dur(INTEREST_EXPENSE_TAGS),
        shares_outstanding=_shares_at_end(facts_json, end),
        goodwill=inst(GOODWILL_TAGS),
        intangibles=inst(INTANGIBLES_TAGS),
        goodwill_impairment=dur(GOODWILL_IMPAIRMENT_TAGS),
        sbc=dur(SBC_TAGS),
    )
    return period, (max(filed_dates) if filed_dates else "")


def period_financials_from_companyfacts(
    facts_json: dict[str, Any],
) -> FundamentalsEvidence:
    """Parse companyfacts into the latest two fiscal years (pure, no network).

    Suppress-not-impute: with no annual 10-K period the fundamentals slice is
    suppressed and flagged; with only one, ``period_t1`` stays ``None`` and the
    two-period models degrade rather than fabricate a prior year.
    """
    evidence = FundamentalsEvidence(entity_name=str(facts_json.get("entityName", "")))
    fiscal_ends = _fiscal_year_ends(facts_json)
    if not fiscal_ends:
        evidence.completeness.append(
            "fundamentals suppressed (no annual 10-K period in companyfacts)"
        )
        return evidence

    end_t = fiscal_ends[-1]
    evidence.period_t, evidence.financials_filed = _period_at_end(facts_json, end_t)
    evidence.financials_period = end_t
    if len(fiscal_ends) >= 2:
        evidence.period_t1, _ = _period_at_end(facts_json, fiscal_ends[-2])
    else:
        evidence.completeness.append(
            "fundamentals limited to one annual period (prior year unavailable)"
        )

    rev_t = evidence.period_t.revenue if evidence.period_t else None
    rev_t1 = evidence.period_t1.revenue if evidence.period_t1 else None
    if rev_t is not None and rev_t1:
        evidence.revenue_growth = (rev_t - rev_t1) / abs(rev_t1)
    return evidence


# ---- fetch boundary: bulk zip + per-CIK provider ----------------------------


def companyfacts_from_zip(zip_path: Path, cik: str) -> dict[str, Any]:
    """Read one CIK's companyfacts JSON from an EDGAR ``companyfacts.zip``.

    Bulk mode is preferred at full-universe scale (one download vs thousands of
    per-ticker calls).
    """
    member = f"CIK{str(cik).zfill(10)}.json"
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(member) as handle:
            payload: dict[str, Any] = json.loads(handle.read())
    return payload


class EdgarFundamentalsProvider(FundamentalsProvider):
    """Fetches companyfacts via the hardened HTTP client and computes them."""

    def __init__(self, client: SafeHttpClient, *, identity: str | None = None) -> None:
        self._client = client
        if identity:
            # edgartools' SEC-required identity registration (used by its typed
            # filing accessors elsewhere); the companyfacts fetch below still
            # goes through our rate-limited, cached, security-hardened client.
            import edgar

            edgar.set_identity(identity)

    @property
    def name(self) -> str:
        return "edgar"

    def fetch_companyfacts(self, cik: str) -> dict[str, Any]:
        url = COMPANYFACTS_URL_TEMPLATE.format(cik=str(cik).zfill(10))
        payload: dict[str, Any] = self._client.get_json(url, provider="edgar")
        return payload

    def get_fundamentals(self, cik: str) -> FundamentalsRecord:
        return compute_fundamentals(self.fetch_companyfacts(cik))
