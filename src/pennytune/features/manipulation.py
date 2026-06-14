"""Structural manipulation *susceptibility* (filing/structure only).

Susceptibility, NOT detection. PennyTune has no price/volume data, so it cannot
see manipulation in progress - it scores the **filing- and structure-based
preconditions** that make a name susceptible to pump-and-dump: very low float,
promotional-filing cadence, toxic/variable-rate financing, the serial-splitter
arc, and registration-heavy structures with no fundamental basis. Every output
states plainly that price-action was not evaluated (no price data). This is
distinct from the accounting-fraud scores.

Inputs are simple values/flags sourced from the fundamentals module (float,
revenue), the dilution module (toxic financing, serial splitter, registrations),
the news module (catalyst), and the 8-K event engine (promotional 8-K cadence);
the assembly pipeline feeds those feature outputs in.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "LOW_FLOAT_MATERIAL",
    "LOW_FLOAT_NOTORIOUS",
    "LOW_FLOAT_CAUTION",
    "PRICE_ACTION_NOTE",
    "ManipulationInputs",
    "ManipulationProfile",
    "float_tier",
    "compute_manipulation",
]

# Float thresholds (shares), graded.
LOW_FLOAT_MATERIAL = 10_000_000  # under ~10M is a material risk factor on its own
LOW_FLOAT_NOTORIOUS = 20_000_000  # under ~20M is "notorious" for pumps
LOW_FLOAT_CAUTION = 50_000_000  # under ~50M warrants caution

PRICE_ACTION_NOTE = (
    "price-action not evaluated (no price data) — verify volume/price patterns "
    "yourself before trading."
)
_PROMO_FILING_THRESHOLD = 3  # S-1/424B cadence enabling resale
_NO_BASIS_REVENUE = 100_000  # below this, registration-heavy = no fundamental basis


@dataclass
class ManipulationInputs:
    float_shares: float | None = None
    float_low_confidence: bool = False
    promotional_filing_count: int = 0  # S-1/424B resale-enabling cadence
    promotional_8k_cadence: bool = False  # promotional 7.01/8.01 cadence
    toxic_financing: bool = False  # from the dilution module
    serial_splitter: bool = False  # from the dilution module
    revenue: float | None = None  # fundamentals (fundamental basis)
    has_registrations: bool = False  # shelf / S-1 present
    has_catalyst: bool = False  # news catalyst (offsets no-fundamental-basis)


@dataclass
class ManipulationProfile:
    score: int = 0
    severity: str = "none"
    flags: list[str] = field(default_factory=list)
    float_tier: str | None = None
    low_confidence_flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=lambda: [PRICE_ACTION_NOTE])


def float_tier(float_shares: float | None) -> str | None:
    """Grade the float into material / notorious / caution / None."""
    if float_shares is None:
        return None
    if float_shares < LOW_FLOAT_MATERIAL:
        return "material"
    if float_shares < LOW_FLOAT_NOTORIOUS:
        return "notorious"
    if float_shares < LOW_FLOAT_CAUTION:
        return "caution"
    return None


def _severity(score: int) -> str:
    if score >= 40:
        return "high"
    if score >= 15:
        return "medium"
    return "low" if score > 0 else "none"


def compute_manipulation(inputs: ManipulationInputs) -> ManipulationProfile:
    """Score structural susceptibility to manipulation (preconditions, not acts)."""
    score = 0
    flags: list[str] = []
    low_confidence: list[str] = []

    tier = float_tier(inputs.float_shares)
    if tier == "material":
        score += 25
        flags.append("LOW-FLOAT")
    elif tier == "notorious":
        score += 18
        flags.append("LOW-FLOAT")
    elif tier == "caution":
        score += 10
        flags.append("LOW-FLOAT")
    if tier is not None and inputs.float_low_confidence:
        # Float is low-confidence for micro-caps; mark float-dependent flags.
        low_confidence.append("LOW-FLOAT")

    if (
        inputs.promotional_filing_count >= _PROMO_FILING_THRESHOLD
        or inputs.promotional_8k_cadence
    ):
        score += 20
        flags.append("PROMOTIONAL-FILING-PATTERN")
    if inputs.toxic_financing:
        score += 20
        flags.append("TOXIC-FINANCING")
    if inputs.serial_splitter:
        score += 15
        flags.append("SERIAL-SPLITTER")

    no_basis = (
        inputs.has_registrations
        and (inputs.revenue is None or inputs.revenue < _NO_BASIS_REVENUE)
        and not inputs.has_catalyst  # a verifiable news catalyst offsets this
    )
    if no_basis:
        score += 15
        flags.append("NO-FUNDAMENTAL-BASIS")

    score = min(100, score)
    return ManipulationProfile(
        score=score,
        severity=_severity(score),
        flags=flags,
        float_tier=tier,
        low_confidence_flags=low_confidence,
        notes=[PRICE_ACTION_NOTE],
    )
