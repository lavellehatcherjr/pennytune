"""Cache Parquet dataframe round-trip (the retained dataframe API)."""

from pathlib import Path

import pandas as pd

from pennytune.cache import Cache


def test_dataframe_roundtrip(tmp_path: Path) -> None:
    cache = Cache(tmp_path / "cache.duckdb")
    frame = pd.DataFrame({"ticker": ["AAA", "BBB"], "price": [0.5, 0.9]})
    cache.put_dataframe("universe", "listed", frame)
    loaded = cache.get_dataframe("universe", "listed", ttl_seconds=3600)
    assert loaded is not None
    assert list(loaded["ticker"]) == ["AAA", "BBB"]
    assert list(loaded["price"]) == [0.5, 0.9]
    cache.close()
