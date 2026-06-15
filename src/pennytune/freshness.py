"""Data-freshness / as-of stamping (cross-cutting).

Every scan/inspect header reports, per data domain, *how fresh* the underlying
data actually is - and is honest about the one place "today" has a lag. Lags
are labeled in plain English (13F institutional holdings are quarterly and
lagged).

The tool fetches no live prices and no price history; freshness covers the
filing-derived domains only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

__all__ = [
    "FreshnessClass",
    "DomainFreshness",
    "FreshnessReport",
    "THIRTEENF_LAG_LABEL",
    "filings_news",
    "financials",
    "institutional_13f",
]

THIRTEENF_LAG_LABEL = (
    "13F institutional holdings are quarterly and lagged (~45 days after quarter-end)."
)


class FreshnessClass(StrEnum):
    """How fresh a data domain is, qualitatively."""

    LIVE = "live"  # filings/news - same-day / near-real-time
    LATEST_FILED = "latest_filed"  # financials - newest 10-K/10-Q the issuer filed
    LAGGED = "lagged"  # 13F institutional holdings - structurally lagged


@dataclass
class DomainFreshness:
    """As-of state for a single data domain."""

    domain: str
    as_of: str
    freshness: FreshnessClass
    label: str = ""
    from_cache: bool = False

    def render(self) -> str:
        cached = " (cached)" if self.from_cache else ""
        note = f" — {self.label}" if self.label else ""
        return f"{self.domain}: {self.as_of}{cached}{note}"


@dataclass
class FreshnessReport:
    """Collects per-domain freshness for honest display in headers."""

    domains: dict[str, DomainFreshness] = field(default_factory=dict)

    def stamp(self, item: DomainFreshness) -> DomainFreshness:
        self.domains[item.domain] = item
        return item

    def get(self, domain: str) -> DomainFreshness | None:
        return self.domains.get(domain)

    def render_lines(self) -> list[str]:
        return [self.domains[name].render() for name in self.domains]


def _now_str(now: datetime | None = None) -> str:
    moment = now if now is not None else datetime.now(UTC)
    return moment.strftime("%Y-%m-%d %H:%M UTC")


def filings_news(
    now: datetime | None = None, *, from_cache: bool = False
) -> DomainFreshness:
    return DomainFreshness(
        "filings/news",
        _now_str(now),
        FreshnessClass.LIVE,
        "EDGAR updates continuously",
        from_cache,
    )


def financials(
    period: str, filed_date: str, *, from_cache: bool = False
) -> DomainFreshness:
    return DomainFreshness(
        "financials",
        f"latest filed {period} (filed {filed_date})",
        FreshnessClass.LATEST_FILED,
        "the newest 10-K/10-Q the company has reported",
        from_cache,
    )


def institutional_13f(quarter: str, *, from_cache: bool = False) -> DomainFreshness:
    return DomainFreshness(
        "institutional (13F)",
        quarter,
        FreshnessClass.LAGGED,
        THIRTEENF_LAG_LABEL,
        from_cache,
    )
