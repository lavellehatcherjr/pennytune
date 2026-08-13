"""Composite scoring & ranking - the signal-fusion stage.

All feature signals converge into one transparent, decomposable composite:

    score = sum(weight_i * sub_score_i) - sum(penalty_j * severity_j * conf_j)

* **Positive contributors** (valuation, growth, fundamental momentum, coverage
  tone, insider conviction, financial health) are normalized sub-scores in
  [0, 1] - graded against **fixed published reference bands**, never against
  the other tickers in the same run - times config weights.
* **Penalty overlays** subtract, scaled by severity AND metric confidence, and
  by the **active preset bundle**: penny-native overlays carry full weight
  under penny/micro and are de-emphasized toward broad; up-market overlays are
  dormant under penny and weighted in under broad. A module with zero preset
  weight renders **"n/a for this preset"**, never a silent pass.
* **FTDs are context only** - never added to the score.
* **Hard gates** (active SEC trading suspension, disclosed determination-stage
  delisting) move a name to a separate HIGH-RISK section regardless of score.
  There is no tradeability/spread gate and no intraday-halt gate (no price
  data, no live halt feed) - every result carries a "verify tradeability and
  halt status yourself" note.

Most signals are weighted contributions (no single one makes or breaks a
recommendation); only the two gates are pass/fail. "Recommend" means
rank-and-shortlist, NOT buy advice - a high rank means "worth your due
diligence", never "this will go up".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from pennytune.features.quant_scores import DISTRESS_ZONE_MAX, SAFE_ZONE_MIN

__all__ = [
    "TRADEABILITY_NOTE",
    "POSITIVE_KEYS",
    "PENALTY_MODULES",
    "PositiveSubScores",
    "Penalty",
    "Gates",
    "ScoreInputs",
    "ScoreBreakdown",
    "RankedResult",
    "percentile_to_subscore",
    "score_candidate",
    "rank_candidates",
]

TRADEABILITY_NOTE = (
    "verify tradeability (bid-ask spread, liquidity) and current trading-halt "
    "status yourself in a brokerage before trading — not evaluated here "
    "(no price data; no live halt feed)."
)

POSITIVE_KEYS: tuple[str, ...] = (
    "valuation",
    "growth",
    "fundamental_momentum",
    "sentiment",
    "insider",
    "fin_health",
)

# Penalty module → (profile penalty-magnitude key | None, preset-bundle key | None).
# A None magnitude key uses base 1.0 (up-market modules have no profile key); a
# None preset key means the module always applies (preset weight 1.0).
PENALTY_MODULES: dict[str, tuple[str | None, str | None]] = {
    "dilution": ("dilution", "dilution"),
    "manipulation": ("manipulation", "manipulation_susceptibility"),
    "delisting": ("delisting", "delisting"),
    "halt_suspension": ("halt_suspension", None),
    "insider_selling": ("insider_selling", None),
    "distress": ("distress", None),
    # Grey-zone solvency caution. Deliberately shares the ``distress`` profile
    # magnitude rather than introducing a config key: it is the same underlying
    # measurement at a lower severity, so one knob should govern both.
    "solvency_watch": ("distress", None),
    "beneish": ("beneish", None),
    "goodwill_impairment": (None, "goodwill_impairment"),
    "multiple_compression": (None, "multiple_compression"),
    "leverage_coverage": (None, "leverage_coverage"),
    "sbc_dilution": (None, "sbc_dilution"),
}


@dataclass
class PositiveSubScores:
    """Normalized positive contributors in [0, 1] (higher = better)."""

    valuation: float = 0.0
    growth: float = 0.0
    fundamental_momentum: float = 0.0
    sentiment: float = 0.0
    insider: float = 0.0
    fin_health: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {key: float(getattr(self, key)) for key in POSITIVE_KEYS}


@dataclass
class Penalty:
    """A penalty's severity [0, 1] and metric confidence [0, 1]."""

    severity: float
    confidence: float = 1.0


@dataclass
class Gates:
    """Hard gates. Any one → move to the HIGH-RISK section."""

    active_suspension: bool = False  # SEC trading-suspension risk
    disclosed_determination: bool = False  # delisting risk

    @property
    def hard_excluded(self) -> bool:
        return self.active_suspension or self.disclosed_determination

    def reasons(self) -> list[str]:
        reasons: list[str] = []
        if self.active_suspension:
            reasons.append("active SEC trading suspension")
        if self.disclosed_determination:
            reasons.append("disclosed delisting determination/suspension")
        return reasons


@dataclass
class ScoreInputs:
    ticker: str
    sic_sector: str = ""
    positives: PositiveSubScores = field(default_factory=PositiveSubScores)
    penalties: dict[str, Penalty] = field(default_factory=dict)
    gates: Gates = field(default_factory=Gates)
    suppressed: list[str] = field(default_factory=list)


@dataclass
class ScoreBreakdown:
    ticker: str
    composite: float
    sic_sector: str = ""
    positive_contributions: dict[str, float] = field(default_factory=dict)
    penalty_contributions: dict[str, float] = field(default_factory=dict)
    na_modules: list[str] = field(default_factory=list)
    gated: bool = False
    gate_reasons: list[str] = field(default_factory=list)
    # Modules that could NOT be computed for this name. Distinct from
    # ``na_modules`` (dormant because the active preset zeroes them) and from a
    # module that ran and found nothing: an absent penalty key alone cannot tell
    # those apart, so this records which checks never happened.
    suppressed: list[str] = field(default_factory=list)
    # Per-ticker completeness notes, carried onto the breakdown so every export
    # format receives them without threading a second map through the writers.
    completeness: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=lambda: [TRADEABILITY_NOTE])


@dataclass
class RankedResult:
    ranked: list[ScoreBreakdown] = field(
        default_factory=list
    )  # non-gated, desc by composite
    high_risk: list[ScoreBreakdown] = field(default_factory=list)  # gated
    top: list[ScoreBreakdown] = field(
        default_factory=list
    )  # ranked[:top_n] for display
    sector_ranks: dict[str, tuple[int, int]] = field(
        default_factory=dict
    )  # ticker → (rank, sector size)

    @property
    def full(self) -> list[ScoreBreakdown]:
        """The complete set (ranked + high-risk) - always exported, ignoring --top."""
        return self.ranked + self.high_risk


def percentile_to_subscore(percentile: float, *, higher_is_better: bool) -> float:
    """Map a sector/size percentile [0, 1] to a [0, 1] sub-score.

    Off the scoring path, kept as a general utility. A percentile only means
    something across a large cross-section; a scan covers at most 100 curated
    names, where peer groups of size 1 make ``rank(pct=True)`` a constant 1.0
    whatever the input. Positive sub-scores come from the absolute anchors below.
    """
    clamped = min(1.0, max(0.0, percentile))
    return clamped if higher_is_better else 1.0 - clamped


# ---- absolute anchors -------------------------------------------------------
#
# Each positive contributor is scored against a published, fixed reference so
# it discriminates without needing a cross-section. A metric that cannot be
# computed returns ``None`` and is SUPPRESSED by the caller (not assigned), so
# it never enters the composite as a zero.

_GROWTH_FLOOR = -0.20  # -20% YoY revenue or worse earns no growth credit
_GROWTH_CEILING = 0.40  # +40% YoY revenue or better earns full credit
_PIOTROSKI_MAX = 9.0  # Piotroski F-score is published on a fixed 0-9 scale
_EV_SALES_CHEAP = 1.0  # EV/Sales <= 1x earns full valuation credit
_EV_SALES_RICH = 10.0  # EV/Sales >= 10x earns none
# math.exp overflows near 710; clamp well short of it.
_LOGISTIC_LIMIT = 700.0


def growth_subscore(revenue_growth: float) -> float:
    """Absolute anchor for YoY revenue growth, clamped to [0, 1]."""
    span = _GROWTH_CEILING - _GROWTH_FLOOR
    return round(min(1.0, max(0.0, (revenue_growth - _GROWTH_FLOOR) / span)), 4)


def piotroski_subscore(score: float) -> float:
    """Absolute anchor: Piotroski F on its published 0-9 scale."""
    return round(min(1.0, max(0.0, score / _PIOTROSKI_MAX)), 4)


def valuation_subscore(ev_to_sales: float) -> float:
    """Absolute anchor: cheaper EV/Sales earns more credit."""
    span = _EV_SALES_RICH - _EV_SALES_CHEAP
    return round(min(1.0, max(0.0, (_EV_SALES_RICH - ev_to_sales) / span)), 4)


def financial_health_subscore(altman_z: float | None) -> float | None:
    """Grade Altman Z'' continuously into a [0, 1] financial-health sub-score.

    Grades the raw score, not the three-value solvency zone. Reading the zone
    ties roughly 38% of all filer pairs and about 93% of pairs within micro caps,
    where nearly every name lands in one band, so more input data cannot improve
    the ranking. The raw score does carry ordering information inside that
    population, so discarding it costs real discrimination.

    Shape: a logistic in ``asinh`` space. ``asinh`` is a signed log - linear near
    zero, logarithmic in the tails - which matters because Z'' is violently
    left-skewed (observed range -284 to +13, with 36% of filers below zero). A
    logistic on the raw value saturates to a flat zero below about -10 and would
    re-create the tie problem for exactly the distressed micro caps this tool
    exists to rank.

    Anchored so the two re-calibrated zone cutoffs land at the quartiles:
    ``DISTRESS_ZONE_MAX`` maps to 0.25 and ``SAFE_ZONE_MIN`` to 0.75. The
    sub-score is therefore monotonic in Z'' and consistent with the distress
    penalty, which reads the same zones - a company can never earn more health
    credit and a heavier distress penalty at once.

    Returns ``None`` when Z'' is not computable, so the caller suppresses the
    contributor rather than scoring it as worst-in-class.
    """
    if altman_z is None:
        return None
    lo, hi = math.asinh(DISTRESS_ZONE_MAX), math.asinh(SAFE_ZONE_MIN)
    midpoint = (lo + hi) / 2.0
    # Places 0.25 at ``lo`` and 0.75 at ``hi``: logit(0.75) = ln 3.
    steepness = 2.0 * math.log(3.0) / (hi - lo)
    exponent = steepness * (math.asinh(altman_z) - midpoint)
    if exponent <= -_LOGISTIC_LIMIT:
        return 0.0
    if exponent >= _LOGISTIC_LIMIT:
        return 1.0
    return round(1.0 / (1.0 + math.exp(-exponent)), 6)


def score_candidate(
    inputs: ScoreInputs,
    *,
    positive_weights: dict[str, float],
    penalty_magnitudes: dict[str, float],
    preset_bundle: dict[str, float],
) -> ScoreBreakdown:
    """Fuse one candidate's signals into a decomposable composite + breakdown."""
    positive_contributions: dict[str, float] = {}
    for key, sub_score in inputs.positives.as_dict().items():
        positive_contributions[key] = positive_weights.get(key, 1.0) * sub_score
    positive_total = sum(positive_contributions.values())

    penalty_contributions: dict[str, float] = {}
    na_modules: list[str] = []
    for module, penalty in inputs.penalties.items():
        if module not in PENALTY_MODULES:
            # Unrecognized module - e.g. short interest / FTDs are CONTEXT ONLY
            # and must never add to the score.
            continue
        mag_key, preset_key = PENALTY_MODULES[module]
        magnitude = penalty_magnitudes.get(mag_key, 1.0) if mag_key else 1.0
        preset_weight = preset_bundle.get(preset_key, 1.0) if preset_key else 1.0
        if preset_key is not None and preset_weight == 0.0:
            na_modules.append(
                module
            )  # dormant for this tier - shown, never a silent pass
            continue
        penalty_contributions[module] = (
            magnitude * preset_weight * penalty.severity * penalty.confidence
        )
    penalty_total = sum(penalty_contributions.values())

    return ScoreBreakdown(
        ticker=inputs.ticker,
        composite=positive_total - penalty_total,
        sic_sector=inputs.sic_sector,
        positive_contributions=positive_contributions,
        penalty_contributions=penalty_contributions,
        na_modules=na_modules,
        gated=inputs.gates.hard_excluded,
        gate_reasons=inputs.gates.reasons(),
        suppressed=list(inputs.suppressed),
        notes=[TRADEABILITY_NOTE],
    )


def rank_candidates(
    breakdowns: list[ScoreBreakdown], *, top_n: int | None = None
) -> RankedResult:
    """Rank the full qualifying universe; gated names go to a HIGH-RISK section."""
    gated = [b for b in breakdowns if b.gated]
    non_gated = [b for b in breakdowns if not b.gated]
    # Stable ordering: composite desc, then ticker for determinism (reproducible).
    ranked = sorted(non_gated, key=lambda b: (-b.composite, b.ticker))
    high_risk = sorted(gated, key=lambda b: (-b.composite, b.ticker))
    top = ranked[:top_n] if top_n is not None else ranked

    sector_ranks: dict[str, tuple[int, int]] = {}
    sectors: dict[str, list[ScoreBreakdown]] = {}
    for breakdown in ranked:
        sectors.setdefault(breakdown.sic_sector, []).append(breakdown)
    for members in sectors.values():
        ordered = sorted(members, key=lambda b: (-b.composite, b.ticker))
        for position, breakdown in enumerate(ordered, start=1):
            sector_ranks[breakdown.ticker] = (position, len(ordered))

    return RankedResult(
        ranked=ranked, high_risk=high_risk, top=top, sector_ranks=sector_ranks
    )
