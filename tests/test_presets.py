"""Universe-preset tests. A preset is now a per-tier risk-weight bundle only."""

import pytest

from pennytune.presets import (
    DEFAULT_PRESET,
    PENNY_NATIVE_MODULES,
    PRESETS,
    RISK_MODULE_KEYS,
    UP_MARKET_MODULES,
    get_preset,
)


def test_default_preset_is_penny() -> None:
    assert DEFAULT_PRESET == "penny"


def test_all_presets_present() -> None:
    assert set(PRESETS) == {"penny", "micro", "small-cap-value", "broad", "custom"}


def test_presets_carry_no_price_or_size_band() -> None:
    # Presets no longer filter by price/cap/EV; they only tune risk weights.
    for preset in PRESETS.values():
        for banned in ("price_min", "price_max", "cap_min", "cap_max", "ev_min"):
            assert not hasattr(preset, banned)


def test_bundle_keys_consistent() -> None:
    for preset in PRESETS.values():
        assert set(preset.risk_weights) == set(RISK_MODULE_KEYS)


def test_penny_bundle_penny_native_full_up_market_off() -> None:
    penny = PRESETS["penny"]
    assert all(penny.risk_weights[m] == 1.0 for m in PENNY_NATIVE_MODULES)
    assert all(penny.risk_weights[m] == 0.0 for m in UP_MARKET_MODULES)


def test_broad_bundle_up_market_in_penny_native_minimized() -> None:
    broad = PRESETS["broad"]
    # Up-market weighted in; penny-native minimized but NOT zero (never a false
    # pass - composite scoring shows near-zero weight as "n/a").
    assert all(broad.risk_weights[m] == 1.0 for m in UP_MARKET_MODULES)
    assert all(broad.risk_weights[m] == 0.1 for m in PENNY_NATIVE_MODULES)


def test_small_cap_value_raises_piotroski() -> None:
    assert PRESETS["small-cap-value"].risk_weights["piotroski"] == 1.3


def test_micro_keeps_penny_native_heavy() -> None:
    micro = PRESETS["micro"]
    assert micro.risk_weights["dilution"] == 1.0
    assert micro.risk_weights["delisting"] == 1.0


def test_get_preset_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_preset("does-not-exist")
