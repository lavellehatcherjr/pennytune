"""Calibration regression tests: the ranking must be defensible for micro-caps.

Each case pins a failure mode seen against live SEC data, reduced to a fixture
so it runs offline:

* the toxic-financing EFTS probe matched loose words instead of the phrase, so
  every large cap scored a false dilution hit;
* delisting risk was read only from 8-K Item 3.01, which real issuers routinely
  do not use for a continued-listing disclosure;
* the reverse-split detector read a share-count series that mixed
  split-adjusted restatements with as-reported values, so Apple registered
  three reverse splits it never did.
"""

from __future__ import annotations

from typing import Any

from pennytune.features.delisting import DelistingInputs, compute_delisting
from pennytune.features.dilution import (
    EdgarDilutionProvider,
    detect_reverse_splits,
    share_count_series,
)
from pennytune.features.quant_scores import PeriodFinancials, altman_z

# ---- Defect 3: the toxic-financing query must be an exact phrase -------------


class _RecordingClient:
    """Captures the params of every EFTS request the provider issues."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def get_json(
        self, url: str, *, provider: str = "", params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.calls.append({"url": url, "params": dict(params or {})})
        return {"hits": {"hits": [], "total": {"value": 0}}}


def test_toxic_financing_query_is_an_exact_phrase() -> None:
    """An unquoted multi-word EFTS query matches the words, not the phrase.

    Live A/B at the time of writing: unquoted returned 18/21/29/88/123 hits for
    AAPL/MSFT/JNJ/KO/WMT; the quoted phrase returned 0 for all five, while
    still returning 54/16/34 for ASNS/GITS/LASE. Every large-cap hit was false.
    """
    phrase = EdgarDilutionProvider.TOXIC_EFTS_PHRASE
    assert phrase.startswith('"') and phrase.endswith('"'), (
        f"EFTS phrase must be quoted or it matches loose words: {phrase!r}"
    )


def test_toxic_financing_probe_sends_the_quoted_phrase() -> None:
    """End-to-end through the provider: the wire query must carry the quotes."""
    client = _RecordingClient()
    provider = EdgarDilutionProvider(client)  # type: ignore[arg-type]
    provider.full_text_search(provider.TOXIC_EFTS_PHRASE, forms="8-K", ciks="320193")
    sent = client.calls[0]["params"]["q"]
    assert sent.startswith('"') and sent.endswith('"'), (
        f"query reached the wire unquoted: {sent!r}"
    )


# ---- Defect 2: delisting must see disclosures outside 8-K Item 3.01 ---------


def test_delisting_detects_deficiency_disclosed_outside_item_3_01() -> None:
    """Item 3.01 is not where every issuer discloses continued-listing trouble.

    Sampled live EDGAR full-text hits in 8-Ks over the trailing year: of the
    unique 8-Ks containing "regain compliance", 19% carried no Item 3.01; for
    "minimum bid price" 32%; for "Listing Qualifications" 48%. INHD is one such
    issuer - its recent listing disclosures are tagged 5.03/7.01/8.01.
    """
    profile = compute_delisting(DelistingInputs(full_text_deficiency=True))
    assert profile.tier != "none", (
        "a full-text continued-listing deficiency disclosure must register"
    )
    assert any("full-text" in e for e in profile.evidence), (
        f"the evidence must say the signal came from full text: {profile.evidence}"
    )


def test_full_text_deficiency_is_weaker_than_a_tagged_3_01_notice() -> None:
    """Prefer under-detection: a full-text hit is softer evidence than Item 3.01.

    A full-text match can land on a filing announcing that compliance was
    *regained*, so it must not claim the same tier as a tagged 3.01 notice.
    """
    full_text = compute_delisting(DelistingInputs(full_text_deficiency=True))
    tagged = compute_delisting(DelistingInputs(deficiency_notice=True))
    ranks = {"none": 0, "watch": 1, "deficiency": 2, "imminent": 3, "determination": 4}
    assert ranks[full_text.tier] < ranks[tagged.tier], (
        f"full-text tier {full_text.tier!r} must be softer than "
        f"tagged tier {tagged.tier!r}"
    )


def test_full_text_deficiency_does_not_hard_gate() -> None:
    """A full-text signal must never reach the determination hard gate alone."""
    profile = compute_delisting(DelistingInputs(full_text_deficiency=True))
    assert profile.hard_exclude is False


# ---- Defect 4: the share-count series must not mix restatement vintages -----


def _facts_with_both_tags() -> dict[str, Any]:
    """Apple's real pathology, reduced: the us-gaap series mixes vintages.

    ``us-gaap:CommonStockSharesOutstanding`` is restated after a forward split,
    so a 10-K point carries the split-adjusted count while the surrounding 10-Q
    points are as-reported. Differencing that series shows a large "drop" that
    never happened. ``dei:EntityCommonStockSharesOutstanding`` is the cover-page
    "as of" count and is never retroactively restated.
    """

    def rows(*triples: tuple[str, int, str]) -> list[dict[str, Any]]:
        return [{"end": e, "val": v, "filed": f} for e, v, f in triples]

    us_gaap = rows(
        ("2013-06-29", 908_442_000, "2013-07-24"),
        # restated to the post-7:1-split basis when the later 10-K was filed
        ("2013-09-28", 6_294_494_000, "2014-10-27"),
        ("2013-12-28", 892_447_000, "2014-01-28"),
        # the filer's own units error (thousands tagged as shares)
        ("2014-03-29", 861_745, "2014-04-24"),
        ("2014-06-28", 5_989_171_000, "2014-07-23"),
    )
    dei = rows(
        ("2013-06-29", 908_442_000, "2013-07-24"),
        ("2013-09-28", 899_213_000, "2013-10-30"),
        ("2013-12-28", 892_447_000, "2014-01-28"),
        ("2014-03-29", 861_745_000, "2014-04-24"),
        ("2014-06-28", 855_263_000, "2014-07-23"),
    )
    return {
        "facts": {
            "us-gaap": {"CommonStockSharesOutstanding": {"units": {"shares": us_gaap}}},
            "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": dei}}},
        }
    }


def test_share_series_prefers_the_unrestated_cover_page_tag() -> None:
    """The series must come from the tag that is never retroactively restated."""
    series = share_count_series(_facts_with_both_tags())
    values = [p.shares for p in series]
    assert 6_294_494_000 not in values, (
        "series picked the restated us-gaap tag, mixing split-adjusted and "
        f"as-reported vintages: {values}"
    )
    assert 861_745 not in values, f"series carried a units-error point: {values}"


def test_forward_split_issuer_registers_no_reverse_splits() -> None:
    """Apple has never done a reverse split; the detector reported three."""
    splits = detect_reverse_splits(share_count_series(_facts_with_both_tags()))
    assert splits.count == 0, (
        f"reported {splits.count} reverse split(s) for a forward-split-only "
        f"issuer: {[(e.period_end, round(e.ratio, 2)) for e in splits.events]}"
    )
    assert splits.serial is False


def test_implausible_ratio_is_rejected_as_a_data_error() -> None:
    """A 1000x single-period share collapse is a tagging error, not a split."""
    from pennytune.features.dilution import ShareCountPoint

    series = [
        ShareCountPoint("2024-03-31", 892_447_000.0),
        ShareCountPoint("2024-06-30", 861_745.0),  # 1035x - not a real split
        ShareCountPoint("2024-09-30", 870_000.0),
    ]
    splits = detect_reverse_splits(series)
    assert splits.count == 0, (
        f"accepted an implausible ratio as a reverse split: "
        f"{[(e.period_end, round(e.ratio, 2)) for e in splits.events]}"
    )


def test_genuine_reverse_split_is_still_detected() -> None:
    """Guard against over-correcting: a real 1-for-10 must still register."""
    from pennytune.features.dilution import ShareCountPoint

    series = [
        ShareCountPoint("2024-03-31", 20_751_726.0),
        ShareCountPoint("2024-06-30", 20_751_726.0),
        ShareCountPoint("2024-12-31", 2_075_172.0),  # 1-for-10
        ShareCountPoint("2025-03-31", 2_200_000.0),
    ]
    splits = detect_reverse_splits(series)
    assert splits.count == 1, f"missed a genuine reverse split: {splits}"


# ---- Defect 1: Altman Z'' is not applicable to a near-zero-liability filer ---


def _period(**kw: float) -> PeriodFinancials:
    """Only the seven fields Altman Z'' reads; everything else stays None."""
    return PeriodFinancials(**kw)


def test_altman_suppressed_when_equity_to_liabilities_dominates() -> None:
    """INHD's real FY2025 balance sheet, which scored Z'' = 19.61 = "safe".

    X4 (book equity / total liabilities) = 18.09 contributes 18.99 of the 19.61,
    i.e. 96.9% of the score, because liabilities are 5.2% of assets after a
    capital raise. X1+X2+X3 net to +0.62, inside the distress band. The company
    had going-concern doubt "not alleviated" and reverse-split 1-for-24 then
    1-for-20 within five months. Altman's model was fit on leveraged operating
    firms and has no term for "the cushion is large because they just sold
    stock", so the score is an extrapolation outside the fitted region.
    """
    result = altman_z(
        _period(
            total_assets=16_005_383.0,
            total_liabilities=838_656.0,
            book_equity=15_166_727.0,
            retained_earnings=-14_818_007.0,
            ebit=-4_362_473.0,
            current_assets=13_805_383.0,
            current_liabilities=468_110.0,
        )
    )
    assert not result.computable, (
        f"scored an inapplicable balance sheet: value={result.value}, "
        f"flags={result.flags}"
    )
    assert any("applicability" in m for m in result.missing), (
        f"suppression must name the reason: {result.missing}"
    )


def test_altman_still_computed_for_a_profitable_low_leverage_company() -> None:
    """ISRG-shaped control: X4 = 7.08, higher than four suppressed names.

    A naive X4-magnitude gate would suppress this healthy company. It must not:
    retained earnings and EBIT are both positive, so the equity is earned, not
    contributed.
    """
    result = altman_z(
        _period(
            total_assets=20_500_000_000.0,
            total_liabilities=2_521_500_000.0,
            book_equity=17_853_000_000.0,
            retained_earnings=6_970_000_000.0,
            ebit=2_952_000_000.0,
            current_assets=10_000_000_000.0,
            current_liabilities=2_210_000_000.0,
        )
    )
    assert result.computable, "suppressed a profitable, low-leverage large cap"
    assert "zone:safe" in result.flags


def test_altman_verdict_survives_a_high_equity_ratio() -> None:
    """The applicability gate must not withhold a verdict it can still give.

    X4 can only inflate Z'', so a filer whose score is low even after removing
    the X4 contribution is genuinely weak and keeps its verdict rather than
    being suppressed. This fixture (X4 = 7.66, Z'' = -0.37, and -8.41 with the
    X4 term removed) is exactly that case.

    It asserts "not safe" rather than "distress": under the re-anchored bands
    Z'' = -0.37 is grey. That is the known cost of re-anchoring. A couple of
    going-concern filers land in grey rather than distress, which buys back a
    much larger number of healthy large caps wrongly called distressed. None
    move to safe.
    """
    result = altman_z(
        _period(
            total_assets=277_200_000.0,
            total_liabilities=32_155_000.0,
            book_equity=246_200_000.0,
            retained_earnings=-854_800_000.0,
            ebit=-125_800_000.0,
            current_assets=230_000_000.0,
            current_liabilities=31_800_000.0,
        )
    )
    assert result.computable, "the gate withheld a verdict it could still give"
    assert "zone:safe" not in result.flags, (
        f"called a weak balance sheet safe: {result.flags}"
    )
