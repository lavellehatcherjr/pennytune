"""Delisting-risk module. EDGAR notices only, no live price-clock.

Encodes the current, citable Nasdaq rules but does NOT count consecutive
sub-threshold closes (no price history). Instead it detects the *deficiency
notice* itself (8-K Item 3.01 / going-concern / company statements), reports
where the company says it sits in the cure timeline, and uses the current price
only as context - flagging a price at/under $0.10 as extreme-risk (the
Modified Low-Price determination may be imminent) while telling the user to
verify the day-count, which the tool cannot compute.

Rules verified current as of 2026-06-12 (SEC/Nasdaq):
- $1.00 minimum bid: <$1.00 for 30 consecutive business days → deficiency →
  180-day cure, up to two periods (360 days total).
- Modified Low-Price (operative 2026-01-19): closing bid <= $0.10 for 10
  consecutive trading days → immediate Staff Delisting Determination
  (Rule 5810) + immediate suspension, no compliance period, appeal does not
  stay - applies even during a $1.00 compliance period.
- Reverse-split rule (Jan 2025): if a reverse split was effected within the
  prior year and the bid-price rule is failed, Nasdaq moves to delist;
  automatic suspension if not compliant within 360 days.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pennytune.features.events import EventTape

__all__ = [
    "NASDAQ_MIN_BID_RULE",
    "MODIFIED_LOW_PRICE_RULE",
    "REVERSE_SPLIT_RULE",
    "DAY_COUNT_CAVEAT",
    "EXTREME_LOW_PRICE",
    "MIN_BID_PRICE",
    "DelistingInputs",
    "DelistingProfile",
    "compute_delisting",
]

NASDAQ_MIN_BID_RULE = (
    "Nasdaq $1.00 minimum bid: <$1.00 for 30 consecutive business days → "
    "deficiency → 180-day cure (up to two periods = 360 days)."
)
MODIFIED_LOW_PRICE_RULE = (
    "Modified Low-Price (operative 2026-01-19): closing bid <= $0.10 for 10 "
    "consecutive trading days → immediate Staff Delisting Determination "
    "(Rule 5810) + immediate suspension; no compliance period; appeal does not stay."
)
REVERSE_SPLIT_RULE = (
    "If a reverse split was effected within the prior year and the bid-price "
    "rule is failed, Nasdaq moves to delist; automatic suspension if not "
    "compliant within 360 days (Jan 2025 rule)."
)
DAY_COUNT_CAVEAT = (
    "Consecutive-day price count NOT computed (no price history) — verify the "
    "day-count yourself."
)

EXTREME_LOW_PRICE = 0.10
MIN_BID_PRICE = 1.00

_TIER_RANK = {"none": 0, "watch": 1, "deficiency": 2, "imminent": 3, "determination": 4}


@dataclass
class DelistingInputs:
    current_price: float | None = None  # current-price context only (not a day-count)
    deficiency_notice: bool = False  # disclosed 8-K 3.01 / press release
    determination_disclosed: bool = (
        False  # disclosed Staff Delisting Determination / suspension
    )
    disclosed_timeline: str | None = None  # company's own statement of where it sits
    going_concern: bool = False  # disclosed going-concern doubt
    reverse_split_within_year: bool = False  # from dilution (2024-25 rule)
    event_tape: EventTape | None = None  # 8-K tape - derives 3.01 deficiency


@dataclass
class DelistingProfile:
    tier: str = "none"  # none < watch < deficiency < imminent < determination
    hard_exclude: bool = False  # disclosed determination/suspension → hard gate
    extreme_risk: bool = False  # current price <= $0.10
    flags: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=lambda: [DAY_COUNT_CAVEAT])


def compute_delisting(inputs: DelistingInputs) -> DelistingProfile:
    """Grade delisting risk from disclosed notices + current-price context."""
    flags: list[str] = []
    evidence: list[str] = []
    notes: list[str] = [DAY_COUNT_CAVEAT]
    tiers: list[str] = ["none"]

    deficiency = inputs.deficiency_notice
    if inputs.event_tape is not None and inputs.event_tape.signals.has_delisting_notice:
        deficiency = True
        evidence.append("8-K Item 3.01 continued-listing deficiency notice")

    price = inputs.current_price
    extreme_risk = False
    if price is not None and price <= EXTREME_LOW_PRICE:
        extreme_risk = True
        flags.append("PRICE-SUB-10C")
        tiers.append("imminent")
        evidence.append(
            f"current price ${price:.4f} <= $0.10 (Modified Low-Price rule)"
        )
        notes.append(MODIFIED_LOW_PRICE_RULE)
    elif price is not None and price < MIN_BID_PRICE:
        flags.append("PRICE-SUB-1")
        tiers.append("watch")
        evidence.append(f"current price ${price:.2f} < $1.00 minimum bid")

    if deficiency:
        flags.append("DELISTING-DEFICIENCY")
        tiers.append("deficiency")
        notes.append(NASDAQ_MIN_BID_RULE)
        if inputs.disclosed_timeline:
            evidence.append(f"company-disclosed timeline: {inputs.disclosed_timeline}")

    if inputs.going_concern:
        flags.append("GOING-CONCERN")
        tiers.append("watch")

    # Reverse-split secondary-deficiency → immediate determination (2024-25 rule).
    if inputs.reverse_split_within_year and (
        deficiency or (price is not None and price < MIN_BID_PRICE)
    ):
        flags.append("REVERSE-SPLIT-SECONDARY-DEFICIENCY")
        tiers.append("determination")
        evidence.append("reverse split within the prior year + bid-price deficiency")
        notes.append(REVERSE_SPLIT_RULE)

    if inputs.determination_disclosed:
        flags.append("DELISTING-DETERMINATION")
        tiers.append("determination")
        evidence.append("disclosed Staff Delisting Determination / suspension stage")

    tier = max(tiers, key=lambda t: _TIER_RANK[t])
    return DelistingProfile(
        tier=tier,
        hard_exclude=tier == "determination",  # hard gate
        extreme_risk=extreme_risk,
        flags=flags,
        evidence=evidence,
        notes=notes,
    )
