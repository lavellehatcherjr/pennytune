"""SEC fails-to-deliver settlement-stress context tests."""

import io
import zipfile
from datetime import UTC, datetime
from typing import Any

from pennytune.features.short_interest import (
    FTD_LONG_OR_SHORT_CAVEAT,
    EdgarFtdProvider,
    _recent_ftd_periods,
    ftd_settlement_stress,
    parse_sec_ftd,
)
from pennytune.providers.base import ProviderError

NOW = datetime(2026, 6, 13, tzinfo=UTC)
_REAL_HEADER = "SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE"

FTD_FILE = (
    "SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE\n"
    "20260515|123456789|TBLT|150000|TOUGHBUILT INC|0.45\n"
    "20260530|123456789|TBLT|200000|TOUGHBUILT INC|0.40\n"
)


def test_sec_ftd_parse_and_settlement_stress() -> None:
    by_symbol = parse_sec_ftd(FTD_FILE)
    assert "TBLT" in by_symbol
    context = ftd_settlement_stress(by_symbol["TBLT"])
    assert context.present is True
    assert context.persistent is True  # two distinct settlement windows
    assert context.window_count == 2
    assert context.total_fails == 350_000
    assert context.latest_fails == 200_000
    assert "naked shorting" in context.caveat


def test_ftd_caveat_constant() -> None:
    assert "long and short sales" in FTD_LONG_OR_SHORT_CAVEAT
    assert "naked shorting" in FTD_LONG_OR_SHORT_CAVEAT


# ---- the live fetch boundary: bulk zip download + symbol filter --------------


def test_recent_ftd_periods_newest_first_from_prior_month() -> None:
    # current month is never published yet → start at the prior month, b then a
    assert _recent_ftd_periods(NOW, lookback_months=2) == [
        "202605b",
        "202605a",
        "202604b",
        "202604a",
    ]


def _zip(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("cnsfails.txt", text)
    return buf.getvalue()


class _FakeFtdClient:
    """Serves the zip for ONE period; 404 (ProviderError) for the rest."""

    def __init__(
        self, period: str | None, zip_bytes: bytes = b"", error_all: bool = False
    ) -> None:
        self._period = period
        self._zip = zip_bytes
        self._error_all = error_all
        self.requested: list[str] = []

    def get_bytes(self, url: str, **kwargs: Any) -> bytes:
        self.requested.append(url)
        if self._error_all:
            raise ProviderError("HTTP 503")
        if self._period and self._period in url:
            return self._zip
        raise ProviderError("HTTP 404")


_OCGN_FILE = (
    _REAL_HEADER + "\n"
    "20260501|67577C105|OCGN|498|OCUGEN INC COM|1.73\n"
    "20260504|67577C105|OCGN|1200|OCUGEN INC COM|1.70\n"
)


def test_ftd_provider_real_shape_searches_newest_first_and_parses() -> None:
    # 202605b not yet published (404) → falls back to 202605a (the real latest)
    client = _FakeFtdClient("202605a", _zip(_OCGN_FILE))
    provider = EdgarFtdProvider(client)  # type: ignore[arg-type]
    ev = provider.get_ftd_evidence("OCGN", now=NOW)
    assert ev.period == "202605a"
    assert ev.ftd is not None and ev.ftd.present is True
    assert ev.ftd.window_count == 2 and ev.ftd.total_fails == 1698.0
    assert any("202605b" in u for u in client.requested)  # tried newer first
    assert any("202605a" in u for u in client.requested)


def test_ftd_provider_no_records_is_clean_not_degraded() -> None:
    client = _FakeFtdClient("202605a", _zip(_OCGN_FILE))
    provider = EdgarFtdProvider(client)  # type: ignore[arg-type]
    ev = provider.get_ftd_evidence("GROW", now=NOW)  # not in the file
    assert ev.ftd is not None and ev.ftd.present is False  # checked, no fails
    assert ev.completeness == []  # clean is NOT a degraded flag


def test_ftd_provider_is_context_only_never_a_penalty() -> None:
    # The provider returns an FtdContext (surfaced as context); it never gates or
    # scores — there is no penalty/severity field to inflate.
    client = _FakeFtdClient("202605a", _zip(_OCGN_FILE))
    ev = EdgarFtdProvider(client).get_ftd_evidence("OCGN", now=NOW)  # type: ignore[arg-type]
    assert not hasattr(ev.ftd, "severity") and not hasattr(ev.ftd, "score")


def test_ftd_provider_unreachable_file_is_degraded() -> None:
    client = _FakeFtdClient(None, error_all=True)
    provider = EdgarFtdProvider(client)  # type: ignore[arg-type]
    ev = provider.get_ftd_evidence("ANY", now=NOW)
    assert ev.ftd is None
    assert any("could not check" in note for note in ev.completeness)


def test_ftd_provider_fetches_the_file_once() -> None:
    client = _FakeFtdClient("202605a", _zip(_OCGN_FILE))
    provider = EdgarFtdProvider(client)  # type: ignore[arg-type]
    provider.get_ftd_evidence("OCGN", now=NOW)
    after_first = len(client.requested)
    provider.get_ftd_evidence("GROW", now=NOW)  # second ticker → no new download
    assert len(client.requested) == after_first
