"""Dilution & corporate-action risk. The core differentiator.

Detection of the single most common way penny-stock investors get quietly
destroyed: the company issuing new shares. This module distinguishes dilution
*capacity* (they can dilute - shelves) from *execution* (they are diluting -
ATM/424B5 takedowns, rising share counts), and surfaces the related corporate
actions (reverse splits, toxic financing, restatements, shell structures).

Architecture (as in the fundamentals and 8-K event engines): the analytical
detections are **pure functions** over structured inputs - a submissions-derived
filing list, a companyfacts share-count series, cover-page facts, the 8-K event
tape, and optional full-text snippets - so they are fully fixture-testable with
no network. ``build_filing_refs`` / ``share_count_series`` / ``parse_efts_hits``
parse the EDGAR submissions, companyfacts, and efts full-text payloads
(schema-tolerant, untrusted, per the security requirements);
:class:`EdgarDilutionProvider` is the fetch boundary. Reverse splits are
detected from **share-count history**, never price (no price history).
Unparseable inputs degrade to partial/low-confidence flags, never a false
negative.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from pennytune.features.events import EventTape
from pennytune.providers.base import ProviderError
from pennytune.providers.http import SafeHttpClient

__all__ = [
    "FilingRef",
    "ShareCountPoint",
    "CoverPageFacts",
    "ShelfInfo",
    "OfferingActivity",
    "Utilization",
    "ToxicFinancing",
    "DilutionVelocity",
    "AuthorizedHeadroom",
    "Overhang",
    "ReverseSplitEvent",
    "ReverseSplits",
    "AuditorFlags",
    "NTLateFiling",
    "ShellComposite",
    "DilutionInputs",
    "DilutionProfile",
    "DilutionEvidence",
    "TOXIC_PATTERNS",
    "SHELF_FORMS",
    "PROSPECTUS_FORMS",
    "NT_FORMS",
    "detect_shelves",
    "detect_offering_activity",
    "shelf_utilization",
    "detect_toxic_financing",
    "dilution_velocity",
    "authorized_headroom",
    "fully_diluted_overhang",
    "detect_reverse_splits",
    "auditor_flags",
    "detect_nt_late_filing",
    "shell_composite",
    "compute_dilution",
    "build_filing_refs",
    "parse_submissions_sic",
    "share_count_series",
    "parse_efts_hits",
    "EdgarDilutionProvider",
]

SHELF_FORMS = frozenset(
    {"S-3", "S-3/A", "S-3ASR", "S-1", "S-1/A", "F-3", "F-3/A", "F-1"}
)
PROSPECTUS_FORMS = frozenset({"424B3", "424B5", "424B4", "424B2"})
NT_FORMS = frozenset({"NT 10-K", "NT 10-Q", "NT 10-K/A", "NT 10-Q/A", "NT 20-F"})
SHARE_TAGS: tuple[tuple[str, str], ...] = (
    ("us-gaap", "CommonStockSharesOutstanding"),
    ("dei", "EntityCommonStockSharesOutstanding"),
    ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
)
# Death-spiral / toxic-financing language.
TOXIC_PATTERNS = (
    "beneficial ownership limitation",
    "variable rate",
    "floating conversion",
    "floorless",
    "death spiral",
    "convertible note",
    "convertible promissory note",
    "warrant coverage",
    "reset provision",
    "most favored nation",
)
_DEATH_SPIRAL_QOQ = 0.20  # 20%+/quarter share growth
_ATM_THRESHOLD = 2  # repeated 424B3 within window = active ATM drip


# ---- input structures -------------------------------------------------------


@dataclass
class FilingRef:
    """A filing reference; ``offering_amount``/``text`` filled where parseable."""

    form: str
    filing_date: str
    accession: str
    offering_amount: float | None = None
    text: str = ""


@dataclass
class ShareCountPoint:
    period_end: str
    shares: float


@dataclass
class CoverPageFacts:
    authorized_shares: float | None = None
    filer_status: str | None = None
    auditor_name: str | None = None
    auditor_firm_id: str | None = None
    is_shell: bool | None = None
    employees: int | None = None


# ---- per-analysis result structures -----------------------------------------


@dataclass
class ShelfInfo:
    present: bool = False
    count: int = 0
    max_amount: float | None = None
    pct_of_market_cap: float | None = None
    wksi_routine: bool = False


@dataclass
class OfferingActivity:
    b3_count: int = 0
    b5_count: int = 0
    active_atm: bool = False


@dataclass
class Utilization:
    shelf_amount: float | None = None
    drawn: float | None = None
    remaining: float | None = None
    pct_drawn: float | None = None


@dataclass
class ToxicFinancing:
    present: bool = False
    terms: list[str] = field(default_factory=list)


@dataclass
class DilutionVelocity:
    qoq: float | None = None
    yoy: float | None = None
    trend: str | None = None  # "accelerating" | "decelerating"
    death_spiral: bool = False
    low_confidence: bool = False


@dataclass
class AuthorizedHeadroom:
    authorized: float | None = None
    outstanding: float | None = None
    headroom_pct: float | None = None
    near_ceiling: bool = False
    authorized_increase_event: bool = False


@dataclass
class Overhang:
    fully_diluted: float | None = None
    overhang_pct: float | None = None
    partial: bool = False


@dataclass
class ReverseSplitEvent:
    period_end: str
    ratio: float


@dataclass
class ReverseSplits:
    count: int = 0
    serial: bool = False
    events: list[ReverseSplitEvent] = field(default_factory=list)
    since_year: str | None = None
    cumulative_ratio: float | None = None


@dataclass
class AuditorFlags:
    auditor_name: str | None = None
    auditor_change: bool = False
    restatement: bool = False
    repeated_auditor_changes: bool = False


@dataclass
class NTLateFiling:
    present: bool = False
    count: int = 0
    escalated: bool = False


@dataclass
class ShellComposite:
    is_shell_arc: bool = False
    signal_count: int = 0
    reasons: list[str] = field(default_factory=list)


@dataclass
class DilutionInputs:
    filings: list[FilingRef] = field(default_factory=list)
    share_series: list[ShareCountPoint] = field(default_factory=list)
    cover: CoverPageFacts = field(default_factory=CoverPageFacts)
    event_tape: EventTape | None = None
    market_cap: float | None = None
    float_shares: float | None = None
    revenue: float | None = None
    warrants: float | None = None
    options: float | None = None
    convertibles: float | None = None
    remaining_shelf_shares: float | None = None
    shelf_amount: float | None = None
    takedown_amounts: list[float] = field(default_factory=list)
    financing_texts: list[str] = field(default_factory=list)
    insider_buying: bool = False
    now: datetime | None = None


@dataclass
class DilutionProfile:
    shelf: ShelfInfo
    offerings: OfferingActivity
    utilization: Utilization
    toxic: ToxicFinancing
    velocity: DilutionVelocity
    headroom: AuthorizedHeadroom
    overhang: Overhang
    splits: ReverseSplits
    auditor: AuditorFlags
    nt: NTLateFiling
    shell: ShellComposite
    score: int = 0
    severity: str = "none"
    flags: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    insider_buying_offset: bool = False


@dataclass
class DilutionEvidence:
    """The dilution slice of the per-ticker evidence assembled from live EDGAR.

    Carries the ``DilutionInputs`` the scorer consumes plus the issuer SIC
    (which only the submissions endpoint provides). ``inputs`` is ``None`` only
    when nothing usable could be assembled; ``completeness`` records any
    parser-level gaps (suppress-not-impute).
    """

    inputs: DilutionInputs | None = None
    sic_code: int | None = None
    sic_sector: str = ""
    completeness: list[str] = field(default_factory=list)


# ---- helpers ----------------------------------------------------------------


def _norm_form(form: str) -> str:
    return form.strip().upper()


def _age_days(filing_date: str, now: datetime) -> int | None:
    try:
        return (now.date() - date.fromisoformat(filing_date)).days
    except ValueError:
        return None


def _within(filing_date: str, now: datetime | None, window_days: int) -> bool:
    if now is None:
        return True
    age = _age_days(filing_date, now)
    return age is None or age <= window_days


def detect_shelves(
    filings: Sequence[FilingRef], market_cap: float | None = None
) -> ShelfInfo:
    shelves = [f for f in filings if _norm_form(f.form) in SHELF_FORMS]
    if not shelves:
        return ShelfInfo()
    amounts = [f.offering_amount for f in shelves if f.offering_amount is not None]
    max_amount = max(amounts) if amounts else None
    pct = (max_amount / market_cap * 100.0) if (max_amount and market_cap) else None
    wksi = any(
        _norm_form(f.form) == "S-3ASR" for f in shelves
    )  # routine for large filers
    return ShelfInfo(
        present=True,
        count=len(shelves),
        max_amount=max_amount,
        pct_of_market_cap=pct,
        wksi_routine=wksi,
    )


def detect_offering_activity(
    filings: Sequence[FilingRef], *, now: datetime | None = None, window_days: int = 60
) -> OfferingActivity:
    b3 = [f for f in filings if _norm_form(f.form) == "424B3"]
    b5 = [f for f in filings if _norm_form(f.form) == "424B5"]
    recent_b3 = [f for f in b3 if _within(f.filing_date, now, window_days)]
    return OfferingActivity(
        b3_count=len(b3), b5_count=len(b5), active_atm=len(recent_b3) >= _ATM_THRESHOLD
    )


def shelf_utilization(
    shelf_amount: float | None, takedown_amounts: Sequence[float]
) -> Utilization:
    if shelf_amount is None:
        return Utilization()
    drawn = float(sum(takedown_amounts))
    remaining = shelf_amount - drawn
    pct = (drawn / shelf_amount * 100.0) if shelf_amount else None
    return Utilization(
        shelf_amount=shelf_amount, drawn=drawn, remaining=remaining, pct_drawn=pct
    )


def detect_toxic_financing(texts: Iterable[str]) -> ToxicFinancing:
    blob = " ".join(texts).lower()
    hits = [pattern for pattern in TOXIC_PATTERNS if pattern in blob]
    return ToxicFinancing(present=bool(hits), terms=hits)


def _one_year_before(
    series: Sequence[ShareCountPoint], latest_end: str
) -> ShareCountPoint | None:
    try:
        anchor = date.fromisoformat(latest_end)
        target = anchor.replace(year=anchor.year - 1)
    except ValueError:
        return None
    best: ShareCountPoint | None = None
    best_diff: int | None = None
    for point in series:
        try:
            point_date = date.fromisoformat(point.period_end)
        except ValueError:
            continue
        diff = abs((point_date - target).days)
        if best_diff is None or diff < best_diff:
            best, best_diff = point, diff
    return best if (best_diff is not None and best_diff <= 45) else None


def dilution_velocity(series: Sequence[ShareCountPoint]) -> DilutionVelocity:
    ordered = sorted(series, key=lambda p: p.period_end)
    if len(ordered) < 2:
        return DilutionVelocity(low_confidence=True)
    latest, prev = ordered[-1], ordered[-2]
    qoq = (latest.shares - prev.shares) / prev.shares if prev.shares > 0 else None
    year_ago = _one_year_before(ordered, latest.period_end)
    yoy = (
        (latest.shares - year_ago.shares) / year_ago.shares
        if (year_ago and year_ago.shares > 0)
        else None
    )
    trend: str | None = None
    if len(ordered) >= 3 and ordered[-3].shares > 0 and qoq is not None:
        prior_qoq = (prev.shares - ordered[-3].shares) / ordered[-3].shares
        trend = "accelerating" if qoq > prior_qoq else "decelerating"
    death_spiral = qoq is not None and qoq >= _DEATH_SPIRAL_QOQ
    return DilutionVelocity(qoq=qoq, yoy=yoy, trend=trend, death_spiral=death_spiral)


def authorized_headroom(
    authorized: float | None,
    outstanding: float | None,
    event_tape: EventTape | None = None,
) -> AuthorizedHeadroom:
    headroom_pct: float | None = None
    near_ceiling = False
    if authorized and outstanding is not None and authorized > 0:
        headroom_pct = (authorized - outstanding) / authorized * 100.0
        near_ceiling = (outstanding / authorized) >= 0.90
    # An 8-K 5.03 (charter amendment) or 5.07 (shareholder vote) signals intent
    # to raise the authorized count.
    increase_event = False
    if event_tape is not None:
        increase_event = (
            event_tape.item_counts.get("5.03", 0) > 0
            or event_tape.item_counts.get("5.07", 0) > 0
        )
    return AuthorizedHeadroom(
        authorized=authorized,
        outstanding=outstanding,
        headroom_pct=headroom_pct,
        near_ceiling=near_ceiling,
        authorized_increase_event=increase_event,
    )


def fully_diluted_overhang(
    basic: float | None,
    *,
    warrants: float | None = None,
    options: float | None = None,
    convertibles: float | None = None,
    remaining_shelf_shares: float | None = None,
    float_shares: float | None = None,
) -> Overhang:
    if basic is None:
        return Overhang(partial=True)
    components = (warrants, options, convertibles, remaining_shelf_shares)
    additional = sum(c for c in components if c is not None)
    partial = any(c is None for c in components)
    base = float_shares if float_shares is not None else basic
    overhang_pct = (additional / base * 100.0) if base else None
    return Overhang(
        fully_diluted=basic + additional, overhang_pct=overhang_pct, partial=partial
    )


def detect_reverse_splits(
    series: Sequence[ShareCountPoint], *, min_ratio: float = 1.8
) -> ReverseSplits:
    ordered = sorted(series, key=lambda p: p.period_end)
    events: list[ReverseSplitEvent] = []
    for prev, cur in zip(ordered, ordered[1:], strict=False):
        if prev.shares > 0 and cur.shares > 0 and prev.shares / cur.shares >= min_ratio:
            events.append(
                ReverseSplitEvent(
                    period_end=cur.period_end, ratio=prev.shares / cur.shares
                )
            )
    cumulative: float | None = None
    for event in events:
        cumulative = event.ratio if cumulative is None else cumulative * event.ratio
    return ReverseSplits(
        count=len(events),
        serial=len(events) >= 2,
        events=events,
        since_year=events[0].period_end[:4] if events else None,
        cumulative_ratio=cumulative,
    )


def auditor_flags(
    cover: CoverPageFacts, event_tape: EventTape | None = None
) -> AuditorFlags:
    change_count = event_tape.item_counts.get("4.01", 0) if event_tape else 0
    restatement = (event_tape.item_counts.get("4.02", 0) > 0) if event_tape else False
    return AuditorFlags(
        auditor_name=cover.auditor_name,
        auditor_change=change_count > 0,
        restatement=restatement,
        repeated_auditor_changes=change_count >= 2,
    )


def detect_nt_late_filing(filings: Sequence[FilingRef]) -> NTLateFiling:
    nts = [
        f
        for f in filings
        if _norm_form(f.form) in NT_FORMS or "12B-25" in _norm_form(f.form)
    ]
    escalated = any(
        any(
            term in f.text.lower()
            for term in ("restatement", "going concern", "substantial doubt")
        )
        for f in nts
    )
    return NTLateFiling(present=bool(nts), count=len(nts), escalated=escalated)


def shell_composite(
    cover: CoverPageFacts,
    event_tape: EventTape | None = None,
    *,
    revenue: float | None = None,
    shares: float | None = None,
) -> ShellComposite:
    reasons: list[str] = []
    if cover.is_shell:
        reasons.append("shell cover-page flag")
    if event_tape is not None and event_tape.item_counts.get("5.06", 0) > 0:
        reasons.append("8-K Item 5.06 shell-status change")
    if cover.employees is not None and cover.employees <= 5:
        reasons.append("very low employee count")
    if (
        revenue is not None
        and shares is not None
        and revenue < 100_000
        and shares > 50_000_000
    ):
        reasons.append("minimal revenue vs large share count")
    return ShellComposite(
        is_shell_arc=len(reasons) >= 2, signal_count=len(reasons), reasons=reasons
    )


def _severity(score: int) -> str:
    if score >= 40:
        return "high"
    if score >= 15:
        return "medium"
    return "low" if score > 0 else "none"


def compute_dilution(inputs: DilutionInputs) -> DilutionProfile:
    """Run every detection, fuse into a dilution-risk sub-score + severity."""
    shelf = detect_shelves(inputs.filings, inputs.market_cap)
    offerings = detect_offering_activity(inputs.filings, now=inputs.now)
    utilization = shelf_utilization(inputs.shelf_amount, inputs.takedown_amounts)
    toxic = detect_toxic_financing(
        [f.text for f in inputs.filings] + list(inputs.financing_texts)
    )
    velocity = dilution_velocity(inputs.share_series)
    outstanding = inputs.share_series[-1].shares if inputs.share_series else None
    headroom = authorized_headroom(
        inputs.cover.authorized_shares, outstanding, inputs.event_tape
    )
    overhang = fully_diluted_overhang(
        outstanding,
        warrants=inputs.warrants,
        options=inputs.options,
        convertibles=inputs.convertibles,
        remaining_shelf_shares=inputs.remaining_shelf_shares,
        float_shares=inputs.float_shares,
    )
    splits = detect_reverse_splits(inputs.share_series)
    auditor = auditor_flags(inputs.cover, inputs.event_tape)
    nt = detect_nt_late_filing(inputs.filings)
    shell = shell_composite(
        inputs.cover, inputs.event_tape, revenue=inputs.revenue, shares=outstanding
    )

    score = 0
    flags: list[str] = []
    evidence: list[str] = []

    if shelf.present:
        if (
            shelf.pct_of_market_cap is not None
            and shelf.pct_of_market_cap > 100
            and not shelf.wksi_routine
        ):
            score += 15
            flags.append("DILUTION-SHELF-LARGE")
            amount = shelf.max_amount or 0.0
            pct = shelf.pct_of_market_cap or 0.0
            evidence.append(f"shelf ${amount:,.0f} = {pct:.0f}% of market cap")
        else:
            evidence.append(f"{shelf.count} shelf registration(s) present")
    if offerings.active_atm:
        score += 15
        flags.append("ACTIVE-ATM")
        evidence.append(f"{offerings.b3_count} 424B3 filings → active ATM drip-selling")
    if toxic.present:
        score += 20
        flags.append("TOXIC-FINANCING")
        evidence.append("toxic-financing language: " + ", ".join(toxic.terms[:3]))
    if velocity.death_spiral and velocity.qoq is not None:
        score += 20
        flags.append("DILUTION-VELOCITY-HIGH")
        evidence.append(
            f"share count +{velocity.qoq * 100:.0f}% QoQ ({velocity.trend or 'n/a'})"
        )
    if headroom.near_ceiling or headroom.authorized_increase_event:
        score += 10
        flags.append("AUTHORIZED-HEADROOM-LOW")
    if overhang.overhang_pct is not None and overhang.overhang_pct > 100:
        score += 15
        flags.append("OVERHANG-HIGH")
        evidence.append(
            f"fully-diluted overhang ~+{overhang.overhang_pct:.0f}% of float"
        )
    if splits.serial:
        score += 20
        flags.append("SERIAL-SPLITTER")
        evidence.append(f"{splits.count} reverse splits since {splits.since_year}")
    elif splits.count >= 1:
        score += 8
        flags.append("REVERSE-SPLIT")
    if nt.escalated:
        score += 15
        flags.append("NT-RESTATEMENT")
    elif nt.present:
        score += 5
        flags.append("NT-LATE")
    if shell.is_shell_arc:
        score += 15
        flags.append("SHELL-ARC")
    if auditor.restatement:
        score += 15
        flags.append("RESTATEMENT")
    if auditor.repeated_auditor_changes:
        score += 10
        flags.append("AUDITOR-CHURN")

    insider_offset = False
    if inputs.insider_buying and score > 0:
        score = max(0, score - 10)
        insider_offset = True
        evidence.append(
            "offsetting insider open-market buying noted (softens the read)"
        )

    score = min(100, score)
    return DilutionProfile(
        shelf=shelf,
        offerings=offerings,
        utilization=utilization,
        toxic=toxic,
        velocity=velocity,
        headroom=headroom,
        overhang=overhang,
        splits=splits,
        auditor=auditor,
        nt=nt,
        shell=shell,
        score=score,
        severity=_severity(score),
        flags=flags,
        evidence=evidence,
        insider_buying_offset=insider_offset,
    )


# ---- parsers (untrusted payloads) -------------------------------------------


def build_filing_refs(submissions_json: dict[str, Any]) -> list[FilingRef]:
    """Build FilingRefs for ALL filings in an EDGAR submissions payload."""
    recent = (submissions_json.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    accns = recent.get("accessionNumber") or []
    dates = recent.get("filingDate") or []
    refs: list[FilingRef] = []
    for index, form in enumerate(forms):
        refs.append(
            FilingRef(
                form=str(form),
                filing_date=str(dates[index]) if index < len(dates) else "",
                accession=str(accns[index]) if index < len(accns) else "",
            )
        )
    return refs


def parse_submissions_sic(submissions_json: dict[str, Any]) -> tuple[int | None, str]:
    """Extract ``(sic_code, sic_sector)`` from an EDGAR submissions payload.

    Submissions carry ``sic`` (a numeric string, e.g. ``"6282"``) and
    ``sicDescription`` (e.g. ``"Investment Advice"``). The description is the
    human-readable sector label used for sector-relative grouping; the numeric
    code drives the financials out-of-model check. Suppress-not-impute: a filer
    with no SIC yields ``(None, "")``.
    """
    raw_sic = submissions_json.get("sic")
    sic_code: int | None = None
    if raw_sic not in (None, ""):
        try:
            sic_code = int(str(raw_sic).strip())
        except (TypeError, ValueError):
            sic_code = None
    description = str(submissions_json.get("sicDescription") or "").strip()
    sector = description or (str(raw_sic).strip() if sic_code is not None else "")
    return sic_code, sector


def share_count_series(
    facts_json: dict[str, Any], tags: tuple[tuple[str, str], ...] = SHARE_TAGS
) -> list[ShareCountPoint]:
    """Extract a shares-outstanding time series from companyfacts (untrusted)."""
    facts = facts_json.get("facts") or {}
    for taxonomy, tag in tags:
        concept = facts.get(taxonomy, {}).get(tag)
        if not concept:
            continue
        units = concept.get("units") or {}
        rows = units.get("shares")
        if rows is None:
            rows = next((v for k, v in units.items() if k.startswith("shares")), [])
        by_end: dict[str, tuple[float, str]] = {}
        for row in rows:
            if not isinstance(row, dict) or row.get("val") is None:
                continue
            end = str(row.get("end", ""))
            filed = str(row.get("filed", ""))
            if not end:
                continue
            if end not in by_end or filed >= by_end[end][1]:
                by_end[end] = (float(row["val"]), filed)
        if by_end:
            return [
                ShareCountPoint(end, value)
                for end, (value, _) in sorted(by_end.items())
            ]
    return []


def parse_efts_hits(payload: dict[str, Any]) -> list[FilingRef]:
    """Parse an efts.sec.gov full-text-search payload into FilingRefs.

    The live ``_source`` carries ``form`` (the form), ``root_forms`` (a list),
    ``file_type`` (the *exhibit* type, e.g. ``EX-99.1`` - never the form), and
    ``adsh`` (the accession); the accession also prefixes the ``_id``. Earlier
    field guesses (``form_type``/``root_form``/``accession_no``) do not exist in
    the live payload, so the real keys are read first with safe fallbacks.
    """
    hits = ((payload.get("hits") or {}).get("hits")) or []
    refs: list[FilingRef] = []
    for hit in hits:
        source = hit.get("_source") or {}
        root_forms = source.get("root_forms")
        root_form = (
            str(root_forms[0]) if isinstance(root_forms, list) and root_forms else None
        )
        form = str(source.get("form") or root_form or source.get("file_type") or "")
        filed = str(source.get("file_date") or "")
        accession = str(
            source.get("adsh")
            or source.get("accession_no")
            or str(hit.get("_id", "")).split(":")[0]
        )
        refs.append(FilingRef(form=form, filing_date=filed, accession=accession))
    return refs


class EdgarDilutionProvider:
    """Fetch boundary for dilution analysis (submissions + efts full-text).

    The submissions/efts wire-formats are parsed schema-tolerantly (defensive
    against schema drift). The analytical core (:func:`compute_dilution`) is what
    the unit tests exercise.
    """

    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    EFTS_URL = "https://efts.sec.gov/LATEST/search-index"

    # Best-effort toxic-financing probe: the ownership-cap boilerplate nearly
    # every toxic convertible/warrant deal carries, scoped to financing forms so
    # benign ownership disclosures (13D/G) do not trip it.
    TOXIC_EFTS_PHRASE = "beneficial ownership limitation"
    TOXIC_EFTS_FORMS = "424B5,424B3,424B4,8-K,S-1,S-3"

    def __init__(self, client: SafeHttpClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "edgar"

    def fetch_submissions(self, cik: str) -> dict[str, Any]:
        url = self.SUBMISSIONS_URL.format(cik=str(cik).zfill(10))
        payload: dict[str, Any] = self._client.get_json(url, provider="edgar")
        return payload

    def full_text_search(
        self, query: str, *, forms: str | None = None, ciks: str | None = None
    ) -> dict[str, Any]:
        params = {"q": query}
        if forms:
            params["forms"] = forms
        if ciks:  # scope to one issuer so the hit-count is company-specific
            params["ciks"] = str(ciks).zfill(10)
        payload: dict[str, Any] = self._client.get_json(
            self.EFTS_URL, provider="edgar", params=params
        )
        return payload

    def get_dilution_evidence(
        self,
        cik: str,
        *,
        companyfacts: dict[str, Any],
        submissions: dict[str, Any] | None,
        revenue: float | None = None,
        now: datetime | None = None,
        event_tape: EventTape | None = None,
    ) -> DilutionEvidence:
        """Assemble live dilution evidence + issuer SIC for one CIK.

        Reuses the already-fetched ``companyfacts`` (share-count series) and the
        already-fetched ``submissions`` (filing list + SIC) - no index requests
        of its own - and runs a single best-effort EFTS toxic-language probe.
        The optional ``event_tape`` (built upstream from the same submissions)
        un-gates the 8-K-driven detections - auditor change (4.01), restatement
        (4.02), charter/shell (5.03/5.06/5.07) - which stay suppressed when it is
        ``None``. Each slice degrades independently: ``submissions is None`` (the
        fetch failed upstream) or an EFTS failure suppresses just that slice and
        is flagged, while the companyfacts-derived share series (velocity,
        reverse splits) still computes - suppress-not-impute.
        """
        completeness: list[str] = []
        share_series = share_count_series(companyfacts)

        filings: list[FilingRef] = []
        sic_code: int | None = None
        sic_sector = ""
        if submissions is None:
            completeness.append(
                "dilution filings + SIC degraded (submissions unavailable)"
            )
        else:
            filings = build_filing_refs(submissions)
            sic_code, sic_sector = parse_submissions_sic(submissions)
            if sic_code is None:
                completeness.append("SIC suppressed (submissions carry no SIC)")

        financing_texts: list[str] = []
        try:
            hits = self.full_text_search(
                self.TOXIC_EFTS_PHRASE,
                forms=self.TOXIC_EFTS_FORMS,
                ciks=cik,
            )
            if parse_efts_hits(hits):
                financing_texts.append(self.TOXIC_EFTS_PHRASE)
        except ProviderError as exc:
            completeness.append(f"toxic-financing scan degraded (EFTS: {exc})")

        inputs = DilutionInputs(
            filings=filings,
            share_series=share_series,
            revenue=revenue,
            financing_texts=financing_texts,
            event_tape=event_tape,
            now=now,
        )
        return DilutionEvidence(
            inputs=inputs,
            sic_code=sic_code,
            sic_sector=sic_sector,
            completeness=completeness,
        )
