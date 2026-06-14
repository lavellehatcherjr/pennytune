"""Configuration system tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from pennytune.config import (
    default_config,
    flatten,
    get_value,
    load_config,
    redact_identity,
    save_config,
    set_value,
    validate_edgar_identity,
)


def test_default_config_is_hold_penny() -> None:
    cfg = default_config()
    assert cfg.profile == "hold"
    assert cfg.preset == "penny"
    assert cfg.weights.valuation == 1.4  # hold bundle
    assert cfg.penalties.dilution == 1.6
    assert cfg.filters.exchange == "all"  # the only universe filter
    assert cfg.risk_acknowledged is False
    assert cfg.edgar_identity is None


def test_edgar_identity_validation_accepts_minimal_and_rejects_malformed() -> None:
    # Format-only: a name token + an email-like token is enough (not "real");
    # whitespace is normalized.
    assert validate_edgar_identity("Handle x@y.com") == "Handle x@y.com"
    assert (
        validate_edgar_identity("  Dana   Lee  dana@example.com ")
        == "Dana Lee dana@example.com"
    )
    for bad in ("foo", "   ", "", "x@y.com", "Name notanemail", "Name foo@bar"):
        with pytest.raises(ValueError):
            validate_edgar_identity(bad)


def test_config_set_rejects_malformed_identity() -> None:
    cfg = default_config()
    with pytest.raises((ValueError, ValidationError)):
        set_value(cfg, "edgar_identity", "foo")
    set_value(cfg, "edgar_identity", "Handle x@y.com")  # valid -> accepted
    assert cfg.edgar_identity == "Handle x@y.com"


def test_toml_roundtrip(tmp_path: Path) -> None:
    cfg = default_config()
    set_value(cfg, "edgar_identity", "Dana Lee dana@example.com")
    set_value(cfg, "weights.growth", "1.55")
    set_value(cfg, "filters.exchange", "nasdaq")
    set_value(cfg, "preset", "broad")

    path = tmp_path / "config.toml"
    save_config(cfg, path)
    assert path.exists()

    loaded = load_config(path)
    assert loaded.edgar_identity == "Dana Lee dana@example.com"
    assert loaded.weights.growth == 1.55
    assert loaded.filters.exchange == "nasdaq"
    assert loaded.preset == "broad"
    assert loaded == cfg  # full structural equality after round-trip


def test_load_missing_returns_default(tmp_path: Path) -> None:
    assert load_config(tmp_path / "absent.toml") == default_config()


def test_set_unknown_key_raises() -> None:
    cfg = default_config()
    with pytest.raises(KeyError):
        set_value(cfg, "weights.bogus", "1.0")
    with pytest.raises(KeyError):
        set_value(cfg, "nonexistent", "x")


def test_set_out_of_range_raises() -> None:
    cfg = default_config()
    with pytest.raises(ValidationError):
        set_value(cfg, "weights.valuation", "-1")  # ge=0
    with pytest.raises(ValidationError):
        set_value(cfg, "rate_limits.edgar_rps", "20")  # le=10 (hard ceiling)


def test_set_bad_type_raises() -> None:
    cfg = default_config()
    with pytest.raises(ValueError):
        set_value(cfg, "weights.valuation", "abc")
    with pytest.raises(ValueError):
        set_value(cfg, "risk_acknowledged", "maybe")


def test_set_bool_and_int_coercion() -> None:
    cfg = default_config()
    set_value(cfg, "risk_acknowledged", "true")
    assert cfg.risk_acknowledged is True
    set_value(cfg, "cache_ttl.universe_seconds", "5000")
    assert cfg.cache_ttl.universe_seconds == 5000


def test_set_profile_resets_weights() -> None:
    cfg = default_config()
    set_value(cfg, "profile", "trader")
    assert cfg.profile == "trader"
    assert cfg.weights.sentiment == 1.4  # trader bundle
    assert cfg.penalties.manipulation == 1.2


def test_set_preset_sets_preset_only() -> None:
    cfg = default_config()
    set_value(cfg, "preset", "micro")
    assert cfg.preset == "micro"
    # A preset selects a risk-weight bundle; it carries no price/size band.
    assert not hasattr(cfg.filters, "min_price")


def test_profile_and_preset_compose_independently() -> None:
    # The two axes are orthogonal: a preset must not touch profile weights.
    cfg = default_config()
    set_value(cfg, "profile", "high-return")
    high_return_weights = cfg.weights.model_dump()

    set_value(cfg, "preset", "broad")
    assert cfg.weights.model_dump() == high_return_weights  # preset left weights alone
    assert cfg.profile == "high-return"

    set_value(cfg, "profile", "hold")
    assert cfg.preset == "broad"  # profile left the preset alone


def test_invalid_profile_or_preset_value_raises() -> None:
    cfg = default_config()
    with pytest.raises(ValueError):
        set_value(cfg, "profile", "nope")
    with pytest.raises(ValueError):
        set_value(cfg, "preset", "nope")


def test_flatten_and_get_value() -> None:
    cfg = default_config()
    flat = flatten(cfg)
    assert flat["weights.valuation"] == 1.4
    assert flat["filters.exchange"] == "all"
    assert "presets.penny.dilution" in flat
    assert get_value(cfg, "presets.penny.dilution") == 1.0
    with pytest.raises(KeyError):
        get_value(cfg, "weights.nope")


def test_set_nested_preset_bundle() -> None:
    cfg = default_config()
    set_value(cfg, "presets.broad.dilution", "0.25")
    assert cfg.presets["broad"].dilution == 0.25


def test_redact_identity() -> None:
    assert redact_identity(None) == "(not set)"
    assert redact_identity("Dana Lee dana@example.com") == "Dana Lee <d***@example.com>"
    assert redact_identity("NoEmailToken") == "NoEmailToken"
