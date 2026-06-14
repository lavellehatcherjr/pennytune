"""Cache TTL, offline/refresh, and Parquet round-trip tests."""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from pennytune.cache import Cache, CachePolicy, OfflineCacheMissError, cached_fetch


def _open(tmp_path: Path) -> Cache:
    return Cache(tmp_path / "cache.duckdb")


def test_put_get_fresh(tmp_path: Path) -> None:
    cache = _open(tmp_path)
    cache.put("universe", "snapshot", b"data")
    assert cache.get("universe", "snapshot", ttl_seconds=3600) == b"data"
    cache.close()


def test_ttl_expiry(tmp_path: Path) -> None:
    cache = _open(tmp_path)
    stamped = datetime(2026, 6, 1, 12, 0, 0)
    cache.put("universe", "snap", b"old", fetched_at=stamped)
    now = stamped + timedelta(seconds=100)
    assert cache.get("universe", "snap", ttl_seconds=50, now=now) is None  # expired
    assert (
        cache.get("universe", "snap", ttl_seconds=200, now=now) == b"old"
    )  # still fresh
    cache.close()


def test_missing_returns_none(tmp_path: Path) -> None:
    cache = _open(tmp_path)
    assert cache.get("domain", "absent", ttl_seconds=10) is None
    cache.close()


def test_clear_by_domain_and_all(tmp_path: Path) -> None:
    cache = _open(tmp_path)
    cache.put("a", "1", b"x")
    cache.put("a", "2", b"y")
    cache.put("b", "1", b"z")
    assert cache.clear("a") == 2
    assert cache.get("a", "1", ttl_seconds=10) is None
    assert cache.get("b", "1", ttl_seconds=10) == b"z"
    assert cache.clear() == 1
    cache.close()


def test_dataframe_roundtrip(tmp_path: Path) -> None:
    cache = _open(tmp_path)
    frame = pd.DataFrame({"ticker": ["AAA", "BBB"], "price": [0.5, 0.9]})
    cache.put_dataframe("universe", "listed", frame)
    loaded = cache.get_dataframe("universe", "listed", ttl_seconds=3600)
    assert loaded is not None
    assert list(loaded["ticker"]) == ["AAA", "BBB"]
    assert list(loaded["price"]) == [0.5, 0.9]
    cache.close()


def test_offline_uses_cache_without_network(tmp_path: Path) -> None:
    cache = _open(tmp_path)
    cache.put("universe", "snap", b"cached")

    def boom() -> bytes:
        raise AssertionError("network must not be called in --offline mode")

    out = cached_fetch(
        cache,
        "universe",
        "snap",
        ttl_seconds=3600,
        fetch_fn=boom,
        policy=CachePolicy(offline=True),
    )
    assert out == b"cached"
    cache.close()


def test_offline_miss_raises(tmp_path: Path) -> None:
    cache = _open(tmp_path)

    def boom() -> bytes:
        raise AssertionError("no network")

    with pytest.raises(OfflineCacheMissError):
        cached_fetch(
            cache,
            "d",
            "absent",
            ttl_seconds=10,
            fetch_fn=boom,
            policy=CachePolicy(offline=True),
        )
    cache.close()


def test_refresh_forces_fetch(tmp_path: Path) -> None:
    cache = _open(tmp_path)
    cache.put("d", "k", b"old")
    out = cached_fetch(
        cache,
        "d",
        "k",
        ttl_seconds=3600,
        fetch_fn=lambda: b"new",
        policy=CachePolicy(refresh=True),
    )
    assert out == b"new"
    assert cache.get("d", "k", ttl_seconds=3600) == b"new"  # cache updated
    cache.close()


def test_online_fetches_when_stale(tmp_path: Path) -> None:
    cache = _open(tmp_path)
    stamped = datetime(2026, 6, 1, 12, 0, 0)
    cache.put("d", "k", b"old", fetched_at=stamped)
    now = stamped + timedelta(seconds=100)
    calls = {"n": 0}

    def fetch() -> bytes:
        calls["n"] += 1
        return b"fresh"

    out = cached_fetch(
        cache, "d", "k", ttl_seconds=50, fetch_fn=fetch, policy=CachePolicy(), now=now
    )
    assert out == b"fresh"
    assert calls["n"] == 1
    cache.close()


def test_online_uses_cache_when_fresh(tmp_path: Path) -> None:
    cache = _open(tmp_path)
    cache.put("d", "k", b"cached")

    def boom() -> bytes:
        raise AssertionError("should not fetch while cache is fresh")

    out = cached_fetch(
        cache, "d", "k", ttl_seconds=3600, fetch_fn=boom, policy=CachePolicy()
    )
    assert out == b"cached"
    cache.close()
