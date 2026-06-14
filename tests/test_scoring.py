"""Composite-scoring & ranking tests."""

import pytest

from pennytune.presets import PRESETS
from pennytune.scoring import (
    PENALTY_MODULES,
    POSITIVE_KEYS,
    Gates,
    Penalty,
    PositiveSubScores,
    ScoreBreakdown,
    ScoreInputs,
    percentile_to_subscore,
    rank_candidates,
    score_candidate,
)

_UNIT_WEIGHTS = {key: 1.0 for key in POSITIVE_KEYS}
_UNIT_MAGS = {
    "dilution": 1.0,
    "manipulation": 1.0,
    "delisting": 1.0,
    "halt_suspension": 1.0,
    "insider_selling": 1.0,
    "distress": 1.0,
    "beneish": 1.0,
}
_PENNY = PRESETS["penny"].risk_weights
_BROAD = PRESETS["broad"].risk_weights


def _score(
    inputs: ScoreInputs, *, bundle: dict[str, float] | None = None
) -> ScoreBreakdown:
    return score_candidate(
        inputs,
        positive_weights=_UNIT_WEIGHTS,
        penalty_magnitudes=_UNIT_MAGS,
        preset_bundle=bundle or {},
    )


def test_positive_subscore_aggregation() -> None:
    b = _score(
        ScoreInputs("AAA", positives=PositiveSubScores(valuation=1.0, growth=0.5))
    )
    assert b.positive_contributions["valuation"] == pytest.approx(1.0)
    assert b.positive_contributions["growth"] == pytest.approx(0.5)
    assert b.composite == pytest.approx(1.5)


def test_penalty_scaled_by_severity_and_confidence() -> None:
    b = score_candidate(
        ScoreInputs(
            "AAA", penalties={"dilution": Penalty(severity=0.5, confidence=0.5)}
        ),
        positive_weights={},
        penalty_magnitudes={"dilution": 2.0},
        preset_bundle={"dilution": 1.0},
    )
    assert b.penalty_contributions["dilution"] == pytest.approx(0.5)  # 2.0*1.0*0.5*0.5
    assert b.composite == pytest.approx(-0.5)


def test_hard_gate_excludes_even_a_great_score() -> None:
    great = _score(
        ScoreInputs(
            "GREAT",
            positives=PositiveSubScores(1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            gates=Gates(active_suspension=True),
        )
    )
    ok = _score(ScoreInputs("OK", positives=PositiveSubScores(valuation=0.5)))
    assert great.gated is True
    assert "active SEC trading suspension" in great.gate_reasons
    result = rank_candidates([great, ok])
    assert [b.ticker for b in result.ranked] == [
        "OK"
    ]  # GREAT excluded despite higher composite
    assert [b.ticker for b in result.high_risk] == ["GREAT"]
    assert great in result.full  # still in the exported full set


def test_distress_downgrades_but_does_not_exclude() -> None:
    b = score_candidate(
        ScoreInputs(
            "DIS",
            positives=PositiveSubScores(valuation=1.0),
            penalties={"distress": Penalty(1.0)},
        ),
        positive_weights=_UNIT_WEIGHTS,
        penalty_magnitudes=_UNIT_MAGS,
        preset_bundle={},
    )
    assert b.gated is False  # signal, not a gate
    assert b.penalty_contributions["distress"] == pytest.approx(1.0)
    assert rank_candidates([b]).ranked == [b]


def test_short_interest_is_context_never_adds_to_score() -> None:
    assert "short_interest" not in PENALTY_MODULES
    assert "short_interest_ftd" not in PENALTY_MODULES
    assert "short_interest" not in POSITIVE_KEYS
    # Even if mistakenly passed, an unrecognized module is ignored.
    b = score_candidate(
        ScoreInputs("SI", penalties={"short_interest_ftd": Penalty(1.0)}),
        positive_weights={},
        penalty_magnitudes={},
        preset_bundle={},
    )
    assert b.composite == pytest.approx(0.0)
    assert "short_interest_ftd" not in b.penalty_contributions


def test_preset_aware_penny_native_penalty_weighting() -> None:
    dilution = ScoreInputs("D", penalties={"dilution": Penalty(1.0)})
    penny = score_candidate(
        dilution,
        positive_weights={},
        penalty_magnitudes=_UNIT_MAGS,
        preset_bundle=_PENNY,
    )
    broad = score_candidate(
        dilution,
        positive_weights={},
        penalty_magnitudes=_UNIT_MAGS,
        preset_bundle=_BROAD,
    )
    assert penny.penalty_contributions["dilution"] == pytest.approx(
        1.0
    )  # full weight under penny
    assert broad.penalty_contributions["dilution"] == pytest.approx(
        0.1
    )  # de-emphasized under broad
    assert (
        penny.penalty_contributions["dilution"]
        > broad.penalty_contributions["dilution"]
    )


def test_preset_aware_up_market_dormant_under_penny() -> None:
    goodwill = ScoreInputs("G", penalties={"goodwill_impairment": Penalty(1.0)})
    penny = score_candidate(
        goodwill,
        positive_weights={},
        penalty_magnitudes=_UNIT_MAGS,
        preset_bundle=_PENNY,
    )
    broad = score_candidate(
        goodwill,
        positive_weights={},
        penalty_magnitudes=_UNIT_MAGS,
        preset_bundle=_BROAD,
    )
    # Dormant under penny → shown as n/a, NEVER a silent pass.
    assert "goodwill_impairment" in penny.na_modules
    assert "goodwill_impairment" not in penny.penalty_contributions
    # Weighted in under broad.
    assert broad.penalty_contributions["goodwill_impairment"] == pytest.approx(1.0)


def test_valuation_scored_from_percentile_not_absolute() -> None:
    assert percentile_to_subscore(0.1, higher_is_better=False) == pytest.approx(
        0.9
    )  # cheap
    assert percentile_to_subscore(0.8, higher_is_better=True) == pytest.approx(0.8)
    assert percentile_to_subscore(1.5, higher_is_better=True) == 1.0  # clamped


def test_top_n_slicing_with_full_export() -> None:
    breakdowns = [
        _score(ScoreInputs(f"T{i}", positives=PositiveSubScores(valuation=i / 10)))
        for i in range(5)
    ]
    result = rank_candidates(breakdowns, top_n=2)
    assert len(result.top) == 2
    assert len(result.full) == 5  # full set always available regardless of --top
    assert result.top[0].ticker == "T4"  # highest valuation ranks first


def test_per_sector_ranking() -> None:
    breakdowns = [
        _score(
            ScoreInputs(
                "A", sic_sector="tech", positives=PositiveSubScores(valuation=0.9)
            )
        ),
        _score(
            ScoreInputs(
                "B", sic_sector="tech", positives=PositiveSubScores(valuation=0.5)
            )
        ),
        _score(
            ScoreInputs(
                "C", sic_sector="bio", positives=PositiveSubScores(valuation=0.7)
            )
        ),
    ]
    result = rank_candidates(breakdowns)
    assert result.sector_ranks["A"] == (1, 2)
    assert result.sector_ranks["B"] == (2, 2)
    assert result.sector_ranks["C"] == (1, 1)


def test_reproducible_given_same_inputs_and_weights() -> None:
    inputs = ScoreInputs(
        "R",
        positives=PositiveSubScores(valuation=0.7),
        penalties={"dilution": Penalty(0.5)},
    )
    kwargs = {
        "positive_weights": {key: 1.2 for key in POSITIVE_KEYS},
        "penalty_magnitudes": {"dilution": 1.5},
        "preset_bundle": _PENNY,
    }
    first = score_candidate(inputs, **kwargs)
    second = score_candidate(inputs, **kwargs)
    assert first.composite == second.composite
    assert first.positive_contributions == second.positive_contributions
    assert first.penalty_contributions == second.penalty_contributions
