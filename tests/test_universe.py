"""Universe tests - the shared ticker->CIK lookup used by inspect/scan.

The whole-universe build pipeline was removed once scan moved to curated sets;
only the CIK-resolution lookup (``parse_edgar_exchange_map``) remains.
"""

from __future__ import annotations

from typing import Any

from pennytune.features.universe import parse_edgar_exchange_map

# SEC company_tickers_exchange.json shape: fields + row arrays.
SEC_UNIVERSE: dict[str, Any] = {
    "fields": ["cik", "name", "ticker", "exchange"],
    "data": [
        [111, "Penny Co", "PENY", "Nasdaq"],
        [444, "OTC Co", "OTCX", "OTC"],
    ],
}


def test_parse_edgar_exchange_map_is_a_lookup_including_otc() -> None:
    mapping = parse_edgar_exchange_map(SEC_UNIVERSE)
    assert mapping["PENY"].cik == "0000000111"  # 10-digit zero-padded
    assert mapping["PENY"].exchange == "Nasdaq"
    assert mapping["OTCX"].exchange == "OTC"  # the lookup map keeps OTC names
