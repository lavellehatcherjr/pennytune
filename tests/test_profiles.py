"""Strategy-profile tests."""

import pytest

from pennytune.profiles import (
    DEFAULT_PROFILE,
    HIGH_RETURN_GUARDRAILS,
    PENALTY_KEYS,
    PROFILES,
    WEIGHT_KEYS,
    get_profile,
)


def test_default_profile_is_hold() -> None:
    # Hold (not trader) is the default - it aligns with the tool's no-price,
    # fundamentals-first strengths.
    assert DEFAULT_PROFILE == "hold"


def test_all_profiles_present() -> None:
    assert set(PROFILES) == {"trader", "hold", "high-return", "custom"}


def test_profile_keys_consistent() -> None:
    for profile in PROFILES.values():
        assert set(profile.weights) == set(WEIGHT_KEYS)
        assert set(profile.penalties) == set(PENALTY_KEYS)


def test_hold_weight_deltas() -> None:
    hold = PROFILES["hold"]
    assert hold.weights["valuation"] == 1.4
    assert hold.weights["fin_health"] == 1.3
    assert hold.penalties["dilution"] == 1.6
    assert hold.penalties["delisting"] == 1.6
    assert hold.recency_days == 270


def test_trader_emphasizes_fresh_news() -> None:
    trader = PROFILES["trader"]
    assert trader.weights["sentiment"] == 1.4
    assert trader.recency_days == 14


def test_high_return_guardrails_and_fraud_weighting() -> None:
    high_return = PROFILES["high-return"]
    assert high_return.guardrails == HIGH_RETURN_GUARDRAILS
    assert len(high_return.guardrails) == 3
    assert high_return.weights["growth"] == 1.5
    # Leans hardest on fraud filters.
    assert high_return.penalties["manipulation"] == 1.5
    assert high_return.penalties["beneish"] == 1.5


def test_only_high_return_has_guardrails() -> None:
    for name in ("trader", "hold", "custom"):
        assert PROFILES[name].guardrails == ()


def test_get_profile_unknown_raises() -> None:
    with pytest.raises(KeyError):
        get_profile("does-not-exist")
