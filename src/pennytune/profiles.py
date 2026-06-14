"""Strategy / horizon profiles selectable with ``--profile``.

A profile is a documented starting bundle of scoring weights, penalty
magnitudes, and a news-recency window, selectable with ``--profile``. Profiles
change *emphasis* for an investing style; they never disable the hard safety
gates (active SEC suspension, active halt, the most severe disclosed delisting
tier) or the structural manipulation flags, and there is no tradeability/spread
gate anywhere (the tool has no price data).

"Momentum" everywhere means **fundamental** momentum - a rising Piotroski
F-Score and accelerating revenue - never price/chart momentum.

Profiles are pure data (no config/pydantic dependency) so they can be imported
without cycles. The default profile is ``hold``, chosen because it aligns with
the tool's no-price, fundamentals-first strengths.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "Profile",
    "PROFILES",
    "DEFAULT_PROFILE",
    "WEIGHT_KEYS",
    "PENALTY_KEYS",
    "HIGH_RETURN_GUARDRAILS",
    "get_profile",
]

DEFAULT_PROFILE = "hold"

#: Positive-contributor weight keys (positive scoring sub-scores).
WEIGHT_KEYS: tuple[str, ...] = (
    "valuation",
    "growth",
    "fundamental_momentum",
    "sentiment",
    "insider",
    "fin_health",
)

#: Penalty-overlay magnitude keys (negative scoring contributors).
PENALTY_KEYS: tuple[str, ...] = (
    "dilution",
    "manipulation",
    "delisting",
    "halt_suspension",
    "insider_selling",
    "distress",
    "beneish",
)

#: Mandatory honesty guardrails shown when the ``high-return`` profile is active.
#: The third item is deliberate: "double your money" framing is the exact
#: language pump-and-dumps use, so this profile leans hardest on fraud filters
#: rather than implying a predicted double.
HIGH_RETURN_GUARDRAILS: tuple[str, ...] = (
    "No tool predicts which sub-$1 stock doubles; this profile improves the "
    "odds and removes death-traps — it does not promise a double on any name.",
    "The strategy assumes a diversified basket and disciplined position sizing "
    "(a few multibaggers paying for the many that don't), not single-name "
    "betting. Finding names is ~30% of the outcome; sizing is the other ~70%.",
    "'High return' / 'double your money' is classic pump-and-dump marketing "
    "language, so this profile leans hardest on the fraud, dilution, and "
    "manipulation filters.",
)


@dataclass(frozen=True)
class Profile:
    """A named bundle of scoring weights, penalties, and recency settings."""

    name: str
    description: str
    weights: dict[str, float]
    penalties: dict[str, float]
    recency_days: int
    guardrails: tuple[str, ...] = field(default=())


PROFILES: dict[str, Profile] = {
    # Short-term, catalyst- & news-aware. With no price/technical data this
    # leans on fresh catalysts/news (sentiment) rather than price momentum.
    "trader": Profile(
        name="trader",
        description=(
            "Short-term, catalyst- and news-aware (no price/technical data; "
            "emphasizes fresh catalysts, not price momentum)."
        ),
        weights={
            "valuation": 1.0,
            "growth": 1.2,
            "fundamental_momentum": 1.0,
            "sentiment": 1.4,
            "insider": 1.1,
            "fin_health": 0.9,
        },
        penalties={
            "dilution": 1.0,
            "manipulation": 1.2,
            "delisting": 1.0,
            "halt_suspension": 1.0,
            "insider_selling": 1.0,
            "distress": 1.0,
            "beneish": 1.0,
        },
        recency_days=14,
    ),
    # Buy-and-hold value & survival (months to ~2 years). The DEFAULT profile:
    # valuation/growth/fin-health/runway weighted up; dilution and delisting
    # penalties made severe; recency widened to quarters.
    "hold": Profile(
        name="hold",
        description="Buy-and-hold value & survival (months to ~2 years).",
        weights={
            "valuation": 1.4,
            "growth": 1.2,
            "fundamental_momentum": 1.2,
            "sentiment": 0.8,
            "insider": 1.1,
            "fin_health": 1.3,
        },
        penalties={
            "dilution": 1.6,
            "manipulation": 1.3,
            "delisting": 1.6,
            "halt_suspension": 1.0,
            "insider_selling": 1.2,
            "distress": 1.4,
            "beneish": 1.2,
        },
        recency_days=270,
    ),
    # Asymmetric-upside hunt (sub-$1 acceptable, hold < ~2 years). Upside
    # drivers weighted up hard; survival/fraud penalties kept severe; carries
    # the mandatory honesty guardrails.
    "high-return": Profile(
        name="high-return",
        description=(
            "Asymmetric-upside hunt (sub-$1 acceptable, hold < ~2 years); "
            "survival- and fraud-gated."
        ),
        weights={
            "valuation": 1.5,
            "growth": 1.5,
            "fundamental_momentum": 1.2,
            "sentiment": 1.1,
            "insider": 1.2,
            "fin_health": 1.1,
        },
        penalties={
            "dilution": 1.6,
            "manipulation": 1.5,
            "delisting": 1.6,
            "halt_suspension": 1.0,
            "insider_selling": 1.3,
            "distress": 1.5,
            "beneish": 1.5,
        },
        recency_days=60,
        guardrails=HIGH_RETURN_GUARDRAILS,
    ),
    # User-defined weights from config; neutral baseline here.
    "custom": Profile(
        name="custom",
        description="User-defined weights from config.",
        weights={key: 1.0 for key in WEIGHT_KEYS},
        penalties={key: 1.0 for key in PENALTY_KEYS},
        recency_days=90,
    ),
}


def get_profile(name: str) -> Profile:
    """Return the named profile, or raise ``KeyError`` with the valid choices."""
    try:
        return PROFILES[name]
    except KeyError:
        raise KeyError(
            f"Unknown profile: {name!r}; choose from {sorted(PROFILES)}"
        ) from None
