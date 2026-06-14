"""Universe-construction tests. The universe is the SEC listed-company file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pennytune.cache import Cache, CachePolicy, OfflineCacheMissError
from pennytune.config import Filters
from pennytune.features.universe import (
    build_candidate_set,
    build_universe,
    exchange_bucket,
    is_listed_exchange,
    parse_edgar_exchange_map,
    parse_sec_universe,
    passes_exchange,
)
from pennytune.freshness import FreshnessReport
from pennytune.providers.base import ProviderError

# SEC company_tickers_exchange.json shape: fields + row arrays.
SEC_UNIVERSE: dict[str, Any] = {
    "fields": ["cik", "name", "ticker", "exchange"],
    "data": [
        [111, "Penny Co", "PENY", "Nasdaq"],
        [222, "Mid Co", "MIDC", "NYSE"],
        [333, "Amex Co", "AMXC", "NYSE American"],
        [444, "OTC Co", "OTCX", "OTC"],  # dropped: never-OTC
        [555, "Blank Co", "BLNK", None],  # dropped: no listed venue
        [666, "Big Co", "BIGB", "Nasdaq"],
    ],
}


def _filters(exchange: str = "all") -> Filters:
    return Filters(exchange=exchange)  # type: ignore[arg-type]


def test_parse_sec_universe_keeps_listed_only() -> None:
    candidates = parse_sec_universe(SEC_UNIVERSE)
    tickers = {c.ticker for c in candidates}
    assert tickers == {"PENY", "MIDC", "AMXC", "BIGB"}  # OTCX + BLNK dropped
    peny = next(c for c in candidates if c.ticker == "PENY")
    assert peny.cik == "0000000111"  # 10-digit zero-padded
    assert peny.name == "Penny Co"
    assert peny.exchange == "Nasdaq"


def test_parse_sec_universe_empty_on_bad_schema() -> None:
    assert parse_sec_universe({"fields": ["x"], "data": [[1]]}) == []
    assert parse_sec_universe({}) == []


def test_parse_edgar_exchange_map_is_a_lookup_including_otc() -> None:
    mapping = parse_edgar_exchange_map(SEC_UNIVERSE)
    assert mapping["PENY"].cik == "0000000111"
    assert mapping["OTCX"].exchange == "OTC"  # the lookup map keeps OTC names


def test_is_listed_exchange_never_otc() -> None:
    assert is_listed_exchange("Nasdaq")
    assert is_listed_exchange("NYSE American")
    assert not is_listed_exchange("OTC")
    assert not is_listed_exchange("OTC Pink")
    assert not is_listed_exchange(None)
    assert not is_listed_exchange("")


def test_exchange_bucket() -> None:
    assert exchange_bucket("Nasdaq") == "nasdaq"
    assert exchange_bucket("NYSE") == "nyse"
    assert exchange_bucket("NYSE American") == "nyse"
    assert exchange_bucket("OTC") is None


def test_build_candidate_set_never_otc_and_counts() -> None:
    result = build_candidate_set(SEC_UNIVERSE, _filters(), "penny")
    assert {c.ticker for c in result.candidates} == {"PENY", "MIDC", "AMXC", "BIGB"}
    assert "OTCX" not in {c.ticker for c in result.candidates}
    assert result.counts["listed"] == 4
    assert result.counts["selected"] == 4
    assert result.preset == "penny"


def test_exchange_filter_nasdaq_only() -> None:
    result = build_candidate_set(SEC_UNIVERSE, _filters("nasdaq"), "penny")
    assert {c.ticker for c in result.candidates} == {"PENY", "BIGB"}  # NYSE excluded


def test_exchange_filter_nyse_only() -> None:
    result = build_candidate_set(SEC_UNIVERSE, _filters("nyse"), "penny")
    assert {c.ticker for c in result.candidates} == {"MIDC", "AMXC"}


def test_passes_exchange_predicate() -> None:
    candidates = parse_sec_universe(SEC_UNIVERSE)
    peny = next(c for c in candidates if c.ticker == "PENY")
    assert passes_exchange(peny, "all")
    assert passes_exchange(peny, "nasdaq")
    assert not passes_exchange(peny, "nyse")


# ---- build_universe orchestration (cache + fallback) -------------------------


def _cache(tmp_path: Path) -> Cache:
    return Cache(db_path=tmp_path / "c.duckdb")


def test_build_universe_fetches_and_filters(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    freshness = FreshnessReport()
    result = build_universe(
        fetch_sec_universe=lambda: SEC_UNIVERSE,
        cache=cache,
        filters=_filters("nasdaq"),
        preset_name="penny",
        freshness=freshness,
    )
    assert {c.ticker for c in result.candidates} == {"PENY", "BIGB"}
    assert not result.from_cache
    assert freshness.get("universe") is not None  # stamped
    cache.close()


def test_build_universe_cached_fallback_on_fetch_failure(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    # Warm the cache, then a later failing fetch should fall back to it.
    build_universe(
        fetch_sec_universe=lambda: SEC_UNIVERSE,
        cache=cache,
        filters=_filters(),
        preset_name="penny",
    )

    def _boom() -> dict[str, Any]:
        raise ProviderError("SEC down")

    result = build_universe(
        fetch_sec_universe=_boom,
        cache=cache,
        filters=_filters(),
        preset_name="penny",
        policy=CachePolicy(refresh=True),  # force a fetch attempt
    )
    assert result.from_cache  # served stale from cache, never blocked
    assert result.candidates
    cache.close()


def test_build_universe_offline_without_cache_raises(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    with pytest.raises(OfflineCacheMissError):
        build_universe(
            fetch_sec_universe=lambda: SEC_UNIVERSE,
            cache=cache,
            filters=_filters(),
            preset_name="penny",
            policy=CachePolicy(offline=True),
        )
    cache.close()
