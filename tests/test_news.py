"""News / coverage-characterization tests. Fixtures + fake backend."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

import pytest
import responses
import tenacity

from pennytune.features.events import build_event, build_event_tape
from pennytune.features.news import (
    GDELT_ATTRIBUTION,
    Article,
    CoverageInputs,
    GdeltNewsProvider,
    NeutralToneBackend,
    ToneScore,
    aggregate_tone,
    compute_coverage,
    dedupe_by_root_url,
    detect_catalysts,
    diff_risk_factors,
    extract_red_flags,
    gdelt_query,
    gdelt_volume_spike,
    gkg_theme_tags,
    parse_gdelt_articles,
    promotional_domain_skew,
    root_url,
    select_tone_backend,
    tonal_polarization,
    tone_trajectory,
)
from pennytune.providers.base import ProviderError
from pennytune.providers.http import SafeHttpClient
from pennytune.ratelimit import make_retrying


class FakeToneBackend:
    """Deterministic, keyword-driven tone backend - no model, no network."""

    name = "fake"

    def available(self) -> bool:
        return True

    def score(self, text: str) -> ToneScore:
        low = text.lower()
        if any(w in low for w in ("doubt", "lawsuit", "loss", "decline", "bankruptcy")):
            return ToneScore(0.0, 0.6, 0.4, -0.6, "negative")
        if any(w in low for w in ("approval", "contract", "award", "growth", "record")):
            return ToneScore(0.6, 0.0, 0.4, 0.6, "positive")
        return ToneScore(0.0, 0.0, 1.0, 0.0, "neutral")

    def score_many(self, texts: Sequence[str]) -> list[ToneScore]:
        return [self.score(t) for t in texts]


# ---- red flags + risk-factor diff -------------------------------------------


def test_red_flag_booleans() -> None:
    flags = extract_red_flags(
        "There is substantial doubt about our ability to continue as a going concern. "
        "We identified a material weakness in internal control."
    )
    assert flags.going_concern is True
    assert flags.material_weakness is True
    clean = extract_red_flags("A healthy company with a clean audit opinion.")
    assert clean.going_concern is False
    assert clean.material_weakness is False


def test_risk_factor_diff() -> None:
    prior = "Risk A: competition.\n\nRisk B: regulation."
    current = (
        "Risk A: competition.\n\nRisk B: regulation.\n\n"
        "We may need additional financing and could face dilution."
    )
    diff = diff_risk_factors(prior, current)
    assert diff.count == 1
    assert "financing" in diff.categories


# ---- GDELT parsing / dedupe / signals ---------------------------------------


def test_parse_and_dedupe_by_root_url() -> None:
    payload = {
        "articles": [
            {"url": "https://x.com/a?utm=1", "title": "T1", "domain": "x.com"},
            {"url": "https://www.x.com/a", "title": "T1 dup", "domain": "x.com"},
        ]
    }
    articles = parse_gdelt_articles(payload)
    assert len(articles) == 2
    assert root_url("https://www.x.com/a") == "x.com/a"
    assert len(dedupe_by_root_url(articles)) == 1


def test_volume_spike_detection() -> None:
    spike, ratio = gdelt_volume_spike(
        [("d1", 1.0), ("d2", 1.0), ("d3", 1.0), ("d4", 5.0)]
    )
    assert spike is True
    assert ratio == pytest.approx(5.0)
    flat, _ = gdelt_volume_spike([("d1", 1.0), ("d2", 1.1), ("d3", 0.9), ("d4", 1.2)])
    assert flat is False


def test_tone_trajectory() -> None:
    assert (
        tone_trajectory([("d1", -2.0), ("d2", -1.0), ("d3", 2.0), ("d4", 4.0)])
        == "rising"
    )
    assert (
        tone_trajectory([("d1", 4.0), ("d2", 2.0), ("d3", -1.0), ("d4", -3.0)])
        == "falling"
    )


def test_tonal_polarization() -> None:
    assert tonal_polarization([8.0, -7.0, 9.0, -8.0]) is True  # pump signature
    assert tonal_polarization([1.0, 2.0, 1.0]) is False


def test_gkg_theme_tags() -> None:
    tags = gkg_theme_tags(["ECON_BANKRUPTCY", "LEGAL_TROUBLE", "TAX_FDA_APPROVAL"])
    assert "bankruptcy" in tags
    assert "litigation" in tags
    assert "fda" in tags


def test_promotional_domain_skew() -> None:
    articles = [
        Article("u1", "t", domain="stockpromoters.com"),
        Article("u2", "t", domain="reuters.com"),
        Article("u3", "t", domain="randomblog.com"),  # unclassified, ignored
    ]
    assert promotional_domain_skew(articles) == pytest.approx(0.5)


# ---- catalysts + recency ----------------------------------------------------


def test_catalyst_detection_from_events_and_news() -> None:
    tape = build_event_tape([build_event("a", "2026-05-30", "8-K", "1.01")])
    articles = [
        Article(
            "u", "FDA approval granted for lead drug", "20260601T000000Z", "biz.com"
        )
    ]
    kinds = {c.kind for c in detect_catalysts(tape, articles)}
    assert "contract" in kinds  # from 8-K Item 1.01
    assert "fda" in kinds  # from the headline


def test_catalyst_recency_weighting() -> None:
    now = datetime(2026, 6, 1)
    tape = build_event_tape(
        [
            build_event("a", "2026-05-30", "8-K", "2.02"),
            build_event("b", "2025-06-01", "8-K", "2.02"),
        ]
    )
    catalysts = detect_catalysts(tape, [], now=now, recency_days=90)
    recent = next(c for c in catalysts if c.date == "2026-05-30")
    old = next(c for c in catalysts if c.date == "2025-06-01")
    assert recent.recency_weight > old.recency_weight


# ---- tone aggregate + backend selection -------------------------------------


def test_aggregate_tone() -> None:
    backend = FakeToneBackend()
    agg = aggregate_tone(
        backend.score_many(["contract award", "substantial doubt", "ordinary update"])
    )
    assert agg.count == 3
    assert (agg.positive, agg.negative, agg.neutral) == (1, 1, 1)
    assert agg.net_label == "neutral"  # +0.6, -0.6, 0 → mean 0


def test_select_backend_prefers_vader() -> None:
    backend, note = select_tone_backend(vader_available=True)
    assert backend.name == "vader"
    assert note == ""


def test_select_backend_neutral_when_vader_unavailable() -> None:
    backend, note = select_tone_backend(vader_available=False)
    assert backend.name == "neutral"
    assert note


# ---- compute_coverage orchestration -----------------------------------------


def test_attribution_string_content() -> None:
    assert "GDELT Project" in GDELT_ATTRIBUTION
    assert "gdeltproject.org" in GDELT_ATTRIBUTION


def test_no_news_is_neutral_not_penalized() -> None:
    profile = compute_coverage(CoverageInputs(), FakeToneBackend())
    assert profile.tone.count == 0
    assert profile.tone.net_label == "neutral"
    assert profile.gdelt is None  # empty GDELT window → suppressed, not zero-filled
    assert profile.attribution is None
    assert "LOW-COVERAGE" in profile.flags


def test_gdelt_empty_suppressed_when_only_headlines() -> None:
    profile = compute_coverage(
        CoverageInputs(headlines=["ordinary update"]), FakeToneBackend()
    )
    assert profile.gdelt is None
    assert profile.attribution is None


def test_compute_coverage_with_gdelt_and_red_flags() -> None:
    inputs = CoverageInputs(
        articles=[
            Article(
                "https://reuters.com/x",
                "Company wins big contract award",
                "20260530T000000Z",
                "reuters.com",
            )
        ],
        gdelt_volume_series=[("d1", 1.0), ("d2", 1.0), ("d3", 5.0)],
        gkg_themes=["ECON_BANKRUPTCY"],
        filing_text="There is substantial doubt about going concern.",
    )
    profile = compute_coverage(inputs, FakeToneBackend())
    assert profile.gdelt is not None
    assert (
        profile.attribution == GDELT_ATTRIBUTION
    )  # GDELT-derived → attribution travels
    assert profile.gdelt.volume_spike is True
    assert "bankruptcy" in profile.gdelt.theme_tags
    assert profile.red_flags.going_concern is True
    assert "GOING-CONCERN" in profile.flags
    assert profile.tone.net_label == "positive"  # headline tone
    assert profile.tone_backend == "fake"


# ---- the live GDELT fetch boundary (parse-not-obey; 429 retry; clean path) ---


def _gdelt_payload(*titles: str, domain: str = "reuters.com") -> dict[str, Any]:
    return {
        "articles": [
            {
                "url": f"https://{domain}/a{i}",
                "title": t,
                "domain": domain,
                "seendate": "20260510T120000Z",
            }
            for i, t in enumerate(titles)
        ]
    }


class _FakeNewsClient:
    def __init__(self, payload: Any = None, error: Exception | None = None) -> None:
        self._payload = payload
        self._error = error
        self.calls = 0

    def get_json(self, url: str, **kwargs: Any) -> Any:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._payload


def test_news_provider_parses_gdelt_sets_attribution_and_tone() -> None:
    client = _FakeNewsClient(
        _gdelt_payload("Acme wins FDA approval", "Acme lands a contract")
    )
    provider = GdeltNewsProvider(client, tone_backend=FakeToneBackend())  # type: ignore[arg-type]
    ev = provider.get_coverage_evidence("ACME", "Acme Inc")
    assert ev.gdelt_used is True  # GDELT data used → attribution travels
    assert ev.profile is not None and ev.profile.attribution == GDELT_ATTRIBUTION
    assert ev.profile.gdelt is not None and ev.profile.gdelt.article_count == 2
    assert ev.news_available is True
    assert ev.sentiment_compound is not None and ev.sentiment_compound > 0


def test_news_provider_no_coverage_is_clean_not_negative() -> None:
    provider = GdeltNewsProvider(
        _FakeNewsClient({"articles": []}),  # type: ignore[arg-type]
        tone_backend=NeutralToneBackend(),
    )
    ev = provider.get_coverage_evidence("CLEAN", "Clean Co")
    assert ev.sentiment_compound is None  # suppressed → not scored (not negative)
    assert ev.gdelt_used is False  # no GDELT signal
    assert ev.news_available is True  # checked
    assert ev.completeness == []  # clean is NOT a degraded flag


def test_news_provider_gdelt_failure_degrades_only_its_slice() -> None:
    client = _FakeNewsClient(error=ProviderError("HTTP 503"))
    provider = GdeltNewsProvider(client, tone_backend=NeutralToneBackend())  # type: ignore[arg-type]
    tape = build_event_tape([build_event("a", "2026-05-01", "8-K", "2.02")])
    ev = provider.get_coverage_evidence("X", "X Co", event_tape=tape)
    assert ev.gdelt_used is False and ev.sentiment_compound is None  # not penalized
    assert any("GDELT coverage unavailable" in note for note in ev.completeness)
    # the EDGAR filing spine (the event tape) still produced output
    assert ev.profile is not None and ev.profile.material_filings


@responses.activate
def test_news_provider_gdelt_429_recovers_via_client_backoff() -> None:
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    responses.add(responses.GET, url, status=429)  # GDELT rate-limits the burst…
    responses.add(responses.GET, url, json=_gdelt_payload("Acme update"), status=200)
    client = SafeHttpClient(
        user_agent="Dana Lee dana@example.com",
        retrier_factory=lambda: make_retrying(
            max_attempts=3, wait=tenacity.wait_none()
        ),
    )
    provider = GdeltNewsProvider(client, tone_backend=NeutralToneBackend())
    ev = provider.get_coverage_evidence("ACME", "Acme Inc")
    assert ev.gdelt_used is True  # …and the existing client backoff recovers it
    assert ev.profile is not None and ev.profile.gdelt is not None
    assert ev.profile.gdelt.article_count == 1
    client.close()


def test_gdelt_query_drops_entity_suffixes() -> None:
    assert gdelt_query("Ocugen, Inc.", "OCGN") == '"OCUGEN"'
    assert gdelt_query("U S Global Investors Inc", "GROW") == '"U S GLOBAL INVESTORS"'
    assert gdelt_query("", "GROW") == "GROW"  # fallback to the ticker
