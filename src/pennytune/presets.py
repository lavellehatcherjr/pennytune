"""Universe presets selectable with ``--preset``.

A preset selects a **per-tier risk-weighting bundle** - which risk modules
matter for a slice of the market - orthogonal to the strategy profile, which
decides *how signals are weighted for an investing style*. The two compose
(e.g. ``--preset small-cap-value --profile hold``).

A preset no longer filters the universe by price or size (the tool fetches no
prices); it only tunes the scoring weights. Penny-native modules carry full
weight under ``penny`` and are progressively de-emphasized toward ``broad``;
up-market modules are dormant under ``penny`` and weighted in under ``broad``.
A module that does not apply to the active tier is given weight 0.0 - the engine
renders that as "n/a for this preset", never as a silent pass (an honesty
mechanism). The product stays tuned for sub-$1 micro-caps: ``penny`` is the
default; it is risk-tuning context, not an automatic price filter.

Presets are pure data (no config/pydantic dependency) so they import cleanly.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "Preset",
    "PRESETS",
    "DEFAULT_PRESET",
    "PENNY_NATIVE_MODULES",
    "UP_MARKET_MODULES",
    "FORENSIC_MODULES",
    "RISK_MODULE_KEYS",
    "get_preset",
]

DEFAULT_PRESET = "penny"

#: Penny-native risk modules (heavy at the bottom of the market).
PENNY_NATIVE_MODULES: tuple[str, ...] = (
    "dilution",
    "dilution_velocity",
    "delisting",
    "manipulation_susceptibility",
    "toxic_financing",
    "serial_splitter",
    "low_float",
    "short_interest_ftd",
)

#: Up-market risk modules (weighted in toward the top of the market).
UP_MARKET_MODULES: tuple[str, ...] = (
    "goodwill_impairment",
    "multiple_compression",
    "leverage_coverage",
    "sbc_dilution",
)

#: Forensic emphasis knobs (e.g. Piotroski weight rises in value universes).
FORENSIC_MODULES: tuple[str, ...] = ("piotroski",)

#: All risk-module keys carried by a preset bundle.
RISK_MODULE_KEYS: tuple[str, ...] = (
    PENNY_NATIVE_MODULES + UP_MARKET_MODULES + FORENSIC_MODULES
)


@dataclass(frozen=True)
class Preset:
    """A named risk tier: a per-tier risk-weight bundle (no price/size band)."""

    name: str
    description: str
    risk_weights: dict[str, float]


def _bundle(penny: float, up_market: float, piotroski: float) -> dict[str, float]:
    """Build a full risk-weight bundle from per-group defaults."""
    weights = {key: penny for key in PENNY_NATIVE_MODULES}
    weights.update({key: up_market for key in UP_MARKET_MODULES})
    weights["piotroski"] = piotroski
    return weights


PRESETS: dict[str, Preset] = {
    # Default. Penny-native modules at full weight; up-market modules off.
    "penny": Preset(
        name="penny",
        description=(
            "Penny-native risk emphasis (dilution/delisting/manipulation/toxic "
            "financing at full weight); tuned for sub-$1 micro-caps."
        ),
        risk_weights=_bundle(penny=1.0, up_market=0.0, piotroski=1.0),
    ),
    # Penny modules still heavily weighted; a touch of up-market begins.
    "micro": Preset(
        name="micro",
        description="Penny-native emphasis, lightly eased; small up-market weighting.",
        risk_weights={
            **_bundle(penny=0.9, up_market=0.1, piotroski=1.1),
            "dilution": 1.0,
            "dilution_velocity": 1.0,
            "delisting": 1.0,
            "toxic_financing": 1.0,
            "serial_splitter": 1.0,
        },
    ),
    # Value-leaning: Piotroski raised; dilution/delisting de-emphasized; up-market
    # begins weighting in.
    "small-cap-value": Preset(
        name="small-cap-value",
        description=(
            "Value-leaning: Piotroski raised; penny-native de-emphasized; "
            "up-market begins weighting in."
        ),
        risk_weights={
            **_bundle(penny=0.6, up_market=0.5, piotroski=1.3),
            "low_float": 0.4,
            "short_interest_ftd": 0.4,
            "sbc_dilution": 0.4,
        },
    ),
    # Penny modules minimized (shown as n/a, never false-pass); up-market in.
    "broad": Preset(
        name="broad",
        description=(
            "Up-market risk emphasis (impairment/leverage/SBC/multiple-"
            "compression weighted in); penny-native overlays minimized."
        ),
        risk_weights=_bundle(penny=0.1, up_market=1.0, piotroski=0.7),
    ),
    # User-defined risk-weight bundle (penny-like default).
    "custom": Preset(
        name="custom",
        description="User-defined risk-weight bundle.",
        risk_weights=_bundle(penny=1.0, up_market=0.0, piotroski=1.0),
    ),
}


def get_preset(name: str) -> Preset:
    """Return the named preset, or raise ``KeyError`` with the valid choices."""
    try:
        return PRESETS[name]
    except KeyError:
        raise KeyError(
            f"Unknown preset: {name!r}; choose from {sorted(PRESETS)}"
        ) from None
