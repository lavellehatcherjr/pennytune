"""Universe construction & filtering.

The candidate universe is the set of SEC-registered, NYSE/NASDAQ-listed U.S.
companies (**never OTC**), sourced solely from the SEC public-domain
``company_tickers_exchange.json`` file (ticker -> CIK -> exchange). The exchange
field enforces the never-OTC rule directly; the optional ``--exchange`` flag
narrows to NYSE or NASDAQ.

The tool fetches **no live prices**: there is no price, market-cap, or
volume-based filtering at the universe stage. A scan ranks the listed universe
by filing-derived quality / forensic signals, and ``inspect`` analyses a ticker
the user already has. Any current-price-dependent metric (market cap, EV
ratios) is therefore suppressed downstream, never imputed.

Parsing is schema-tolerant and treats responses as untrusted, per the security
requirements.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pennytune import freshness as fresh
from pennytune.cache import Cache, CachePolicy, OfflineCacheMissError
from pennytune.config import Filters
from pennytune.freshness import FreshnessReport
from pennytune.providers.base import ProviderError

__all__ = [
    "UniverseCandidate",
    "EdgarListing",
    "UniverseResult",
    "UNIVERSE_NOTE",
    "LISTED_EXCHANGES",
    "is_listed_exchange",
    "exchange_bucket",
    "passes_exchange",
    "parse_sec_universe",
    "parse_edgar_exchange_map",
    "build_candidate_set",
    "build_universe",
    "SEC_UNIVERSE_URL",
]

UNIVERSE_NOTE = (
    "universe = SEC-registered NYSE/NASDAQ-listed companies (never OTC); "
    "no current-price filtering - rank by filing quality, or inspect a ticker."
)

# NYSE/NASDAQ-listed venues only; anything else (OTC/Pink/Expert/blank) is
# excluded by construction (the never-OTC rule).
LISTED_EXCHANGES = frozenset({"NASDAQ", "NYSE", "NYSE AMERICAN", "NYSE ARCA", "AMEX"})

# SEC public-domain ticker -> CIK -> exchange file: the sole universe source.
SEC_UNIVERSE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
_UNIVERSE_TTL_SECONDS = 7 * 86_400  # the listed-company map changes slowly


@dataclass
class UniverseCandidate:
    """One listed-company candidate from the SEC universe file."""

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


@dataclass
class UniverseResult:
    """The listed candidate set plus provenance for honest output."""

    candidates: list[UniverseCandidate]
    preset: str
    counts: dict[str, int]
    from_cache: bool = False
    notes: list[str] = field(default_factory=lambda: [UNIVERSE_NOTE])


# ---- SEC universe parsing (untrusted input) ---------------------------------


def _columns(payload: dict[str, Any]) -> tuple[list[str], list[Any]]:
    return list(payload.get("fields") or []), list(payload.get("data") or [])


def parse_sec_universe(payload: dict[str, Any]) -> list[UniverseCandidate]:
    """Parse SEC ``company_tickers_exchange.json`` into listed candidates.

    Fields are ``[cik, name, ticker, exchange]``. Only NYSE/NASDAQ-listed
    venues are kept (the never-OTC rule, enforced directly from the SEC exchange
    field); rows with no usable ticker or a non-listed/OTC venue are dropped.
    """
    fields, data = _columns(payload)
    try:
        cik_i = fields.index("cik")
        tic_i = fields.index("ticker")
        exch_i = fields.index("exchange")
    except ValueError:
        return []
    name_i = fields.index("name") if "name" in fields else None
    out: list[UniverseCandidate] = []
    for row in data:
        try:
            ticker = str(row[tic_i]).strip().upper()
            if not ticker:
                continue
            exchange = str(row[exch_i]) if row[exch_i] else None
            if not is_listed_exchange(exchange):
                continue  # never-OTC: drop OTC / non-NYSE-NASDAQ / blank venues
            cik = str(int(row[cik_i])).zfill(10)
            name = str(row[name_i]) if name_i is not None else ""
        except (IndexError, ValueError, TypeError):
            continue
        out.append(
            UniverseCandidate(ticker=ticker, name=name, cik=cik, exchange=exchange)
        )
    return out


def parse_edgar_exchange_map(payload: dict[str, Any]) -> dict[str, EdgarListing]:
    """Parse SEC ``company_tickers_exchange.json`` into a ticker->listing map.

    A reusable ticker -> (CIK, exchange) lookup (e.g. for per-ticker CIK
    resolution); the universe candidate set itself is built by
    :func:`parse_sec_universe`.
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


# ---- listing / never-OTC + exchange predicate -------------------------------


def is_listed_exchange(exchange: str | None) -> bool:
    """True only for NYSE/NASDAQ listed venues - never OTC, a hard rule."""
    if not exchange:
        return False
    normalized = exchange.strip().upper()
    if any(bad in normalized for bad in ("OTC", "PINK", "GREY", "GRAY", "EXPERT")):
        return False
    return normalized in LISTED_EXCHANGES


def exchange_bucket(exchange: str | None) -> str | None:
    """Map an exchange string to the ``nasdaq`` / ``nyse`` filter bucket."""
    if not exchange:
        return None
    normalized = exchange.upper()
    if "NASDAQ" in normalized:
        return "nasdaq"
    if "NYSE" in normalized or "AMEX" in normalized:
        return "nyse"
    return None


def passes_exchange(candidate: UniverseCandidate, which: str) -> bool:
    if which == "all":
        return True
    return exchange_bucket(candidate.exchange) == which


def build_candidate_set(
    universe_payload: dict[str, Any],
    filters: Filters,
    preset_name: str,
    *,
    from_cache: bool = False,
) -> UniverseResult:
    """Build the listed universe from the SEC file and apply the exchange filter."""
    listed = parse_sec_universe(universe_payload)
    survivors = [c for c in listed if passes_exchange(c, filters.exchange)]
    counts = {"listed": len(listed), "selected": len(survivors)}
    return UniverseResult(
        candidates=survivors,
        preset=preset_name,
        counts=counts,
        from_cache=from_cache,
        notes=[UNIVERSE_NOTE],
    )


# ---- orchestration: caching + cached fallback ------------------------------


def _cached_json(
    cache: Cache,
    domain: str,
    key: str,
    ttl_seconds: float,
    fetch_fn: Callable[[], dict[str, Any]],
    policy: CachePolicy,
    now: datetime | None,
    *,
    allow_stale_fallback: bool = True,
) -> tuple[dict[str, Any], bool]:
    """Fetch JSON with cache; on fetch failure fall back to stale cache.

    Returns ``(payload, from_cache)``. Raises :class:`OfflineCacheMissError`
    under ``--offline`` with nothing cached, or re-raises the provider error
    when the fetch fails and no cached copy exists.
    """
    if policy.offline:
        entry = cache.get_entry(domain, key)
        if entry is None:
            raise OfflineCacheMissError(
                f"{domain}/{key} is not cached and --offline is set"
            )
        payload: dict[str, Any] = json.loads(entry.payload)
        return payload, True

    if not policy.refresh:
        fresh_bytes = cache.get(domain, key, ttl_seconds, now=now)
        if fresh_bytes is not None:
            cached_payload: dict[str, Any] = json.loads(fresh_bytes)
            return cached_payload, True

    try:
        fetched: dict[str, Any] = fetch_fn()
        cache.put(
            domain,
            key,
            json.dumps(fetched).encode("utf-8"),
            content_type="application/json",
            fetched_at=now,
        )
        return fetched, False
    except ProviderError:
        if allow_stale_fallback:
            entry = cache.get_entry(domain, key)
            if entry is not None:
                stale_payload: dict[str, Any] = json.loads(entry.payload)
                return stale_payload, True
        raise


def build_universe(
    *,
    fetch_sec_universe: Callable[[], dict[str, Any]],
    cache: Cache,
    filters: Filters,
    preset_name: str,
    policy: CachePolicy | None = None,
    freshness: FreshnessReport | None = None,
    universe_ttl_seconds: float = _UNIVERSE_TTL_SECONDS,
    now: datetime | None = None,
) -> UniverseResult:
    """Fetch (or load from cache) the SEC universe file, filter, stamp freshness."""
    effective_policy = policy or CachePolicy()
    payload, from_cache = _cached_json(
        cache,
        "universe",
        "sec_listed_companies",
        universe_ttl_seconds,
        fetch_sec_universe,
        effective_policy,
        now,
    )
    result = build_candidate_set(payload, filters, preset_name, from_cache=from_cache)
    if freshness is not None:
        freshness.stamp(fresh.universe(now, from_cache=from_cache))
    return result
