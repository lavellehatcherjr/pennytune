"""News, catalysts & coverage characterization.

Framed as **coverage characterization**, not predictive sentiment: tone
describes *how* a name is being written about - it is evidence, not a forecast.
No keyed news APIs (the tool has no key mechanism). Sources, in reliability
order: EDGAR "Latest Filings" RSS as the dependable spine, then GDELT DOC 2.0
(keyless) for breadth - noisy and entity-indexed, so articles are de-duped by
root URL and the mandatory GDELT attribution travels with any GDELT-derived
output and appears in the docs.

The highest-signal items are the *qualitative* EDGAR full-text booleans
(going-concern, material weakness, related-party, customer concentration) and
newly-added Item-1A risk factors - decision-grade flags, not sentiment.

Architecture: the analytical functions are pure; tone scoring is a pluggable
:class:`ToneBackend` (VADER, falling back to neutral if unavailable), injected
so the logic is fully testable without loading the lexicon.
Edge cases: lexicon absent → neutral with a note; no news → neutral, not
penalized; empty GDELT window → signals suppressed (None), never zero-filled.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol
from urllib.parse import urlsplit

from pennytune.features.events import EventTape
from pennytune.providers.base import ProviderError
from pennytune.providers.http import SafeHttpClient

__all__ = [
    "GDELT_ATTRIBUTION",
    "ToneScore",
    "ToneBackend",
    "NeutralToneBackend",
    "VaderBackend",
    "select_tone_backend",
    "Article",
    "RedFlags",
    "RiskFactorDiff",
    "GdeltSignals",
    "Catalyst",
    "ToneAggregate",
    "CoverageInputs",
    "CoverageProfile",
    "CoverageEvidence",
    "extract_red_flags",
    "diff_risk_factors",
    "parse_gdelt_articles",
    "parse_gdelt_timeline",
    "root_url",
    "dedupe_by_root_url",
    "gdelt_volume_spike",
    "tone_trajectory",
    "tonal_polarization",
    "gkg_theme_tags",
    "promotional_domain_skew",
    "detect_catalysts",
    "aggregate_tone",
    "compute_coverage",
    "gdelt_query",
    "GdeltNewsProvider",
]

# Mandatory GDELT attribution - must travel with any GDELT-derived output and
# appear in the docs.
GDELT_ATTRIBUTION = (
    "This product uses data from The GDELT Project (https://www.gdeltproject.org/)."
)

RED_FLAG_PATTERNS: dict[str, tuple[str, ...]] = {
    "going_concern": ("going concern", "substantial doubt"),
    "material_weakness": ("material weakness",),
    "related_party": ("related party", "related-party"),
    "customer_concentration": (
        "customer concentration",
        "concentration of revenue",
        "one customer",
        "significant customer",
    ),
}
_RISK_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "financing": (
        "financing",
        "capital",
        "dilution",
        "going concern",
        "liquidity",
        "raise",
    ),
    "litigation": (
        "lawsuit",
        "litigation",
        "legal proceeding",
        "investigation",
        "sued",
    ),
    "liquidity": ("liquidity", "cash", "default", "covenant", "insolvency"),
}
_CATALYST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fda": ("fda", "approval", "clinical", "phase 3", "phase iii", "trial"),
    "contract": ("contract", "award", "partnership", "agreement", "purchase order"),
    "uplisting": ("uplist", "uplisting", "nasdaq uplisting", "listing approved"),
    "m&a": ("merger", "acquisition", "acquire", "buyout", "takeover"),
}
_GKG_THEME_MAP: dict[str, str] = {
    "BANKRUPTCY": "bankruptcy",
    "LEGAL": "litigation",
    "LAWSUIT": "litigation",
    "TRIAL": "litigation",
    "FRAUD": "fraud",
    "INVESTIGAT": "investigation",
    "REGULAT": "regulatory",
    "SEC": "regulatory",
    "FDA": "fda",
    "DRUG": "fda",
    "CONTRACT": "contract",
    "MERGER": "m&a",
    "ACQUISITION": "m&a",
}
# Low-quality promotional domains vs. established financial press (illustrative;
# extendable). Promotional skew is a pump precondition (feeds manipulation).
_PROMO_DOMAINS = frozenset(
    {
        "stockpromoters.com",
        "pennystocks.com",
        "ottoday.com",
        "smallcapvoice.com",
        "stocktwits.com",
    }
)
_REPUTABLE_DOMAINS = frozenset(
    {
        "reuters.com",
        "bloomberg.com",
        "wsj.com",
        "sec.gov",
        "ft.com",
        "barrons.com",
        "cnbc.com",
    }
)
_EXTREME_TONE = 5.0  # |tone| beyond this is "extreme" for polarization
_VOLUME_SPIKE_RATIO = 3.0


# ---- tone backends ----------------------------------------------------------


@dataclass
class ToneScore:
    positive: float
    negative: float
    neutral: float
    compound: float
    label: str  # "positive" | "negative" | "neutral"


def _label_from_compound(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


class ToneBackend(Protocol):
    """Pluggable tone scorer (structural; FakeToneBackend in tests satisfies it)."""

    @property
    def name(self) -> str: ...

    def available(self) -> bool: ...

    def score(self, text: str) -> ToneScore: ...

    def score_many(self, texts: Sequence[str]) -> list[ToneScore]: ...


class NeutralToneBackend:
    """No-op backend used when no real tone model is available (tone suppressed)."""

    name = "neutral"

    def available(self) -> bool:
        return True

    def score(self, text: str) -> ToneScore:
        return ToneScore(0.0, 0.0, 1.0, 0.0, "neutral")

    def score_many(self, texts: Sequence[str]) -> list[ToneScore]:
        return [self.score(t) for t in texts]


class VaderBackend:
    """VADER lexicon backend (standalone ``vaderSentiment``; lexicon bundled)."""

    name = "vader"

    def __init__(self) -> None:
        self._analyzer: Any = None

    def available(self) -> bool:
        import importlib.util

        return importlib.util.find_spec("vaderSentiment") is not None

    def _ensure(self) -> Any:
        if self._analyzer is None:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            self._analyzer = SentimentIntensityAnalyzer()
        return self._analyzer

    def score(self, text: str) -> ToneScore:
        scores = self._ensure().polarity_scores(text)
        return ToneScore(
            positive=scores["pos"],
            negative=scores["neg"],
            neutral=scores["neu"],
            compound=scores["compound"],
            label=_label_from_compound(scores["compound"]),
        )

    def score_many(self, texts: Sequence[str]) -> list[ToneScore]:
        return [self.score(t) for t in texts]


def select_tone_backend(
    *,
    vader_available: bool | None = None,
) -> tuple[ToneBackend, str]:
    """Choose a tone backend: VADER if available, else neutral.

    Returns ``(backend, note)``; the note explains any fallback.
    Availability can be injected (tests) to avoid loading the lexicon.
    """
    vader = VaderBackend()
    vd_ok = vader_available if vader_available is not None else vader.available()

    if vd_ok:
        return vader, ""
    return (
        NeutralToneBackend(),
        "No tone backend available — tone suppressed (neutral).",
    )


# ---- data structures --------------------------------------------------------


@dataclass
class Article:
    url: str
    title: str
    seendate: str = ""
    domain: str = ""
    language: str = ""
    sourcecountry: str = ""


@dataclass
class RedFlags:
    going_concern: bool = False
    material_weakness: bool = False
    related_party: bool = False
    customer_concentration: bool = False
    matched: dict[str, str] = field(default_factory=dict)


@dataclass
class RiskFactorDiff:
    added: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.added)


@dataclass
class GdeltSignals:
    article_count: int = 0
    volume_spike: bool = False
    spike_ratio: float | None = None
    tone_trajectory: str | None = None
    polarization: bool = False
    theme_tags: list[str] = field(default_factory=list)
    promotional_skew: float | None = None


@dataclass
class Catalyst:
    kind: str
    date: str
    source: str
    recency_weight: float = 1.0


@dataclass
class ToneAggregate:
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    mean_compound: float = 0.0
    net_label: str = "neutral"
    count: int = 0


@dataclass
class CoverageInputs:
    headlines: list[str] = field(default_factory=list)
    articles: list[Article] = field(default_factory=list)
    filing_text: str = ""
    prior_risk_factors: str = ""
    current_risk_factors: str = ""
    gdelt_volume_series: list[tuple[str, float]] = field(default_factory=list)
    gdelt_tone_series: list[tuple[str, float]] = field(default_factory=list)
    gkg_themes: list[str] = field(default_factory=list)
    event_tape: EventTape | None = None
    now: datetime | None = None
    recency_days: int = 90


@dataclass
class CoverageProfile:
    tone: ToneAggregate
    red_flags: RedFlags
    risk_diff: RiskFactorDiff
    gdelt: GdeltSignals | None
    catalysts: list[Catalyst]
    material_filings: list[str]
    attribution: str | None = None
    tone_backend: str = "neutral"
    flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ---- EDGAR full-text red flags + risk-factor diff ---------------------------


def extract_red_flags(text: str) -> RedFlags:
    """Extract decision-grade qualitative booleans from filing full-text."""
    low = text.lower()
    flags = RedFlags()
    for field_name, patterns in RED_FLAG_PATTERNS.items():
        for pattern in patterns:
            if pattern in low:
                setattr(flags, field_name, True)
                flags.matched[field_name] = pattern
                break
    return flags


def _segments(text: str) -> list[str]:
    raw = text.replace("\r", "\n").split("\n\n")
    return [seg.strip() for seg in raw if seg.strip()]


def diff_risk_factors(prior: str, current: str) -> RiskFactorDiff:
    """Newly-added Item-1A risk factors (pure string diff), categorized."""
    prior_set = {seg.lower() for seg in _segments(prior)}
    added = [seg for seg in _segments(current) if seg.lower() not in prior_set]
    categories: set[str] = set()
    for segment in added:
        low = segment.lower()
        for category, keywords in _RISK_CATEGORY_KEYWORDS.items():
            if any(keyword in low for keyword in keywords):
                categories.add(category)
    return RiskFactorDiff(added=added, categories=sorted(categories))


# ---- GDELT parsing + signals ------------------------------------------------


def parse_gdelt_articles(payload: dict[str, Any]) -> list[Article]:
    """Parse a GDELT DOC 2.0 artlist payload (schema-tolerant, untrusted)."""
    articles: list[Article] = []
    for row in payload.get("articles") or []:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url") or "").strip()
        if not url:
            continue
        articles.append(
            Article(
                url=url,
                title=str(row.get("title") or ""),
                seendate=str(row.get("seendate") or ""),
                domain=str(row.get("domain") or ""),
                language=str(row.get("language") or ""),
                sourcecountry=str(row.get("sourcecountry") or ""),
            )
        )
    return articles


def parse_gdelt_timeline(payload: dict[str, Any]) -> list[tuple[str, float]]:
    """Parse a GDELT timelinevol/timelinetone payload into (date, value) points."""
    timeline = payload.get("timeline") or []
    points: list[tuple[str, float]] = []
    for series in timeline:
        for entry in series.get("data") or []:
            try:
                points.append((str(entry.get("date", "")), float(entry.get("value"))))
            except (TypeError, ValueError):
                continue
        if points:
            break  # first series only
    return points


def root_url(url: str) -> str:
    """Canonical root of a URL (scheme+host+path, no query/fragment, no www)."""
    parts = urlsplit(url)
    host = parts.netloc.lower().removeprefix("www.")
    return f"{host}{parts.path.rstrip('/')}".lower()


def dedupe_by_root_url(articles: Sequence[Article]) -> list[Article]:
    seen: set[str] = set()
    deduped: list[Article] = []
    for article in articles:
        key = root_url(article.url)
        if key not in seen:
            seen.add(key)
            deduped.append(article)
    return deduped


def gdelt_volume_spike(
    series: Sequence[tuple[str, float]], *, threshold: float = _VOLUME_SPIKE_RATIO
) -> tuple[bool, float | None]:
    """Detect a coverage-volume spike: latest vs the prior-window median."""
    if len(series) < 3:
        return False, None
    values = [v for _, v in series]
    latest = values[-1]
    baseline = sorted(values[:-1])[len(values[:-1]) // 2]  # median of the prior window
    if baseline <= 0:
        return (latest > 0, None)
    ratio = latest / baseline
    return ratio >= threshold, ratio


def tone_trajectory(series: Sequence[tuple[str, float]]) -> str | None:
    """Direction of average tone over the window (not a point estimate)."""
    if len(series) < 2:
        return None
    first_half = [v for _, v in series[: len(series) // 2]]
    second_half = [v for _, v in series[len(series) // 2 :]]
    if not first_half or not second_half:
        return None
    delta = sum(second_half) / len(second_half) - sum(first_half) / len(first_half)
    if delta > 0.5:
        return "rising"
    if delta < -0.5:
        return "falling"
    return "flat"


def tonal_polarization(
    tone_values: Sequence[float], *, extreme: float = _EXTREME_TONE
) -> bool:
    """Bimodal mix of extreme-positive and extreme-negative coverage (pump tell)."""
    has_extreme_pos = any(v >= extreme for v in tone_values)
    has_extreme_neg = any(v <= -extreme for v in tone_values)
    return has_extreme_pos and has_extreme_neg


def gkg_theme_tags(themes: Iterable[str]) -> list[str]:
    """Map raw GKG theme codes to PennyTune categories."""
    tags: set[str] = set()
    for theme in themes:
        upper = str(theme).upper()
        for needle, category in _GKG_THEME_MAP.items():
            if needle in upper:
                tags.add(category)
    return sorted(tags)


def promotional_domain_skew(articles: Sequence[Article]) -> float | None:
    """Fraction of classified coverage from low-quality promotional domains."""
    classified = [
        a
        for a in articles
        if _domain_root(a.domain) in _PROMO_DOMAINS
        or _domain_root(a.domain) in _REPUTABLE_DOMAINS
    ]
    if not classified:
        return None
    promo = sum(1 for a in classified if _domain_root(a.domain) in _PROMO_DOMAINS)
    return promo / len(classified)


def _domain_root(domain: str) -> str:
    return domain.lower().removeprefix("www.")


# ---- catalysts + tone aggregation -------------------------------------------


def _age_days(date_str: str, now: datetime) -> int | None:
    for fmt in ("iso", "gdelt"):
        try:
            if fmt == "iso":
                parsed = date.fromisoformat(date_str[:10])
            else:
                parsed = datetime.strptime(date_str[:8], "%Y%m%d").date()
            return (now.date() - parsed).days
        except ValueError:
            continue
    return None


def _recency_weight(date_str: str, now: datetime | None, recency_days: int) -> float:
    if now is None:
        return 1.0
    age = _age_days(date_str, now)
    if age is None:
        return 1.0
    return max(0.0, 1.0 - age / recency_days)


def detect_catalysts(
    event_tape: EventTape | None,
    articles: Sequence[Article],
    *,
    now: datetime | None = None,
    recency_days: int = 90,
) -> list[Catalyst]:
    """Detect catalysts from 8-K item codes and news headlines."""
    catalysts: list[Catalyst] = []
    if event_tape is not None:
        for event in event_tape.events:
            if "1.01" in event.item_codes:
                catalysts.append(
                    Catalyst(
                        "contract",
                        event.filing_date,
                        f"8-K {event.accession}",
                        _recency_weight(event.filing_date, now, recency_days),
                    )
                )
            if "2.02" in event.item_codes:
                catalysts.append(
                    Catalyst(
                        "earnings",
                        event.filing_date,
                        f"8-K {event.accession}",
                        _recency_weight(event.filing_date, now, recency_days),
                    )
                )
    for article in articles:
        low = article.title.lower()
        for kind, keywords in _CATALYST_KEYWORDS.items():
            if any(keyword in low for keyword in keywords):
                catalysts.append(
                    Catalyst(
                        kind,
                        article.seendate,
                        article.url,
                        _recency_weight(article.seendate, now, recency_days),
                    )
                )
                break
    return catalysts


def aggregate_tone(scores: Sequence[ToneScore]) -> ToneAggregate:
    if not scores:
        return ToneAggregate()
    positive = sum(1 for s in scores if s.label == "positive")
    negative = sum(1 for s in scores if s.label == "negative")
    neutral = sum(1 for s in scores if s.label == "neutral")
    mean = sum(s.compound for s in scores) / len(scores)
    return ToneAggregate(
        positive=positive,
        negative=negative,
        neutral=neutral,
        mean_compound=mean,
        net_label=_label_from_compound(mean),
        count=len(scores),
    )


# ---- orchestration ----------------------------------------------------------


def compute_coverage(
    inputs: CoverageInputs, tone_backend: ToneBackend
) -> CoverageProfile:
    """Characterize coverage: tone, red flags, risk diff, GDELT signals, catalysts."""
    red_flags = (
        extract_red_flags(inputs.filing_text) if inputs.filing_text else RedFlags()
    )
    risk_diff = (
        diff_risk_factors(inputs.prior_risk_factors, inputs.current_risk_factors)
        if inputs.current_risk_factors
        else RiskFactorDiff()
    )

    headlines = list(inputs.headlines) or [a.title for a in inputs.articles if a.title]
    tone = (
        aggregate_tone(tone_backend.score_many(headlines))
        if headlines
        else ToneAggregate()
    )

    deduped = dedupe_by_root_url(inputs.articles)
    has_gdelt = bool(
        deduped
        or inputs.gdelt_volume_series
        or inputs.gdelt_tone_series
        or inputs.gkg_themes
    )
    gdelt: GdeltSignals | None = None
    attribution: str | None = None
    if has_gdelt:  # empty window → suppressed (None), never zero-filled
        spike, ratio = gdelt_volume_spike(inputs.gdelt_volume_series)
        tone_values = [v for _, v in inputs.gdelt_tone_series]
        gdelt = GdeltSignals(
            article_count=len(deduped),
            volume_spike=spike,
            spike_ratio=ratio,
            tone_trajectory=tone_trajectory(inputs.gdelt_tone_series),
            polarization=tonal_polarization(tone_values),
            theme_tags=gkg_theme_tags(inputs.gkg_themes),
            promotional_skew=promotional_domain_skew(deduped),
        )
        attribution = GDELT_ATTRIBUTION

    catalysts = detect_catalysts(
        inputs.event_tape, deduped, now=inputs.now, recency_days=inputs.recency_days
    )
    material_filings = (
        [f"{e.filing_date} {e.form} {e.category}" for e in inputs.event_tape.events]
        if inputs.event_tape is not None
        else []
    )

    flags: list[str] = []
    if red_flags.going_concern:
        flags.append("GOING-CONCERN")
    if red_flags.material_weakness:
        flags.append("MATERIAL-WEAKNESS")
    if gdelt is not None and (
        gdelt.polarization or (gdelt.promotional_skew or 0.0) >= 0.5
    ):
        flags.append("PROMOTIONAL-COVERAGE")
    if not headlines and not has_gdelt:
        flags.append("LOW-COVERAGE")  # neutral, not penalized

    return CoverageProfile(
        tone=tone,
        red_flags=red_flags,
        risk_diff=risk_diff,
        gdelt=gdelt,
        catalysts=catalysts,
        material_filings=material_filings,
        attribution=attribution,
        tone_backend=tone_backend.name,
        flags=flags,
    )


# ---- fetch boundary: GDELT DOC 2.0 breadth (EDGAR spine reused upstream) ------
#
# GDELT is the noisy *breadth* layer (keyless). The EDGAR Latest-Filings spine is
# the issuer submissions already fetched upstream (the same filing list the
# per-company RSS returns), passed in as the event tape — so no redundant SEC
# fetch. Fetched article titles/metadata are DATA parsed structurally (VADER
# tone, domain/theme classification), never instructions. GDELT rate-limits
# bursts (429/503): a 429 is retried by the hardened client's existing backoff;
# any other failure degrades only the GDELT slice (the spine still stands).

_GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_GDELT_MAX_RECORDS = "30"
_GDELT_TIMESPAN = "3m"
# Keyless app User-Agent for GDELT (which requires none) so the SEC EDGAR
# identity (name + email) is transmitted ONLY to the SEC, never to GDELT.
_GDELT_USER_AGENT = "PennyTune"
_GDELT_SUFFIXES = frozenset(
    {
        "INC",
        "INCORPORATED",
        "CORP",
        "CORPORATION",
        "CO",
        "COMPANY",
        "LTD",
        "LIMITED",
        "LLC",
        "LLP",
        "LP",
        "PLC",
        "SA",
        "NV",
        "AG",
        "AB",
        "COM",
    }  # fmt: skip
)


@dataclass
class CoverageEvidence:
    """The news/coverage slice of the per-ticker evidence.

    Maps the rich :class:`CoverageProfile` onto the three scored
    ``RawEvidence`` news fields. ``sentiment_compound`` is a *modest* positive
    contributor (never a gate); ``gdelt_used`` makes the mandatory GDELT
    attribution travel. No coverage is clean (sentiment suppressed, never
    penalized); a GDELT failure degrades only that slice.
    """

    sentiment_compound: float | None = None
    news_available: bool = True
    gdelt_used: bool = False
    profile: CoverageProfile | None = None
    completeness: list[str] = field(default_factory=list)


def gdelt_query(company: str, ticker: str) -> str:
    """A GDELT phrase query for an issuer (company name preferred, ticker fallback).

    Entity designators (Inc/Corp/…) are dropped; the company name is quoted so
    GDELT phrase-matches it. The query is issuer identity we control — never
    fetched content.
    """
    import re as _re

    tokens = [
        t
        for t in _re.sub(r"[^A-Za-z0-9 ]", " ", company).upper().split()
        if t not in _GDELT_SUFFIXES
    ]
    if tokens:
        return '"' + " ".join(tokens) + '"'
    return ticker.upper()


class GdeltNewsProvider:
    """Fetch boundary: GDELT DOC 2.0 article breadth, scored by the pure analytics.

    Per ticker, one keyless GDELT ``artlist`` call (429-retried by the client's
    existing backoff); the result plus the upstream EDGAR event-tape spine are
    fed to the unchanged :func:`compute_coverage`. A GDELT failure leaves the
    spine intact and is flagged — never fabricated, never penalized.
    """

    GDELT_DOC_URL = _GDELT_DOC_URL

    def __init__(
        self, client: SafeHttpClient, *, tone_backend: ToneBackend | None = None
    ) -> None:
        self._client = client
        if tone_backend is not None:
            self._tone: ToneBackend = tone_backend
            self._tone_note = ""
        else:
            self._tone, self._tone_note = select_tone_backend()

    def _fetch_articles(self, query: str) -> list[Article]:
        payload = self._client.get_json(
            self.GDELT_DOC_URL,
            provider="gdelt",
            headers={"User-Agent": _GDELT_USER_AGENT},
            params={
                "query": query,
                "mode": "artlist",
                "format": "json",
                "maxrecords": _GDELT_MAX_RECORDS,
                "timespan": _GDELT_TIMESPAN,
                "sort": "datedesc",
            },
        )
        return dedupe_by_root_url(parse_gdelt_articles(payload))

    def get_coverage_evidence(
        self,
        ticker: str,
        company: str,
        *,
        event_tape: EventTape | None = None,
        now: datetime | None = None,
    ) -> CoverageEvidence:
        """Characterize coverage for one issuer (GDELT breadth + EDGAR spine)."""
        completeness: list[str] = []
        articles: list[Article] = []
        try:
            articles = self._fetch_articles(gdelt_query(company, ticker))
        except ProviderError as exc:
            completeness.append(
                f"GDELT coverage unavailable ({exc}) — EDGAR filing spine still used"
            )
        if self._tone_note:
            completeness.append(self._tone_note)

        profile = compute_coverage(
            CoverageInputs(articles=articles, event_tape=event_tape, now=now),
            self._tone,
        )
        sentiment = profile.tone.mean_compound if profile.tone.count else None
        return CoverageEvidence(
            sentiment_compound=sentiment,  # modest contributor; None = suppressed
            news_available=True,  # we checked — absence is clean, not negative
            gdelt_used=profile.gdelt is not None,  # → GDELT attribution travels
            profile=profile,
            completeness=completeness,
        )
