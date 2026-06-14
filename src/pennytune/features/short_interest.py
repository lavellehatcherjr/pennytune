"""Settlement-stress CONTEXT from SEC fails-to-deliver (lagged, never timing).

A lagged-but-public *context* signal — never a timing signal. Fails-to-deliver
(FTD) are published by the SEC twice-monthly and are structurally stale, so
they are kept only as settlement-stress context corroborating a thesis, never
as a score input or a timing trigger.

The parser is SCHEMA-TOLERANT (header-alias matching) because the SEC FTD
layout varies. FTDs are lagged → labeled via the freshness layer. By design
this module emits **no** short interest, **no** days-to-cover, and **no**
squeeze field: those were cut as precise-looking noise.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pennytune.providers.base import ProviderError
from pennytune.providers.http import SafeHttpClient

__all__ = [
    "FTD_LONG_OR_SHORT_CAVEAT",
    "FtdRecord",
    "FtdContext",
    "FtdEvidence",
    "parse_sec_ftd",
    "ftd_settlement_stress",
    "EdgarFtdProvider",
]

FTD_LONG_OR_SHORT_CAVEAT = (
    "Fails-to-deliver arise from both long and short sales and are NOT by "
    "themselves evidence of naked shorting (per the SEC)."
)

_FTD_DATE_ALIASES = ("settlement date", "settlementdate", "date")
_FTD_SYMBOL_ALIASES = ("symbol", "ticker")
_FTD_QUANTITY_ALIASES = ("quantity (fails)", "quantity", "fails", "qty", "total fails")
_FTD_CUSIP_ALIASES = ("cusip",)
_FTD_PRICE_ALIASES = ("price",)
_FTD_ISSUER_ALIASES = ("description", "issuer name", "issuer", "company name")


@dataclass
class FtdRecord:
    settlement_date: str
    cusip: str
    symbol: str
    quantity: float
    issuer: str = ""
    price: float | None = None


@dataclass
class FtdContext:
    present: bool = False
    persistent: bool = False
    window_count: int = 0
    total_fails: float = 0.0
    latest_fails: float = 0.0
    caveat: str = FTD_LONG_OR_SHORT_CAVEAT


def _num(cell: str) -> float | None:
    text = cell.strip().replace(",", "").replace("$", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _index(header: Sequence[str], aliases: tuple[str, ...]) -> int | None:
    normalized = [col.strip().lower() for col in header]
    for position, name in enumerate(normalized):
        if name in aliases:
            return position
    return None


def parse_sec_ftd(text: str, *, delimiter: str = "|") -> dict[str, list[FtdRecord]]:
    """Parse the SEC fails-to-deliver pipe-delimited file (schema-tolerant)."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return {}
    header = lines[0].split(delimiter)
    sym_i = _index(header, _FTD_SYMBOL_ALIASES)
    qty_i = _index(header, _FTD_QUANTITY_ALIASES)
    if sym_i is None or qty_i is None:
        return {}
    date_i = _index(header, _FTD_DATE_ALIASES)
    cusip_i = _index(header, _FTD_CUSIP_ALIASES)
    price_i = _index(header, _FTD_PRICE_ALIASES)
    issuer_i = _index(header, _FTD_ISSUER_ALIASES)

    out: dict[str, list[FtdRecord]] = {}
    for line in lines[1:]:
        cells = line.split(delimiter)
        if sym_i >= len(cells) or qty_i >= len(cells):
            continue
        symbol = cells[sym_i].strip().upper()
        quantity = _num(cells[qty_i])
        if not symbol or quantity is None:
            continue

        def cell(idx: int | None) -> str:
            return cells[idx].strip() if (idx is not None and idx < len(cells)) else ""

        record = FtdRecord(
            settlement_date=cell(date_i),
            cusip=cell(cusip_i),
            symbol=symbol,
            quantity=quantity,
            issuer=cell(issuer_i),
            price=_num(cell(price_i)) if price_i is not None else None,
        )
        out.setdefault(symbol, []).append(record)
    return out


def ftd_settlement_stress(
    records: Sequence[FtdRecord], *, min_windows: int = 2
) -> FtdContext:
    """Persistent/elevated FTD context (settlement stress), with the SEC caveat."""
    if not records:
        return FtdContext()
    distinct_dates = {r.settlement_date for r in records if r.settlement_date}
    latest = max(records, key=lambda r: r.settlement_date)
    return FtdContext(
        present=True,
        persistent=len(distinct_dates) >= min_windows,
        window_count=len(distinct_dates),
        total_fails=sum(r.quantity for r in records),
        latest_fails=latest.quantity,
    )


# ---- fetch boundary: the bi-monthly SEC fails-to-deliver bulk file -----------
#
# The SEC publishes FTDs as a zipped, pipe-delimited file per half-month
# (cnsfails{YYYYMM}{a|b}.zip) covering ALL securities, keyed by symbol. One file
# is fetched per scan and cached, then filtered locally per ticker — there is no
# per-ticker endpoint. The data lags ~2 weeks, so it is settlement-stress
# context, never a timing signal.

_FTD_URL = "https://www.sec.gov/files/data/fails-deliver-data/cnsfails{}.zip"
_MAX_UNZIPPED_BYTES = 200_000_000  # defensive cap (the real file is ~3.5 MB)


@dataclass
class FtdEvidence:
    """The fails-to-deliver slice of the per-ticker evidence (context, never scored).

    ``ftd`` is a graded :class:`FtdContext` when the file was checked (a clean
    ``present=False`` for a name with no fails — *not* a degraded result), or
    ``None`` with a completeness flag when no FTD file could be fetched.
    """

    ftd: FtdContext | None = None
    period: str = ""  # the half-month file used (e.g. "202605a") — lag honesty
    completeness: list[str] = field(default_factory=list)


def _recent_ftd_periods(now: datetime, *, lookback_months: int = 4) -> list[str]:
    """Half-month FTD periods (``YYYYMMa``/``b``), newest-first, from last month.

    The current month is never published yet, so start at the prior month; each
    month yields the second half (``b``) then the first (``a``).
    """
    periods: list[str] = []
    year, month = now.year, now.month
    for _ in range(lookback_months):
        month -= 1
        if month == 0:
            month, year = 12, year - 1
        periods.append(f"{year}{month:02d}b")
        periods.append(f"{year}{month:02d}a")
    return periods


def _unzip_first_member(raw: bytes) -> str:
    """Decompress the single member of the FTD zip to text (bounded)."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name = archive.namelist()[0]
        if archive.getinfo(name).file_size > _MAX_UNZIPPED_BYTES:
            raise ValueError("FTD file exceeds the decompression cap")
        return archive.read(name).decode("utf-8", "replace")


class EdgarFtdProvider:
    """Fetches the most recent SEC fails-to-deliver file once and filters it.

    The bulk half-month file is downloaded and parsed a single time (cached), so
    a whole scan costs one file; each ticker is matched by symbol and graded by
    the unchanged :func:`ftd_settlement_stress`. FTD is settlement-stress
    context only — never a gate or a score input.
    """

    BASE_URL = _FTD_URL

    def __init__(self, client: SafeHttpClient) -> None:
        self._client = client
        self._records: dict[str, list[FtdRecord]] | None = None
        self._period = ""
        self._loaded = False

    def _load(self, now: datetime) -> dict[str, list[FtdRecord]] | None:
        if not self._loaded:
            self._loaded = True
            for period in _recent_ftd_periods(now):
                try:
                    raw = self._client.get_bytes(
                        self.BASE_URL.format(period), provider="edgar"
                    )
                except ProviderError:
                    continue  # not published yet / unavailable → try the prior half
                try:
                    self._records = parse_sec_ftd(_unzip_first_member(raw))
                except (zipfile.BadZipFile, OSError, ValueError):
                    continue
                self._period = period
                break
        return self._records

    def get_ftd_evidence(
        self, ticker: str, *, now: datetime | None = None
    ) -> FtdEvidence:
        """Grade ``ticker`` against the latest FTD file (matched by symbol)."""
        records = self._load(now or datetime.now(UTC))
        if records is None:  # no file could be fetched/parsed
            return FtdEvidence(
                completeness=["SEC fails-to-deliver file unavailable (could not check)"]
            )
        context = ftd_settlement_stress(records.get(ticker.upper(), []))
        return FtdEvidence(ftd=context, period=self._period)
