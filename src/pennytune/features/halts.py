"""Trading-suspension risk (SEC).

A safety gate: a name that screens beautifully can be frozen — sometimes
permanently impaired — by an SEC trading suspension. The SEC can suspend a
micro-cap for up to 10 business days (routinely for promotion/fraud concerns).
An active or recent SEC suspension is a hard gate that forces exclusion and
applies a strong penalty.

Intraday exchange-halt status is intentionally NOT evaluated here (the tool
carries no live halt feed) — verify a name's current trading-halt status in
your broker. Inputs are the SEC trading-suspension list, parsed
schema-tolerantly at the fetch boundary.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime

from pennytune.providers.base import ProviderError
from pennytune.providers.http import SafeHttpClient

__all__ = [
    "Suspension",
    "HaltProfile",
    "HaltEvidence",
    "parse_sec_suspensions",
    "normalize_company",
    "compute_halt_risk",
    "EdgarSuspensionProvider",
]

_RECENT_DAYS = 180


@dataclass
class Suspension:
    symbol: str
    company: str = ""
    date: str = ""
    reason: str = ""
    release: str = ""


@dataclass
class HaltProfile:
    tier: str = "none"  # none < suspended (SEC trading suspension)
    hard_exclude: bool = False  # active/recent SEC suspension → hard gate
    flags: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


# ---- parsing the live SEC trading-suspension list (untrusted HTML) -----------
#
# The SEC trading-suspension page (www.sec.gov/litigation/suspensions) is an
# HTML table of (Date, Respondents/company, Release No.) — it carries NO ticker
# column, and dates are "Month DD, YYYY". So the live shape differs from a
# dict-rows feed: we parse the table, normalize each date to ISO (dropping any
# row whose date will not parse, so the recency gate never fires on a bad date),
# and match a candidate to a row by normalized COMPANY NAME downstream.

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}  # fmt: skip
_SUSPENSION_RE = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+"
    r"(\d{1,2}),\s+(\d{4})\s+(.{1,150}?)\s+Release No\.\s*(34-\d+)",
    re.IGNORECASE,
)
# Legal-entity suffixes stripped before a company-name match (kept conservative:
# only true entity designators, not descriptive words like "Holdings"/"Group").
_LEGAL_SUFFIXES = frozenset(
    {
        "INC",
        "INCORPORATED",
        "CORP",
        "CORPORATION",
        "CO",
        "COMPANY",
        "LTD",
        "LIMITED",
        "LLC",
        "LLP",
        "LP",
        "PLC",
        "SA",
        "NV",
        "AG",
        "AB",
    }  # fmt: skip
)


def _iso_date(month: str, day: str, year: str) -> str:
    """``("Sept", "26", "2023") → "2023-09-26"``; ``""`` if it will not parse."""
    number = _MONTHS.get(month[:3].lower())
    if number is None:
        return ""
    try:
        return date(int(year), number, int(day)).isoformat()
    except ValueError:
        return ""


def normalize_company(name: str) -> str:
    """Normalize a company name for matching (upper, drop punctuation + suffixes)."""
    tokens = re.sub(r"[^A-Za-z0-9 ]", " ", name).upper().split()
    return " ".join(t for t in tokens if t not in _LEGAL_SUFFIXES)


def parse_sec_suspensions(html: str) -> list[Suspension]:
    """Parse the SEC trading-suspension HTML list into dated Suspension rows.

    Rows with an unparseable date are dropped (suppress-not-impute) so the
    downstream recency gate is never tripped by a bad date.
    """
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    suspensions: list[Suspension] = []
    for match in _SUSPENSION_RE.finditer(text):
        month, day, year, company, release = match.groups()
        iso = _iso_date(month, day, year)
        if not iso:
            continue
        suspensions.append(
            Suspension(
                symbol="",  # the SEC list carries no ticker — matched by name
                company=company.strip().strip(",").strip(),
                date=iso,
                release=release,
            )
        )
    return suspensions


def _age_days(date_str: str, now: datetime) -> int | None:
    try:
        return (now.date() - date.fromisoformat(date_str[:10])).days
    except ValueError:
        return None


def _is_recent(date_str: str, now: datetime | None, recent_days: int) -> bool:
    if now is None:
        return True  # without a clock, treat a provided record as recent (conservative)
    age = _age_days(date_str, now)
    return age is None or 0 <= age <= recent_days


def compute_halt_risk(
    symbol: str,
    suspensions: Sequence[Suspension],
    *,
    now: datetime | None = None,
    recent_days: int = _RECENT_DAYS,
) -> HaltProfile:
    """Grade SEC trading-suspension risk; an active/recent suspension is a hard gate."""
    sym_suspensions = [s for s in suspensions if s.symbol == symbol]

    flags: list[str] = []
    evidence: list[str] = []
    recent_suspensions = [
        s for s in sym_suspensions if _is_recent(s.date, now, recent_days)
    ]
    if recent_suspensions:
        # Any current OR recent SEC suspension is near-disqualifying.
        flags.append("SEC-SUSPENSION")
        for s in recent_suspensions:
            evidence.append(
                f"SEC trading suspension {s.date} — {s.reason or 'reason n/a'}"
            )

    return HaltProfile(
        tier="suspended" if recent_suspensions else "none",
        hard_exclude=bool(recent_suspensions),
        flags=flags,
        evidence=evidence,
    )


# ---- fetch boundary: the SEC trading-suspension list -------------------------


@dataclass
class HaltEvidence:
    """The trading-suspension slice of the per-ticker evidence.

    ``halt`` is a graded :class:`HaltProfile` when the list was checked (a clean
    ``tier="none"`` for a name not on the list — *not* a degraded result), or
    ``None`` with a completeness flag when the list could not be fetched/parsed
    (the honest "could not check" case).
    """

    halt: HaltProfile | None = None
    completeness: list[str] = field(default_factory=list)


class EdgarSuspensionProvider:
    """Fetches the SEC trading-suspension list once and grades names against it.

    The list (≈one HTML page of the most recent suspensions, newest first) is
    fetched a single time and cached, so a whole scan costs one request; each
    name is matched by normalized company name (the list carries no ticker) and
    graded by the unchanged :func:`compute_halt_risk` recency logic — the gate
    fires only on an active/recent suspension, never an expired one.
    """

    SUSPENSIONS_URL = "https://www.sec.gov/litigation/suspensions"

    def __init__(self, client: SafeHttpClient) -> None:
        self._client = client
        self._suspensions: list[Suspension] | None = None
        self._loaded = False

    def _load(self) -> list[Suspension] | None:
        if not self._loaded:
            self._loaded = True
            try:
                html = self._client.get_text(self.SUSPENSIONS_URL, provider="edgar")
                self._suspensions = parse_sec_suspensions(html)
            except ProviderError:
                self._suspensions = None
        return self._suspensions

    def get_halt_evidence(
        self, ticker: str, company: str, *, now: datetime | None = None
    ) -> HaltEvidence:
        """Grade ``ticker`` against the live list (matched by company name)."""
        suspensions = self._load()
        if not suspensions:  # unreachable, or parsed empty → could not verify
            return HaltEvidence(
                completeness=["SEC suspension list unavailable (could not check)"]
            )
        symbol = ticker.upper()
        target = normalize_company(company)
        matched = [
            Suspension(
                symbol=symbol,
                company=s.company,
                date=s.date,
                reason=s.reason,
                release=s.release,
            )
            for s in suspensions
            if target and normalize_company(s.company) == target
        ]
        return HaltEvidence(halt=compute_halt_risk(symbol, matched, now=now))
