"""Universe lookup - the SEC ticker -> CIK / listing map.

The SEC public-domain ``company_tickers_exchange.json`` file (ticker -> CIK ->
exchange) is parsed into a reusable lookup used to resolve a ticker's EDGAR CIK
for ``inspect`` / ``scan``. PennyTune ranks a curated set of tickers (named
explicitly or read from the watchlist), so there is no whole-universe build
here.

Parsing is schema-tolerant and treats responses as untrusted, per the security
requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "UniverseCandidate",
    "EdgarListing",
    "UNIVERSE_NOTE",
    "parse_edgar_exchange_map",
    "SEC_UNIVERSE_URL",
]

UNIVERSE_NOTE = (
    "universe = SEC-registered NYSE/NASDAQ-listed companies (never OTC); "
    "no current-price filtering - rank by filing quality, or inspect a ticker."
)

# SEC public-domain ticker -> CIK -> exchange file: the sole universe source.
SEC_UNIVERSE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"


@dataclass
class UniverseCandidate:
    """One candidate company (a ticker to analyse)."""

    ticker: str
    name: str
    cik: str | None = None
    exchange: str | None = None
    flags: list[str] = field(default_factory=list)


@dataclass
class EdgarListing:
    """A ticker's EDGAR identity + listing venue."""

    cik: str  # 10-digit zero-padded
    exchange: str | None


# ---- SEC universe parsing (untrusted input) ---------------------------------


def _columns(payload: dict[str, Any]) -> tuple[list[str], list[Any]]:
    return list(payload.get("fields") or []), list(payload.get("data") or [])


def parse_edgar_exchange_map(payload: dict[str, Any]) -> dict[str, EdgarListing]:
    """Parse SEC ``company_tickers_exchange.json`` into a ticker->listing map.

    A reusable ticker -> (CIK, exchange) lookup for per-ticker CIK resolution.
    The map keeps every ticker (including OTC); the never-OTC rule applied only
    to the former whole-universe build, which no longer exists.
    """
    fields, data = _columns(payload)
    try:
        cik_i = fields.index("cik")
        ticker_i = fields.index("ticker")
        exch_i = fields.index("exchange")
    except ValueError:
        return {}
    out: dict[str, EdgarListing] = {}
    for row in data:
        try:
            ticker = str(row[ticker_i]).strip().upper()
            if not ticker:
                continue
            cik = str(int(row[cik_i])).zfill(10)
            raw_exchange = row[exch_i]
            exchange = str(raw_exchange) if raw_exchange else None
        except (IndexError, ValueError, TypeError):
            continue
        out[ticker] = EdgarListing(cik=cik, exchange=exchange)
    return out
