"""Insider & institutional behavior.

Tracks what the people with the most information and money are *doing*. The
analytical value is in the Form 4 **transaction-code** field, not net shares:

* Code **P** (open-market purchase) is the only bullish-conviction signal -
  insiders deploying personal cash; cluster buying = distinct P buyers in a
  window + aggregate dollar value.
* Code **S** (open-market sale) is bearish only if NOT preceded by an option
  exercise; 10b5-1 plan sales are flagged separately (non-discretionary).
* Noise codes are excluded: **A** (grant) and **M** (option exercise) are comp
  mechanics; **F** (shares withheld for taxes) is mandatory and must NEVER be
  counted as selling; **G/C/J/D** are administrative.

Also: Form 144 proposed sales (forward supply overhang, precede the Form 4);
13D (activist) vs 13G (passive) >5% crossings + 13G→13D conversions; and 13F
institutional accumulation. The code-P buying signal softens a dilution
read; selling / a wave of 144s hardens it.

The analytical core is pure over structured transaction lists (testable);
edgartools is the fetch boundary (Forms 3/4/5, 144, 13D/G, 13F).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from defusedxml.ElementTree import ParseError, fromstring

from pennytune.providers.base import ProviderError
from pennytune.providers.http import SafeHttpClient

__all__ = [
    "CONVICTION_BUY_CODE",
    "OPEN_MARKET_SELL_CODE",
    "EXCLUDED_CODES",
    "InsiderTransaction",
    "Form144",
    "OwnershipFiling",
    "InstitutionalPosition",
    "OwnershipSignals",
    "InsiderProfile",
    "InsiderEvidence",
    "detect_ownership_signals",
    "compute_insider_signal",
    "parse_form4_xml",
    "form144s_from_submissions",
    "ownership_filings_from_submissions",
    "raw_ownership_doc",
    "EdgarInsiderProvider",
]

CONVICTION_BUY_CODE = "P"  # open-market purchase
OPEN_MARKET_SELL_CODE = "S"  # open-market sale
# Comp mechanics + administrative codes - never conviction, and F is NEVER a sale.
EXCLUDED_CODES = frozenset({"A", "M", "F", "G", "C", "J", "D"})
_CLUSTER_BUYERS = 2
_FORM144_CLUSTER = 2
_HIGH_CONVICTION_BUYERS = 3
_HIGH_CONVICTION_VALUE = 500_000.0


@dataclass
class InsiderTransaction:
    insider: str
    code: str
    shares: float
    value: float
    date: str
    role: str = ""
    is_10b5_1: bool = False
    preceded_by_exercise: bool = False


@dataclass
class Form144:
    insider: str
    date: str
    shares: float = 0.0
    value: float = 0.0


@dataclass
class OwnershipFiling:
    filer: str
    form_type: str  # "SC 13D" | "SC 13G" (and amendments)
    date: str
    pct: float | None = None


@dataclass
class InstitutionalPosition:
    institution: str
    shares: float
    change_shares: float
    quarter: str = ""


@dataclass
class OwnershipSignals:
    activist_13d: int = 0
    passive_13g: int = 0
    crossings_over_5pct: int = 0
    conversions_13g_to_13d: list[str] = field(default_factory=list)


@dataclass
class InsiderProfile:
    distinct_p_buyers: int = 0
    buy_count: int = 0
    total_buy_value: float = 0.0
    conviction_score: int = 0
    cluster_buy: bool = False
    discretionary_sell_value: float = 0.0
    plan_sell_value: float = 0.0  # 10b5-1, non-discretionary
    exercise_linked_sell_value: float = 0.0
    excluded_count: int = 0  # A/M/F/G/C/J/D - surfaced for transparency, not scored
    form144_count: int = 0
    form144_overhang: bool = False
    ownership: OwnershipSignals = field(default_factory=OwnershipSignals)
    institutional_accumulation: int = 0
    net_signal: str = "neutral"  # bullish | bearish | neutral
    confidence: str = "low"
    insider_buying: bool = False  # cluster code-P buying → softens dilution
    evidence: list[str] = field(default_factory=list)


def detect_ownership_signals(filings: Sequence[OwnershipFiling]) -> OwnershipSignals:
    """13D (activist) vs 13G (passive) >5% events, and 13G→13D conversions."""
    activist = sum(1 for f in filings if "13D" in f.form_type.upper())
    passive = sum(1 for f in filings if "13G" in f.form_type.upper())
    crossings = sum(1 for f in filings if f.pct is not None and f.pct > 5.0)

    by_filer: dict[str, list[OwnershipFiling]] = {}
    for filing in filings:
        by_filer.setdefault(filing.filer, []).append(filing)
    conversions: list[str] = []
    for filer, filer_filings in by_filer.items():
        seen_13g = False
        for filing in sorted(filer_filings, key=lambda f: f.date):
            form = filing.form_type.upper()
            if "13G" in form:
                seen_13g = True
            elif "13D" in form and seen_13g:
                conversions.append(filer)
                break
    return OwnershipSignals(
        activist_13d=activist,
        passive_13g=passive,
        crossings_over_5pct=crossings,
        conversions_13g_to_13d=conversions,
    )


def compute_insider_signal(
    transactions: Sequence[InsiderTransaction],
    *,
    form144s: Sequence[Form144] = (),
    ownership_filings: Sequence[OwnershipFiling] = (),
    institutional: Sequence[InstitutionalPosition] = (),
) -> InsiderProfile:
    """Decompose Form 4 codes into a conviction signal."""
    buys = [t for t in transactions if t.code == CONVICTION_BUY_CODE]
    distinct_buyers = len({t.insider for t in buys})
    total_buy_value = sum(t.value for t in buys)
    cluster_buy = distinct_buyers >= _CLUSTER_BUYERS

    sells = [t for t in transactions if t.code == OPEN_MARKET_SELL_CODE]
    discretionary = [t for t in sells if not t.is_10b5_1 and not t.preceded_by_exercise]
    plan = [t for t in sells if t.is_10b5_1]
    exercise_linked = [t for t in sells if t.preceded_by_exercise and not t.is_10b5_1]
    discretionary_value = sum(t.value for t in discretionary)
    excluded = sum(1 for t in transactions if t.code in EXCLUDED_CODES)

    form144_overhang = len(form144s) >= _FORM144_CLUSTER
    ownership = detect_ownership_signals(ownership_filings)
    accumulation = sum(1 for p in institutional if p.change_shares > 0)

    if cluster_buy and total_buy_value > discretionary_value:
        net = "bullish"
    elif discretionary_value > 0 or form144_overhang:
        net = "bearish"
    else:
        net = "neutral"

    if (
        distinct_buyers >= _HIGH_CONVICTION_BUYERS
        or total_buy_value >= _HIGH_CONVICTION_VALUE
    ):
        confidence = "high"
    elif cluster_buy or discretionary or form144_overhang:
        confidence = "medium"
    else:
        confidence = "low"

    conviction_score = min(
        100,
        distinct_buyers * 20 + (20 if total_buy_value >= _HIGH_CONVICTION_VALUE else 0),
    )

    evidence: list[str] = []
    if cluster_buy:
        evidence.append(
            f"cluster buy: {distinct_buyers} insiders, ~${total_buy_value:,.0f}"
        )
    if discretionary:
        evidence.append(f"discretionary insider selling (~${discretionary_value:,.0f})")
    if plan:
        evidence.append(
            f"{len(plan)} 10b5-1 (non-discretionary) sale(s) noted separately"
        )
    if form144_overhang:
        evidence.append(
            f"{len(form144s)} Form 144 proposed sales → forward supply overhang"
        )
    if ownership.conversions_13g_to_13d:
        evidence.append(
            f"13G→13D conversion(s): {', '.join(ownership.conversions_13g_to_13d)}"
        )

    return InsiderProfile(
        distinct_p_buyers=distinct_buyers,
        buy_count=len(buys),
        total_buy_value=total_buy_value,
        conviction_score=conviction_score,
        cluster_buy=cluster_buy,
        discretionary_sell_value=discretionary_value,
        plan_sell_value=sum(t.value for t in plan),
        exercise_linked_sell_value=sum(t.value for t in exercise_linked),
        excluded_count=excluded,
        form144_count=len(form144s),
        form144_overhang=form144_overhang,
        ownership=ownership,
        institutional_accumulation=accumulation,
        net_signal=net,
        confidence=confidence,
        insider_buying=cluster_buy,
        evidence=evidence,
    )


# ---- fetch boundary: Form 4/5 XML + submissions-derived 144 / 13D-G ----------
#
# The analytical core above is pure; this section turns live EDGAR into the
# transaction lists it consumes. Form 4/5 transaction details (the all-important
# transaction CODE) live only in each filing's ownership XML, so those are
# fetched per filing (windowed + capped to bound requests); Form 144 and 13D/G
# are counted straight from the already-fetched issuer submissions.

# Only Form 4/5 carry transactions; Form 3 is an initial-holdings statement.
TRANSACTION_FORMS = frozenset({"4", "4/A", "5", "5/A"})
FORM144_FORMS = frozenset({"144", "144/A"})
OWNERSHIP_FORMS = frozenset(
    {"SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A", "SCHEDULE 13D", "SCHEDULE 13G"}
)
OWNERSHIP_DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{doc}"
_DEFAULT_FORM4_WINDOW_DAYS = 365  # "recent" insider activity
_DEFAULT_MAX_FORM4_DOCS = 12  # request budget per ticker


@dataclass
class InsiderEvidence:
    """The insider slice of the per-ticker evidence, parsed from live EDGAR.

    Pure data the scorer consumes via :func:`compute_insider_signal`. An empty
    ``transactions`` with a "no recent insider buying" note is a legitimate,
    honest result (most micro-caps have sparse insider activity), never an error.
    """

    transactions: tuple[InsiderTransaction, ...] = ()
    form144s: tuple[Form144, ...] = ()
    ownership_filings: tuple[OwnershipFiling, ...] = ()
    completeness: list[str] = field(default_factory=list)


def _xml_float(text: str | None) -> float | None:
    if text is None:
        return None
    try:
        return float(text.strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def raw_ownership_doc(primary_document: str) -> str:
    """The raw ownership-XML filename for a Form 3/4/5.

    EDGAR's ``primaryDocument`` for an ownership form points at the
    XSL-*rendered* HTML (e.g. ``xslF345X06/form4.xml``); the parseable XML is the
    same file with the ``xslNNN/`` rendering prefix stripped (``form4.xml``).
    """
    return primary_document.rsplit("/", 1)[-1]


def parse_form4_xml(
    xml_bytes: bytes | str, *, filing_date: str = ""
) -> list[InsiderTransaction]:
    """Parse a Form 4/5 ownership XML into non-derivative InsiderTransactions.

    The transaction CODE (``transactionCoding/transactionCode``: P/S/A/F/M/…) is
    read verbatim so the analytics can keep open-market purchases (P) distinct
    from routine grants (A) and tax-withholding (F). A holdings-only filing (no
    transactions) yields an empty list - suppress-not-impute.
    """
    try:
        root = fromstring(
            xml_bytes.decode("utf-8", "replace")
            if isinstance(xml_bytes, bytes)
            else xml_bytes
        )
    except ParseError:
        return []

    owner = (
        root.findtext(".//reportingOwner/reportingOwnerId/rptOwnerName") or ""
    ).strip()
    title = (root.findtext(".//reportingOwnerRelationship/officerTitle") or "").strip()
    is_director = (
        root.findtext(".//reportingOwnerRelationship/isDirector") or ""
    ).strip() in ("1", "true")
    role = title or ("Director" if is_director else "")
    # A 10b5-1 plan is disclosed in the filing footnotes; if present, attribute
    # discretionary sells in this filing to the plan (non-discretionary).
    footnote_blob = " ".join(
        (fn.text or "") for fn in root.findall(".//footnotes/footnote")
    ).lower()
    is_plan = "10b5-1" in footnote_blob

    transactions: list[InsiderTransaction] = []
    for txn in root.findall(".//nonDerivativeTransaction"):
        code = (txn.findtext("transactionCoding/transactionCode") or "").strip()
        if not code:
            continue
        shares = _xml_float(txn.findtext("transactionAmounts/transactionShares/value"))
        price = _xml_float(
            txn.findtext("transactionAmounts/transactionPricePerShare/value")
        )
        txn_date = (txn.findtext("transactionDate/value") or filing_date).strip()
        value = (shares or 0.0) * (price or 0.0)
        transactions.append(
            InsiderTransaction(
                insider=owner,
                code=code,
                shares=shares or 0.0,
                value=value,
                date=txn_date,
                role=role,
                is_10b5_1=is_plan,
            )
        )
    return transactions


def _recent(submissions: dict[str, Any]) -> dict[str, list[Any]]:
    recent = (submissions.get("filings") or {}).get("recent") or {}
    return recent if isinstance(recent, dict) else {}


def form144s_from_submissions(submissions: dict[str, Any]) -> list[Form144]:
    """Form 144 proposed-sale notices (forward supply overhang) from submissions.

    The 144 cover-page shares/value require the filing document; the overhang
    signal only needs the *count*, so the lighter submissions-derived list
    suffices (no extra request).
    """
    recent = _recent(submissions)
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    out: list[Form144] = []
    for index, form in enumerate(forms):
        if str(form).strip().upper() in FORM144_FORMS:
            out.append(
                Form144(
                    insider="(Form 144 filer)",
                    date=str(dates[index]) if index < len(dates) else "",
                )
            )
    return out


def ownership_filings_from_submissions(
    submissions: dict[str, Any],
) -> list[OwnershipFiling]:
    """13D (activist) / 13G (passive) >5% filings from submissions.

    The acquirer (filer) name and ownership percent live in the schedule
    document, not the issuer submissions index, so ``filer`` is keyed to the
    accession (no false 13G→13D conversions) and ``pct`` is left ``None``
    (crossings suppressed) - the activist-vs-passive counts still register.
    """
    recent = _recent(submissions)
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accns = recent.get("accessionNumber") or []
    out: list[OwnershipFiling] = []
    for index, form in enumerate(forms):
        if str(form).strip().upper() in OWNERSHIP_FORMS:
            out.append(
                OwnershipFiling(
                    filer=str(accns[index]) if index < len(accns) else str(index),
                    form_type=str(form),
                    date=str(dates[index]) if index < len(dates) else "",
                )
            )
    return out


class EdgarInsiderProvider:
    """Fetch boundary: live Form 4/5 transactions + 144 / 13D-G from EDGAR.

    Form 4/5 transaction codes live only in each filing's ownership XML, fetched
    through the hardened HTTP client; 144 and 13D/G are read from the already
    fetched issuer submissions. The scored signal is computed downstream by the
    pure :func:`compute_insider_signal`, preserving the P-vs-A/F distinction.
    """

    def __init__(self, client: SafeHttpClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "edgar"

    def _doc_url(self, cik: str, accession: str, primary_document: str) -> str:
        return OWNERSHIP_DOC_URL.format(
            cik=int(cik),
            accn=accession.replace("-", ""),
            doc=raw_ownership_doc(primary_document),
        )

    def _recent_form4_filings(
        self,
        submissions: dict[str, Any],
        *,
        now: datetime | None,
        window_days: int,
        cap: int,
    ) -> tuple[list[tuple[str, str, str]], bool]:
        """The most recent (date, accession, primaryDocument) Form 4/5 filings.

        ``submissions.recent`` is newest-first; returns up to ``cap`` filings
        within the window and whether the cap was hit.
        """
        recent = _recent(submissions)
        forms = recent.get("form") or []
        dates = recent.get("filingDate") or []
        accns = recent.get("accessionNumber") or []
        docs = recent.get("primaryDocument") or []
        selected: list[tuple[str, str, str]] = []
        for index, form in enumerate(forms):
            if str(form).strip() not in TRANSACTION_FORMS:
                continue
            filing_date = str(dates[index]) if index < len(dates) else ""
            if now is not None and not _within_days(filing_date, now, window_days):
                continue
            if index < len(accns) and index < len(docs):
                selected.append((filing_date, str(accns[index]), str(docs[index])))
            if len(selected) >= cap:
                return selected, True
        return selected, False

    def get_insider_evidence(
        self,
        cik: str,
        *,
        submissions: dict[str, Any] | None,
        now: datetime | None = None,
        window_days: int = _DEFAULT_FORM4_WINDOW_DAYS,
        max_form4_docs: int = _DEFAULT_MAX_FORM4_DOCS,
    ) -> InsiderEvidence:
        """Assemble live insider evidence for one CIK (reusing submissions)."""
        if submissions is None:
            return InsiderEvidence(
                completeness=["insider degraded (submissions unavailable)"]
            )
        completeness: list[str] = []
        form144s = form144s_from_submissions(submissions)
        ownership = ownership_filings_from_submissions(submissions)
        selected, capped = self._recent_form4_filings(
            submissions, now=now, window_days=window_days, cap=max_form4_docs
        )
        transactions: list[InsiderTransaction] = []
        for filing_date, accession, document in selected:
            try:
                xml = self._client.get_bytes(
                    self._doc_url(cik, accession, document), provider="edgar"
                )
            except ProviderError:
                continue  # one unreadable Form 4 never aborts the rest
            transactions.extend(parse_form4_xml(xml, filing_date=filing_date))
        if not selected:
            completeness.append("no recent insider Form 4/5 filings")
        elif capped:
            completeness.append(
                f"insider scan limited to the {max_form4_docs} most recent "
                "Form 4/5 filings"
            )
        return InsiderEvidence(
            transactions=tuple(transactions),
            form144s=tuple(form144s),
            ownership_filings=tuple(ownership),
            completeness=completeness,
        )


def _within_days(filing_date: str, now: datetime, window_days: int) -> bool:
    try:
        return (now.date() - date.fromisoformat(filing_date)).days <= window_days
    except ValueError:
        return True  # unparseable date → don't exclude (keep, flagged elsewhere)
