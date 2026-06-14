"""Data-freshness / as-of stamping (cross-cutting).

Every scan/inspect header reports, per data domain, *how fresh* the underlying
data actually is - and is honest about the one place "today" has a lag. Lags
are labeled in plain English (13F institutional holdings are quarterly and
lagged).

There is **no price history**: the only price the tool uses is a current
snapshot (for the universe and market cap), labeled as such - the header never
implies OHLCV history or that tradeability was assessed.
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
    "PRICE_LABEL",
    "filings_news",
    "financials",
    "current_price",
    "universe",
    "institutional_13f",
]

THIRTEENF_LAG_LABEL = (
    "13F institutional holdings are quarterly and lagged (~45 days after quarter-end)."
)
PRICE_LABEL = (
    "current price only, ~15-min delayed; used for the universe and market cap "
    "— no price history (price/technical analysis is out of scope)."
)


class FreshnessClass(StrEnum):
    """How fresh a data domain is, qualitatively."""

    LIVE = "live"  # filings/news - same-day / near-real-time
    LATEST_FILED = "latest_filed"  # financials - newest 10-K/10-Q the issuer filed
    DELAYED_SNAPSHOT = "delayed_snapshot"  # current price - ~15-min delayed, no history
    FETCH_TIME = "fetch_time"  # universe - stamped with the fetch time
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


def current_price(
    now: datetime | None = None, *, from_cache: bool = False
) -> DomainFreshness:
    return DomainFreshness(
        "current price",
        _now_str(now),
        FreshnessClass.DELAYED_SNAPSHOT,
        PRICE_LABEL,
        from_cache,
    )


def universe(
    now: datetime | None = None, *, from_cache: bool = False
) -> DomainFreshness:
    return DomainFreshness(
        "universe",
        _now_str(now),
        FreshnessClass.FETCH_TIME,
        "SEC listed-company file",
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
