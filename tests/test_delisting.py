"""Delisting-risk tests. EDGAR notices only - no price-day counting."""

from pennytune.features.delisting import (
    DAY_COUNT_CAVEAT,
    DelistingInputs,
    compute_delisting,
)
from pennytune.features.events import build_event, build_event_tape


def test_deficiency_notice_from_8k_item_301() -> None:
    tape = build_event_tape([build_event("a", "2026-04-30", "8-K", "3.01")])
    profile = compute_delisting(
        DelistingInputs(
            event_tape=tape,
            disclosed_timeline="180-day cure period, day 145",
            current_price=0.55,
        )
    )
    assert "DELISTING-DEFICIENCY" in profile.flags
    assert profile.tier == "deficiency"
    assert any("day 145" in e for e in profile.evidence)
    # Day-count is never computed.
    assert any("day-count" in n.lower() for n in profile.notes)


def test_sub_10_cent_price_is_extreme_risk_imminent() -> None:
    profile = compute_delisting(DelistingInputs(current_price=0.07))
    assert profile.extreme_risk is True
    assert "PRICE-SUB-10C" in profile.flags
    assert profile.tier == "imminent"
    assert any("Modified Low-Price" in n for n in profile.notes)
    assert profile.hard_exclude is False  # extreme, but not a disclosed determination


def test_reverse_split_secondary_deficiency_is_determination() -> None:
    profile = compute_delisting(
        DelistingInputs(
            current_price=0.55, reverse_split_within_year=True, deficiency_notice=True
        )
    )
    assert "REVERSE-SPLIT-SECONDARY-DEFICIENCY" in profile.flags
    assert profile.tier == "determination"
    assert profile.hard_exclude is True


def test_disclosed_determination_hard_excludes() -> None:
    profile = compute_delisting(DelistingInputs(determination_disclosed=True))
    assert profile.tier == "determination"
    assert profile.hard_exclude is True
    assert "DELISTING-DETERMINATION" in profile.flags


def test_sub_dollar_price_is_watch() -> None:
    profile = compute_delisting(DelistingInputs(current_price=0.50))
    assert "PRICE-SUB-1" in profile.flags
    assert profile.tier == "watch"


def test_clean_name_no_delisting_risk() -> None:
    profile = compute_delisting(DelistingInputs(current_price=2.50))
    assert profile.tier == "none"
    assert profile.hard_exclude is False
    assert DAY_COUNT_CAVEAT in profile.notes
