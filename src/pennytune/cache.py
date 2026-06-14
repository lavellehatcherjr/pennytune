"""Local cache: DuckDB + Parquet with per-domain TTLs.

Cached payloads (raw bytes) and tabular datasets (Parquet) are keyed by
``(domain, key)`` with a ``fetched_at`` stamp; freshness is judged against a
per-domain TTL supplied by the caller (from ``config.CacheTTL``). The
``--offline`` (cache only) and ``--refresh`` (ignore TTLs) flags are honored via
:class:`CachePolicy` and :func:`cached_fetch`.

Timestamps are stored as naive UTC to avoid DuckDB timezone ambiguity. There is
no EOD/OHLCV price cache - the tool keeps only a short-TTL *current price*
snapshot.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

from pennytune import paths

if TYPE_CHECKING:
    import pandas as pd

__all__ = [
    "CacheEntry",
    "CachePolicy",
    "OfflineCacheMissError",
    "Cache",
    "cached_fetch",
]


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


@dataclass
class CacheEntry:
    """A single cached item with its fetch timestamp (naive UTC)."""

    domain: str
    key: str
    payload: bytes
    content_type: str
    source_url: str
    fetched_at: datetime


class OfflineCacheMissError(Exception):
    """Raised when ``--offline`` is set but the item is not cached (→ exit 4)."""


@dataclass
class CachePolicy:
    """Read/write policy derived from the ``--offline`` / ``--refresh`` flags."""

    offline: bool = False
    refresh: bool = False


class Cache:
    """DuckDB-backed cache for byte payloads and Parquet datasets."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (paths.cache_dir() / "cache.duckdb")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(self.db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache_entries ("
            "  domain VARCHAR NOT NULL,"
            "  key VARCHAR NOT NULL,"
            "  payload BLOB,"
            "  content_type VARCHAR,"
            "  source_url VARCHAR,"
            "  fetched_at TIMESTAMP NOT NULL,"
            "  PRIMARY KEY (domain, key)"
            ")"
        )

    @staticmethod
    def is_fresh(
        fetched_at: datetime, ttl_seconds: float, *, now: datetime | None = None
    ) -> bool:
        reference = _to_naive_utc(now) if now is not None else _utcnow_naive()
        age = (reference - _to_naive_utc(fetched_at)).total_seconds()
        return age < ttl_seconds

    def put(
        self,
        domain: str,
        key: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
        source_url: str = "",
        fetched_at: datetime | None = None,
    ) -> None:
        stamp = _to_naive_utc(fetched_at) if fetched_at is not None else _utcnow_naive()
        self._conn.execute(
            "DELETE FROM cache_entries WHERE domain = ? AND key = ?", [domain, key]
        )
        self._conn.execute(
            "INSERT INTO cache_entries VALUES (?, ?, ?, ?, ?, ?)",
            [domain, key, payload, content_type, source_url, stamp],
        )

    def get_entry(self, domain: str, key: str) -> CacheEntry | None:
        row = self._conn.execute(
            "SELECT domain, key, payload, content_type, source_url, fetched_at "
            "FROM cache_entries WHERE domain = ? AND key = ?",
            [domain, key],
        ).fetchone()
        if row is None:
            return None
        payload = bytes(row[2]) if row[2] is not None else b""
        return CacheEntry(
            domain=row[0],
            key=row[1],
            payload=payload,
            content_type=row[3] or "",
            source_url=row[4] or "",
            fetched_at=row[5],
        )

    def get(
        self, domain: str, key: str, ttl_seconds: float, *, now: datetime | None = None
    ) -> bytes | None:
        """Return the cached payload if present and fresh, else None."""
        entry = self.get_entry(domain, key)
        if entry is None or not self.is_fresh(entry.fetched_at, ttl_seconds, now=now):
            return None
        return entry.payload

    def put_dataframe(
        self,
        domain: str,
        key: str,
        frame: pd.DataFrame,
        *,
        fetched_at: datetime | None = None,
    ) -> Path:
        """Write a DataFrame to Parquet and record a cache entry pointing at it."""
        parquet_path = self._parquet_path(domain, key)
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(parquet_path)
        self.put(
            domain,
            key,
            b"",
            content_type="application/x-parquet",
            source_url=str(parquet_path),
            fetched_at=fetched_at,
        )
        return parquet_path

    def get_dataframe(
        self, domain: str, key: str, ttl_seconds: float, *, now: datetime | None = None
    ) -> pd.DataFrame | None:
        """Return the cached DataFrame if present and fresh, else None."""
        entry = self.get_entry(domain, key)
        if entry is None or not self.is_fresh(entry.fetched_at, ttl_seconds, now=now):
            return None
        parquet_path = self._parquet_path(domain, key)
        if not parquet_path.exists():
            return None
        import pandas as pd

        return pd.read_parquet(parquet_path)

    def clear(self, domain: str | None = None) -> int:
        """Delete cache entries (all, or just one domain). Returns count removed."""
        if domain is None:
            count = self._conn.execute("SELECT count(*) FROM cache_entries").fetchone()
            self._conn.execute("DELETE FROM cache_entries")
        else:
            count = self._conn.execute(
                "SELECT count(*) FROM cache_entries WHERE domain = ?", [domain]
            ).fetchone()
            self._conn.execute("DELETE FROM cache_entries WHERE domain = ?", [domain])
        return int(count[0]) if count is not None else 0

    def domain_counts(self) -> dict[str, int]:
        """Cached-entry counts per domain (for the ``cache status`` screen)."""
        rows = self._conn.execute(
            "SELECT domain, count(*) FROM cache_entries GROUP BY domain ORDER BY domain"
        ).fetchall()
        return {row[0]: int(row[1]) for row in rows}

    def close(self) -> None:
        self._conn.close()

    def _parquet_path(self, domain: str, key: str) -> Path:
        safe_key = "".join(ch if (ch.isalnum() or ch in "-_.") else "_" for ch in key)
        return self.db_path.parent / "parquet" / domain / f"{safe_key}.parquet"


def cached_fetch(
    cache: Cache,
    domain: str,
    key: str,
    ttl_seconds: float,
    fetch_fn: Callable[[], bytes],
    policy: CachePolicy,
    *,
    content_type: str = "application/octet-stream",
    source_url: str = "",
    now: datetime | None = None,
) -> bytes:
    """Return cached bytes if fresh; otherwise fetch, store, and return.

    ``--refresh`` skips the freshness read and forces a fetch. ``--offline``
    never calls the network: it returns the cached payload (even if stale, so
    the caller can label its age) and raises :class:`OfflineCacheMissError`
    if nothing is cached.
    """
    if not policy.refresh:
        fresh = cache.get(domain, key, ttl_seconds, now=now)
        if fresh is not None:
            return fresh

    if policy.offline:
        entry = cache.get_entry(domain, key)
        if entry is not None:
            return entry.payload
        raise OfflineCacheMissError(
            f"{domain}/{key} is not cached and --offline is set"
        )

    payload = fetch_fn()
    cache.put(
        domain,
        key,
        payload,
        content_type=content_type,
        source_url=source_url,
        fetched_at=now,
    )
    return payload
