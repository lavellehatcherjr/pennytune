"""8-K item-code event engine: structured material-event scoring.

Turns every 8-K into a scored, categorized event using its **item codes** (the
SEC's structured numbering), with no NLP - just a dictionary lookup over the
``items`` array the EDGAR ``submissions`` API already returns for each filing.
It produces a per-ticker "event tape" whose signals feed the dilution,
catalyst, manipulation-susceptibility, and delisting analyses.

The submissions ``filings.recent.items`` field is a parallel array of
comma-separated item-code strings (e.g. ``"1.01,3.02,9.01"``); parsing is
schema-tolerant and treats the response as untrusted external input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

__all__ = [
    "FINANCING",
    "GOVERNANCE",
    "DISTRESS",
    "PROMOTIONAL",
    "OPERATIONAL",
    "UNCATEGORIZED",
    "ITEM_TAXONOMY",
    "EightKEvent",
    "EventSignals",
    "EventTape",
    "classify_item",
    "normalize_code",
    "build_event",
    "parse_submissions_8k_events",
    "build_event_tape",
]

FINANCING = "financing"
GOVERNANCE = "governance"
DISTRESS = "distress"
PROMOTIONAL = "promotional"
OPERATIONAL = "operational"
UNCATEGORIZED = "uncategorized"

# Item code → (category, severity 0-5). Material-event taxonomy.
ITEM_TAXONOMY: dict[str, tuple[str, float]] = {
    "1.01": (FINANCING, 2.0),  # material agreement entered (often toxic financing)
    "1.02": (OPERATIONAL, 2.0),  # material agreement terminated (e.g. lost customer)
    "1.03": (DISTRESS, 5.0),  # bankruptcy / receivership (max severity)
    "2.02": (OPERATIONAL, 1.0),  # results of operations (earnings)
    "2.03": (DISTRESS, 3.0),  # direct financial obligation created
    "2.04": (DISTRESS, 4.0),  # triggering event accelerating an obligation
    "3.01": (DISTRESS, 4.0),  # delisting / continued-listing failure (delisting)
    "3.02": (FINANCING, 3.0),  # unregistered equity sales - dilution smoking gun
    "4.01": (DISTRESS, 3.0),  # auditor change
    "4.02": (DISTRESS, 5.0),  # non-reliance / restatement (max forensic severity)
    "5.02": (GOVERNANCE, 2.0),  # director/officer departure or appointment
    "5.03": (GOVERNANCE, 2.0),  # charter/bylaw amendment or fiscal-year change
    "5.06": (GOVERNANCE, 3.0),  # change in shell-company status
    "5.07": (GOVERNANCE, 1.0),  # submission to a shareholder vote
    "7.01": (PROMOTIONAL, 1.0),  # Reg FD disclosure
    "8.01": (PROMOTIONAL, 1.0),  # other events (micro-cap hype vector)
    "9.01": (OPERATIONAL, 0.0),  # financial statements & exhibits - boilerplate
}

_CODE_RE = re.compile(r"\d+\.\d+")
_PROMOTIONAL_CODES = frozenset({"7.01", "8.01"})
_DEFAULT_PROMO_THRESHOLD = 3
_DEFAULT_RECENCY_DAYS = 180


@dataclass
class EightKEvent:
    """A single 8-K, scored by item code (all items retained)."""

    accession: str
    filing_date: str
    form: str
    item_codes: list[str]
    category: str  # category of the highest-severity item
    severity: float  # max severity across items
    is_amendment: bool = False
    categories: list[str] = field(default_factory=list)


@dataclass
class EventSignals:
    """Recency-windowed signals routed to the dilution, news, manipulation, and
    delisting analyses (and the forensic-scoring issuance flag)."""

    has_unregistered_equity_sale: bool = False  # 3.02 → dilution
    unregistered_equity_count: int = 0
    issuance_indicator: bool = False  # 3.02 → Dechow issuance indicator
    has_delisting_notice: bool = False  # 3.01 → delisting risk
    has_bankruptcy: bool = False  # 1.03 → delisting risk / distress
    auditor_or_restatement_count: int = 0  # 4.01 / 4.02 → dilution
    charter_shell_vote_count: int = 0  # 5.03 / 5.06 / 5.07 → dilution
    officer_change_count: int = 0  # 5.02 → governance
    covenant_or_obligation_count: int = 0  # 2.03 / 2.04 → distress
    promotional_count: int = 0  # 7.01 / 8.01 → manipulation
    earnings_count: int = 0  # 2.02
    material_agreement_count: int = 0  # 1.01 / 1.02 → news


@dataclass
class EventTape:
    """Per-ticker event tape + aggregates + routed signals."""

    cik: str
    events: list[EightKEvent]
    item_counts: dict[str, int] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)
    recency_weighted: dict[str, float] = field(default_factory=dict)
    signals: EventSignals = field(default_factory=EventSignals)
    promotional_cadence: bool = False
    flags: list[str] = field(default_factory=list)


def normalize_code(raw_code: str) -> str:
    """Extract a bare ``N.NN`` item code from a possibly descriptive string."""
    match = _CODE_RE.search(raw_code or "")
    return match.group(0) if match else (raw_code or "").strip()


def classify_item(raw_code: str) -> tuple[str, float]:
    """Map an item code (or descriptive item string) to (category, severity)."""
    return ITEM_TAXONOMY.get(normalize_code(raw_code), (UNCATEGORIZED, 0.0))


def _split_items(items_field: object) -> list[str]:
    """Split the submissions ``items`` value (comma string or list) into codes."""
    if items_field is None:
        return []
    parts: list[str] = []
    if isinstance(items_field, str):
        parts = items_field.split(",")
    elif isinstance(items_field, (list, tuple)):
        for entry in items_field:
            parts.extend(str(entry).split(","))
    else:
        parts = str(items_field).split(",")
    return [normalize_code(p) for p in parts if normalize_code(p)]


def build_event(
    accession: str, filing_date: str, form: str, items_field: object
) -> EightKEvent:
    """Build one scored event from a filing's metadata + items value."""
    codes = _split_items(items_field)
    pairs = [classify_item(code) for code in codes]
    if pairs:
        severity = max(sev for _, sev in pairs)
        # Primary category = category of the first item at the max severity.
        category = next(cat for cat, sev in pairs if sev == severity)
    else:
        severity = 0.0
        category = UNCATEGORIZED
    return EightKEvent(
        accession=accession,
        filing_date=filing_date,
        form=form,
        item_codes=codes,
        category=category,
        severity=severity,
        is_amendment=form.strip().upper().endswith("/A"),
        categories=sorted({cat for cat, _ in pairs}),
    )


def parse_submissions_8k_events(submissions_json: dict[str, Any]) -> list[EightKEvent]:
    """Extract 8-K events from an EDGAR submissions payload (schema-tolerant)."""
    recent = (submissions_json.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    items = recent.get("items") or []
    accns = recent.get("accessionNumber") or []
    dates = recent.get("filingDate") or []

    events: list[EightKEvent] = []
    for index, form in enumerate(forms):
        if not str(form).startswith("8-K"):
            continue
        events.append(
            build_event(
                accession=str(accns[index]) if index < len(accns) else "",
                filing_date=str(dates[index]) if index < len(dates) else "",
                form=str(form),
                items_field=items[index] if index < len(items) else "",
            )
        )
    return events


def _age_days(filing_date: str, now: datetime) -> int | None:
    try:
        return (now.date() - date.fromisoformat(filing_date)).days
    except ValueError:
        return None


def _in_window(event: EightKEvent, now: datetime | None, recency_days: int) -> bool:
    if now is None:
        return True
    age = _age_days(event.filing_date, now)
    return age is None or age <= recency_days


def _recency_weight(
    event: EightKEvent, now: datetime | None, recency_days: int
) -> float:
    if now is None:
        return 1.0
    age = _age_days(event.filing_date, now)
    if age is None:
        return 1.0
    return max(0.0, 1.0 - age / recency_days)


def build_event_tape(
    events: list[EightKEvent],
    *,
    cik: str = "",
    now: datetime | None = None,
    recency_days: int = _DEFAULT_RECENCY_DAYS,
    promo_threshold: int = _DEFAULT_PROMO_THRESHOLD,
) -> EventTape:
    """Aggregate events into counts, recency-weighted severity, and routed signals."""
    item_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    recency_weighted: dict[str, float] = {}
    for event in events:
        category_counts[event.category] = category_counts.get(event.category, 0) + 1
        weight = _recency_weight(event, now, recency_days)
        recency_weighted[event.category] = (
            recency_weighted.get(event.category, 0.0) + event.severity * weight
        )
        for code in event.item_codes:
            item_counts[code] = item_counts.get(code, 0) + 1

    signals = EventSignals()
    windowed = [e for e in events if _in_window(e, now, recency_days)]
    for event in windowed:
        for code in event.item_codes:
            if code == "3.02":
                signals.unregistered_equity_count += 1
                signals.has_unregistered_equity_sale = True
                signals.issuance_indicator = True
            elif code == "3.01":
                signals.has_delisting_notice = True
            elif code == "1.03":
                signals.has_bankruptcy = True
            elif code in {"4.01", "4.02"}:
                signals.auditor_or_restatement_count += 1
            elif code in {"5.03", "5.06", "5.07"}:
                signals.charter_shell_vote_count += 1
            elif code == "5.02":
                signals.officer_change_count += 1
            elif code in {"2.03", "2.04"}:
                signals.covenant_or_obligation_count += 1
            elif code in _PROMOTIONAL_CODES:
                signals.promotional_count += 1
            elif code == "2.02":
                signals.earnings_count += 1
            elif code in {"1.01", "1.02"}:
                signals.material_agreement_count += 1

    # Promotional cadence: SUSTAINED promotional filings with NO earnings
    # substance (a single press release is normal; feeds manipulation signals).
    promotional_cadence = (
        signals.promotional_count >= promo_threshold and signals.earnings_count == 0
    )

    flags: list[str] = []
    if promotional_cadence:
        flags.append("promotional-8k-cadence")

    return EventTape(
        cik=cik,
        events=events,
        item_counts=item_counts,
        category_counts=category_counts,
        recency_weighted=recency_weighted,
        signals=signals,
        promotional_cadence=promotional_cadence,
        flags=flags,
    )
