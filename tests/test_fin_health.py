"""Financial health must discriminate, not sort into three buckets.

``fin_health`` is the dominant term in the positive half of the composite.
Deriving it from the Altman Z-double-prime *zone* gives it exactly three values
(distress / grey / safe), which costs twice over:

* extra input data cannot improve the ranking, because it piles into three
  buckets and a company at Z''=9 is indistinguishable from one at Z''=2.7;
* Altman's published 1968-era bands put Apple (Z''=2.31, high leverage but
  obviously solvent) in the same bucket as a marginal issuer.

These tests are deliberately anchor-agnostic: they pin the SHAPE of the signal
(discriminating, monotonic, suppressible, and consistent with the distress
penalty) rather than any particular cutoff, so recalibrating the anchors later
does not require rewriting them.
"""

from __future__ import annotations

from pennytune.scan import ComputedSignals, _penalties, _positive_subscores


def _signals(z: float | None, ticker: str = "T") -> ComputedSignals:
    """A signals record carrying only what fin_health and distress read."""
    from pennytune.scan import _altman_zone

    return ComputedSignals(ticker=ticker, altman_z=z, distress_zone=_altman_zone(z))


def _fin_health(z: float | None) -> float:
    return _positive_subscores(_signals(z)).fin_health


# ---- discrimination ----------------------------------------------------------


def test_fin_health_discriminates_inside_the_old_safe_band() -> None:
    """A very strong balance sheet must outscore a marginally safe one."""
    strong, marginal = _fin_health(9.0), _fin_health(2.7)
    assert strong > marginal, (
        f"Z''=9.0 and Z''=2.7 both scored {strong}: the signal is a constant "
        "above the safe cutoff"
    )


def test_fin_health_discriminates_inside_the_old_grey_band() -> None:
    """Near-safe and near-distress are not the same company."""
    near_safe, near_distress = _fin_health(2.55), _fin_health(1.15)
    assert near_safe > near_distress, (
        f"Z''=2.55 and Z''=1.15 both scored {near_safe}: the grey band is flat"
    )


def test_fin_health_discriminates_inside_the_old_distress_band() -> None:
    """A deeply insolvent balance sheet must score below a marginal one."""
    marginal, deep = _fin_health(1.0), _fin_health(-30.0)
    assert marginal > deep, (
        f"Z''=1.0 and Z''=-30.0 both scored {marginal}: distress is floored flat"
    )


def test_fin_health_takes_many_distinct_values_across_the_range() -> None:
    """The whole point: more input data must be able to move the score."""
    values = {_fin_health(z) for z in (-30, -5, 0, 0.5, 1.1, 1.8, 2.31, 2.6, 4, 9, 20)}
    assert len(values) >= 8, f"only {len(values)} distinct fin_health values: {values}"


# ---- shape -------------------------------------------------------------------


def test_fin_health_is_monotonic_in_altman_z() -> None:
    """Healthier balance sheet, never a lower score."""
    zs = [-40, -10, -2, 0, 0.5, 1.0, 1.1, 1.5, 2.0, 2.31, 2.6, 3.5, 5, 8, 15, 40]
    scores = [_fin_health(z) for z in zs]
    for (z0, s0), (z1, s1) in zip(zip(zs, scores), zip(zs[1:], scores[1:])):
        assert s1 >= s0, f"non-monotonic: Z''={z0}->{s0} but Z''={z1}->{s1}"


def test_fin_health_stays_within_the_subscore_range() -> None:
    """Positive sub-scores are normalized to [0, 1] before weighting."""
    for z in (-1e6, -40, 0, 2.31, 40, 1e6):
        assert 0.0 <= _fin_health(z) <= 1.0, f"Z''={z} produced {_fin_health(z)}"


def test_fin_health_is_suppressed_when_altman_is_not_computable() -> None:
    """The applicability gate must still yield no credit at all, not a zero.

    ``PositiveSubScores`` is all-float, so suppression shows up as the field
    never being assigned - which reads as 0.0 here. What matters is that an
    uncomputable Altman cannot earn credit.
    """
    assert _fin_health(None) == 0.0


# ---- consistency with the distress penalty -----------------------------------


def test_health_credit_and_distress_penalty_never_both_increase() -> None:
    """A company cannot earn more health credit AND more distress penalty.

    Both derive from the same number, so scoring them independently lets them
    contradict each other.
    """
    zs = [-30, -5, 0, 1.0, 1.5, 2.31, 2.6, 4.0, 9.0]
    for z0, z1 in zip(zs, zs[1:]):
        health0, health1 = _fin_health(z0), _fin_health(z1)
        pen0 = _penalties(_signals(z0)).get("distress")
        pen1 = _penalties(_signals(z1)).get("distress")
        sev0 = pen0.severity if pen0 else 0.0
        sev1 = pen1.severity if pen1 else 0.0
        assert not (health1 > health0 and sev1 > sev0), (
            f"Z''={z0}->{z1}: health {health0}->{health1} and distress "
            f"{sev0}->{sev1} both rose"
        )
