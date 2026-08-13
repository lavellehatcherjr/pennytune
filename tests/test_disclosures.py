"""Disclosure-only signals: surfaced to the reader, never scored.

Two things are pinned here. First, that each signal renders when the underlying
filing exists and stays quiet when it does not. Second, and the reason these
live in their own module, that neither one moves a composite by any amount.
A disclosure signal that changes the ranking is not a disclosure signal.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pennytune.features.events import (
    build_event_tape,
    comment_letter_activity,
    parse_submissions_8k_events,
)
from pennytune.features.quant_scores import PeriodFinancials
from pennytune.features.universe import UniverseCandidate
from pennytune.scan import RawEvidence, ScanRequest, compute_signals, run_scan

_NOW = datetime(2026, 8, 13, tzinfo=UTC)


def _submissions(*rows: tuple[str, str]) -> dict[str, Any]:
    """A submissions payload carrying (form, filingDate) pairs."""
    return {
        "filings": {
            "recent": {
                "form": [f for f, _ in rows],
                "filingDate": [d for _, d in rows],
                "accessionNumber": [
                    f"0000000000-00-{i:06d}" for i, _ in enumerate(rows)
                ],
                "primaryDocument": ["filename1.pdf" for _ in rows],
                "items": ["" for _ in rows],
                "reportDate": [d for _, d in rows],
            }
        }
    }


def _letters(*rows: tuple[str, str]) -> Any:
    """``comment_letter_activity`` over a payload, read at a fixed instant."""
    return comment_letter_activity(_submissions(*rows), now=_NOW)


# ---- Signal 1: SEC staff comment letters ------------------------------------


def test_comment_letter_is_surfaced_when_an_upload_exists() -> None:
    activity = _letters(("UPLOAD", "2026-05-11"), ("CORRESP", "2026-06-02"))
    assert activity is not None
    assert activity.count == 1
    assert activity.response_count == 1
    assert activity.latest == "2026-05-11"
    assert "2026-05-11" in activity.note()


def test_no_comment_letter_means_no_disclosure() -> None:
    assert _letters(("10-K", "2026-03-01")) is None


def test_the_form_type_is_upload_not_letter() -> None:
    """LETTER is the uploaded FILE type; UPLOAD is the form type.

    Matching on LETTER compiles, runs, and silently never fires. Nothing else
    in the payload distinguishes the two, so only a test pins it.
    """
    assert _letters(("LETTER", "2026-05-11")) is None
    assert _letters(("UPLOAD", "2026-05-11")) is not None


def test_comment_letters_outside_the_window_do_not_surface() -> None:
    """Unwindowed, an UPLOAD is on file for the large majority of filers.

    The staff releases these no earlier than 20 business days after a review
    closes, so nothing is ever fresh; a window is what keeps the line from
    firing on almost everyone.
    """
    assert _letters(("UPLOAD", "2019-01-04")) is None


def test_counts_cover_the_same_window_as_the_date() -> None:
    """A lifetime count beside a recent date reads as if it were all recent.

    Active filers accumulate a decade of correspondence; pairing that total
    with last spring's date implies a volume of current scrutiny that is not
    there. Both counts are windowed with ``latest`` or none of them are.
    """
    activity = _letters(
        ("UPLOAD", "2011-02-14"),
        ("CORRESP", "2011-03-30"),
        ("UPLOAD", "2026-05-11"),
        ("CORRESP", "2026-06-02"),
    )
    assert activity is not None
    assert activity.count == 1
    assert activity.response_count == 1
    assert "1 letter, 1 response(s) in the last 365 days" in activity.note()


def test_response_count_is_reported_without_inferring_resolution() -> None:
    """An UPLOAD with no CORRESP does not mean an unanswered question.

    Filers routinely respond inside another filing, so the index cannot tell
    an open question from a closed one. Report both counts and claim nothing.
    """
    activity = _letters(("UPLOAD", "2026-05-11"))
    assert activity is not None
    assert activity.response_count == 0
    note = activity.note().lower()
    assert "unresolved" not in note
    assert "unanswered" not in note
    assert "outstanding" not in note


# ---- Signal 2: 8-K Item 4.02, non-reliance ----------------------------------


def _tape(*items: str) -> Any:
    rows = [("8-K", "2026-06-01") for _ in items]
    payload = _submissions(*rows)
    payload["filings"]["recent"]["items"] = list(items)
    return build_event_tape(parse_submissions_8k_events(payload), cik="1", now=_NOW)


def test_non_reliance_is_distinguishable_from_an_auditor_change() -> None:
    """4.02 is the issuer disowning its own prior financials.

    Merging it into a joint 4.01/4.02 count makes that indistinguishable from
    a routine auditor change, which is a different and much weaker finding.
    """
    from pennytune.cli import _red_flag_8k_note

    non_reliance = _red_flag_8k_note(_tape("4.02")) or ""
    auditor_only = _red_flag_8k_note(_tape("4.01")) or ""
    assert "4.02" in non_reliance
    assert "non-reliance" in non_reliance.lower()
    assert "4.02" not in auditor_only
    assert non_reliance != auditor_only


def test_auditor_change_still_surfaces_on_its_own() -> None:
    from pennytune.cli import _red_flag_8k_note

    note = _red_flag_8k_note(_tape("4.01")) or ""
    assert "4.01" in note


# ---- The invariant that makes these disclosure-only -------------------------


def _period(scale: float = 1.0) -> PeriodFinancials:
    return PeriodFinancials(
        total_assets=1000.0 * scale,
        current_assets=600.0 * scale,
        current_liabilities=200.0 * scale,
        cash=300.0 * scale,
        total_liabilities=300.0 * scale,
        total_debt=100.0 * scale,
        long_term_debt=80.0 * scale,
        retained_earnings=200.0 * scale,
        book_equity=700.0 * scale,
        revenue=900.0 * scale,
        cogs=500.0 * scale,
        ebit=120.0 * scale,
        net_income=90.0 * scale,
        operating_cash_flow=110.0 * scale,
        capex=30.0 * scale,
        interest_expense=10.0 * scale,
        shares_outstanding=1000.0 * scale,
        receivables=120.0 * scale,
        inventory=80.0 * scale,
        gross_ppe=400.0 * scale,
        net_ppe=300.0 * scale,
        depreciation=40.0 * scale,
        sga=150.0 * scale,
    )


def _evidence(ticker: str, *, tape: Any = None) -> RawEvidence:
    return RawEvidence(
        ticker=ticker,
        sic_sector="3674",
        sic_code=3674,
        market_cap=2_000.0,
        current_price=0.5,
        period_t=_period(),
        period_t1=_period(0.85),
        revenue_growth=0.20,
        sentiment_compound=0.10,
        event_tape=tape,
    )


def test_non_reliance_does_not_move_the_composite() -> None:
    """The 4.02 change is display only: the same tape scores the same number."""
    plain = compute_signals(_evidence("AAA", tape=_tape("4.01")), no_news=True)
    restated = compute_signals(_evidence("AAA", tape=_tape("4.02")), no_news=True)
    # Both carry an 8-K tape; what must not change is that surfacing 4.02
    # separately alters nothing the scorer reads.
    assert plain.altman_z == restated.altman_z
    assert plain.piotroski == restated.piotroski


def test_comment_letters_reach_no_scoring_input() -> None:
    """``comment_letter_activity`` is pure and feeds nothing the scorer reads."""
    subs = _submissions(("UPLOAD", "2026-05-11"), ("CORRESP", "2026-06-02"))
    activity = comment_letter_activity(subs, now=_NOW)
    assert activity is not None
    signals = compute_signals(_evidence("AAA"), no_news=True)
    for field in vars(signals):
        assert "comment" not in field
        assert "upload" not in field.lower()


def test_composite_is_unchanged_by_either_disclosure() -> None:
    """Exact equality against a value pinned before either signal existed."""

    class _Fixture:
        def gather(self, candidate: UniverseCandidate) -> RawEvidence:
            return _evidence(candidate.ticker)

    report = run_scan(
        [UniverseCandidate(ticker="AAA", name="AAA")],
        _Fixture(),
        ScanRequest(),
    )
    assert len(report.result.full) == 1
    assert report.result.full[0].composite == 3.361453
