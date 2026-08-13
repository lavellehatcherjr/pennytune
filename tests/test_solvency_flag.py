"""A grey-zone reading is a caution, not a distress finding.

The solvency penalty fired for both the distress and the grey zone but keyed
both as ``distress``, and ``distress`` is in the critical set. So a company
sitting anywhere below the safe threshold rendered as a red ``[X] distress``.

Once the XBRL derivations made Altman computable for large filers, that meant a
critical distress label on Starbucks, HP, AbbVie, Amgen, Oracle, Duke Energy,
AT&T and Lowe's. Checked against going-concern language in companies' own 10-Ks,
every genuine detection comes from the distress zone and the grey-zone names are
healthy, so the critical flag was wrong about half the time on healthy filers.

The grey penalty stays, at the same magnitude, because a small number of
going-concern filers do land in grey. Only the label and its severity change.
"""

from __future__ import annotations

from pennytune.config import Config
from pennytune.features.quant_scores import (
    DISTRESS_ZONE_MAX,
    SAFE_ZONE_MIN,
    altman_zone,
)
from pennytune.output import _flag_glyph
from pennytune.profiles import get_profile
from pennytune.scan import CRITICAL_PENALTY_MODULES, ComputedSignals, _to_score_inputs
from pennytune.scoring import score_candidate

_WEIGHTS = dict(
    positive_weights=dict(get_profile("hold").weights),
    penalty_magnitudes=dict(get_profile("hold").penalties),
    preset_bundle=Config().presets["penny"].model_dump(),
)

# Real recovered values: SBUX sits at -1.01, comfortably inside grey.
_GREY_Z = -1.01
_DISTRESS_Z = -18.38  # ASNS, a real going-concern filer


def _named(ticker: str, z: float) -> ComputedSignals:
    return ComputedSignals(ticker=ticker, altman_z=z, distress_zone=altman_zone(z))


def _score(signals: ComputedSignals):  # type: ignore[no-untyped-def]
    return score_candidate(_to_score_inputs(signals), **_WEIGHTS)


def test_the_fixtures_sit_in_the_zones_this_test_assumes() -> None:
    """Guard the premise: if the cutoffs move, this test file is meaningless."""
    assert altman_zone(_GREY_Z) == "grey", (
        f"{_GREY_Z} is not grey under cutoffs {DISTRESS_ZONE_MAX}/{SAFE_ZONE_MIN}"
    )
    assert altman_zone(_DISTRESS_Z) == "distress"


# ---- the headline ------------------------------------------------------------


def test_grey_and_distress_do_not_produce_the_same_flag() -> None:
    """A caution must be tellable from a finding."""
    grey = set(_score(_named("GREY", _GREY_Z)).penalty_contributions)
    bad = set(_score(_named("BAD", _DISTRESS_Z)).penalty_contributions)
    assert grey != bad, (
        f"grey and distress both render as {sorted(grey)}; a user cannot tell "
        "an intermediate reading from a distress finding"
    )


def test_a_grey_reading_is_not_labelled_distress() -> None:
    """The specific wrong word: Starbucks is not in distress."""
    grey = _score(_named("GREY", _GREY_Z))
    assert "distress" not in grey.penalty_contributions, (
        "a grey-zone company carries a penalty literally named 'distress': "
        f"{sorted(grey.penalty_contributions)}"
    )


def test_a_grey_reading_is_not_a_critical_finding() -> None:
    """Critical drives the red [X] glyph and the flagged-name filter."""
    grey = _score(_named("GREY", _GREY_Z))
    critical = set(grey.penalty_contributions) & CRITICAL_PENALTY_MODULES
    assert not critical, f"grey raised critical modules {sorted(critical)}"
    text, style = _flag_glyph(grey)
    assert not text.startswith("[X]"), f"grey renders as a critical row: {text!r}"
    assert style != "red", f"grey renders red: {text!r}"


# ---- what must not regress ---------------------------------------------------


def test_a_distress_reading_is_still_critical_and_still_named_distress() -> None:
    """Detection is not traded away: the distress zone keeps its finding."""
    bad = _score(_named("BAD", _DISTRESS_Z))
    assert "distress" in bad.penalty_contributions, sorted(bad.penalty_contributions)
    assert set(bad.penalty_contributions) & CRITICAL_PENALTY_MODULES
    text, style = _flag_glyph(bad)
    assert text.startswith("[X]") and style == "red", text


def test_grey_still_carries_a_visible_solvency_marker() -> None:
    """Renaming must not silently drop the signal: grey is still penalized."""
    grey = _score(_named("GREY", _GREY_Z))
    assert grey.penalty_contributions, (
        "the grey-zone penalty disappeared entirely; the signal was dropped, "
        "not relabelled"
    )


def test_grey_penalty_magnitude_is_unchanged() -> None:
    """The composite must not move: this is a labelling fix, not a rescoring."""
    grey = _score(_named("GREY", _GREY_Z))
    charged = sum(grey.penalty_contributions.values())
    assert charged == 0.7, (
        f"grey solvency charge is {charged}, expected the previous 0.7; "
        "the composite moved when it should not have"
    )


def test_solvency_penalty_is_monotonic_in_the_altman_score() -> None:
    """No company may earn more health credit and a heavier charge at once."""
    ladder = [_DISTRESS_Z, _GREY_Z, SAFE_ZONE_MIN + 1.0]
    health, charge = [], []
    for z in ladder:
        b = _score(_named("X", z))
        health.append(b.positive_contributions.get("fin_health", 0.0))
        charge.append(sum(b.penalty_contributions.values()))
    assert health == sorted(health), f"fin_health not rising with Z: {health}"
    assert charge == sorted(charge, reverse=True), (
        f"solvency charge not falling as Z rises: {charge}"
    )


def test_safe_carries_no_solvency_penalty_at_all() -> None:
    safe = _score(_named("SAFE", SAFE_ZONE_MIN + 1.0))
    assert not safe.penalty_contributions, sorted(safe.penalty_contributions)
