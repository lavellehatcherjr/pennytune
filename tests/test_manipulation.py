"""Structural manipulation-susceptibility tests. No price data."""

from pennytune.features.manipulation import (
    ManipulationInputs,
    compute_manipulation,
    float_tier,
)


def test_float_tiers() -> None:
    assert float_tier(8_000_000) == "material"
    assert float_tier(15_000_000) == "notorious"
    assert float_tier(40_000_000) == "caution"
    assert float_tier(80_000_000) is None
    assert float_tier(None) is None


def test_low_float_toxic_promotional_raises_subflags() -> None:
    profile = compute_manipulation(
        ManipulationInputs(
            float_shares=6_000_000,
            toxic_financing=True,
            promotional_8k_cadence=True,
            serial_splitter=True,
            has_registrations=True,
            revenue=0,
        )
    )
    assert "LOW-FLOAT" in profile.flags
    assert "TOXIC-FINANCING" in profile.flags
    assert "PROMOTIONAL-FILING-PATTERN" in profile.flags
    assert "SERIAL-SPLITTER" in profile.flags
    assert "NO-FUNDAMENTAL-BASIS" in profile.flags
    assert profile.severity == "high"
    # Must explicitly state price-action was not evaluated.
    assert any("price-action not evaluated" in note for note in profile.notes)


def test_float_low_confidence_marked() -> None:
    profile = compute_manipulation(
        ManipulationInputs(float_shares=6_000_000, float_low_confidence=True)
    )
    assert "LOW-FLOAT" in profile.low_confidence_flags


def test_catalyst_offsets_no_fundamental_basis() -> None:
    profile = compute_manipulation(
        ManipulationInputs(has_registrations=True, revenue=0, has_catalyst=True)
    )
    assert "NO-FUNDAMENTAL-BASIS" not in profile.flags


def test_clean_name_low_severity_but_keeps_note() -> None:
    profile = compute_manipulation(
        ManipulationInputs(float_shares=120_000_000, revenue=50_000_000)
    )
    assert profile.severity == "none"
    assert profile.flags == []
    assert any("price-action not evaluated" in note for note in profile.notes)
