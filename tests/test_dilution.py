"""Dilution & corporate-action-risk tests. Fixtures only, no network."""

from typing import Any

import pytest

from pennytune.features.dilution import (
    CoverPageFacts,
    DilutionInputs,
    EdgarDilutionProvider,
    FilingRef,
    ShareCountPoint,
    auditor_flags,
    authorized_headroom,
    build_filing_refs,
    compute_dilution,
    detect_nt_late_filing,
    detect_offering_activity,
    detect_reverse_splits,
    detect_shelves,
    detect_toxic_financing,
    dilution_velocity,
    fully_diluted_overhang,
    parse_efts_hits,
    parse_submissions_sic,
    share_count_series,
    shelf_utilization,
    shell_composite,
)
from pennytune.features.events import build_event, build_event_tape


def _tape(*items: str) -> Any:
    return build_event_tape(
        [build_event(str(i), "2026-01-01", "8-K", item) for i, item in enumerate(items)]
    )


# ---- shelves / offerings / utilization --------------------------------------


def test_detect_shelves_size_to_market_cap() -> None:
    shelf = detect_shelves(
        [FilingRef("S-3", "2026-03-11", "a1", offering_amount=75_000_000)],
        market_cap=40_000_000,
    )
    assert shelf.present
    assert shelf.max_amount == 75_000_000
    assert shelf.pct_of_market_cap == pytest.approx(187.5)


def test_active_atm_detection() -> None:
    drip = detect_offering_activity(
        [FilingRef("424B3", "2026-05-01", "a"), FilingRef("424B3", "2026-05-20", "b")]
    )
    assert drip.active_atm is True
    single = detect_offering_activity([FilingRef("424B3", "2026-05-01", "a")])
    assert single.active_atm is False


def test_shelf_utilization_math() -> None:
    util = shelf_utilization(75_000_000, [30_000_000, 18_000_000])
    assert util.drawn == 48_000_000
    assert util.remaining == 27_000_000
    assert util.pct_drawn == pytest.approx(64.0)


def test_toxic_financing_language() -> None:
    toxic = detect_toxic_financing(
        [
            "beneficial ownership limitation; "
            "variable rate conversion on a convertible note"
        ]
    )
    assert toxic.present is True
    assert "beneficial ownership limitation" in toxic.terms
    assert "variable rate" in toxic.terms


# ---- dilution velocity ------------------------------------------------------


def test_dilution_velocity_accelerating_death_spiral() -> None:
    series = [
        ShareCountPoint("2024-09-30", 5_000_000),
        ShareCountPoint("2025-03-31", 10_000_000),
        ShareCountPoint("2025-06-30", 13_000_000),
        ShareCountPoint("2025-09-30", 18_000_000),
    ]
    vel = dilution_velocity(series)
    assert vel.qoq == pytest.approx((18 - 13) / 13)
    assert vel.yoy == pytest.approx((18 - 5) / 5)
    assert vel.trend == "accelerating"
    assert vel.death_spiral is True


def test_dilution_velocity_decelerating_not_death_spiral() -> None:
    series = [
        ShareCountPoint("2025-03-31", 10_000_000),
        ShareCountPoint("2025-06-30", 13_000_000),
        ShareCountPoint("2025-09-30", 14_000_000),
    ]
    vel = dilution_velocity(series)
    assert vel.trend == "decelerating"
    assert vel.death_spiral is False


# ---- authorized headroom / overhang -----------------------------------------


def test_authorized_headroom_and_increase_event() -> None:
    headroom = authorized_headroom(100_000_000, 95_000_000, _tape("5.03"))
    assert headroom.headroom_pct == pytest.approx(5.0)
    assert headroom.near_ceiling is True
    assert headroom.authorized_increase_event is True


def test_fully_diluted_overhang() -> None:
    over = fully_diluted_overhang(
        50_000_000,
        warrants=30_000_000,
        options=10_000_000,
        convertibles=60_000_000,
        remaining_shelf_shares=50_000_000,
        float_shares=50_000_000,
    )
    assert over.overhang_pct == pytest.approx(300.0)  # 150M extra / 50M float
    assert over.partial is False


def test_overhang_partial_when_component_missing() -> None:
    over = fully_diluted_overhang(50_000_000, warrants=10_000_000, convertibles=None)
    assert over.partial is True


# ---- reverse splits ---------------------------------------------------------


def test_serial_reverse_split_counting() -> None:
    series = [
        ShareCountPoint("2022-12-31", 100_000_000),
        ShareCountPoint("2023-06-30", 10_000_000),  # 1-for-10
        ShareCountPoint("2023-12-31", 30_000_000),  # re-dilution after
        ShareCountPoint("2024-12-31", 6_000_000),  # 1-for-5
    ]
    splits = detect_reverse_splits(series)
    assert splits.count == 2
    assert splits.serial is True
    assert splits.since_year == "2023"
    assert splits.cumulative_ratio == pytest.approx(50.0)


def test_no_reverse_split_on_growth() -> None:
    series = [
        ShareCountPoint("2025-03-31", 10_000_000),
        ShareCountPoint("2025-06-30", 13_000_000),
    ]
    assert detect_reverse_splits(series).count == 0


# ---- auditor / NT / shell ---------------------------------------------------


def test_auditor_change_and_restatement() -> None:
    flags = auditor_flags(
        CoverPageFacts(auditor_name="Tiny LLP"), _tape("4.01", "4.01", "4.02")
    )
    assert flags.auditor_change is True
    assert flags.restatement is True
    assert flags.repeated_auditor_changes is True
    assert flags.auditor_name == "Tiny LLP"


def test_nt_late_filing_and_restatement_escalation() -> None:
    plain = detect_nt_late_filing([FilingRef("NT 10-K", "2026-04-01", "n1")])
    assert plain.present is True
    assert plain.escalated is False
    escalated = detect_nt_late_filing(
        [
            FilingRef(
                "NT 10-Q",
                "2026-05-01",
                "n2",
                text="delayed due to an anticipated restatement",
            )
        ]
    )
    assert escalated.escalated is True


def test_shell_composite() -> None:
    shell = shell_composite(
        CoverPageFacts(is_shell=True, employees=2),
        _tape("5.06"),
        revenue=0,
        shares=80_000_000,
    )
    assert shell.is_shell_arc is True
    assert shell.signal_count >= 2


# ---- parsers ----------------------------------------------------------------


def test_build_filing_refs() -> None:
    submissions: dict[str, Any] = {
        "filings": {
            "recent": {
                "form": ["S-3", "424B5", "10-Q"],
                "accessionNumber": ["0001", "0002", "0003"],
                "filingDate": ["2026-03-11", "2026-04-02", "2026-05-08"],
            }
        }
    }
    refs = build_filing_refs(submissions)
    assert [r.form for r in refs] == ["S-3", "424B5", "10-Q"]
    assert refs[0].accession == "0001"


def test_share_count_series() -> None:
    facts: dict[str, Any] = {
        "facts": {
            "us-gaap": {
                "CommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {
                                "end": "2025-06-30",
                                "val": 13_000_000,
                                "filed": "2025-08-01",
                            },
                            {
                                "end": "2025-03-31",
                                "val": 10_000_000,
                                "filed": "2025-05-01",
                            },
                        ]
                    }
                }
            }
        }
    }
    series = share_count_series(facts)
    assert [p.period_end for p in series] == ["2025-03-31", "2025-06-30"]
    assert series[-1].shares == 13_000_000


def test_parse_efts_hits() -> None:
    # Real efts.sec.gov shape (confirmed live): the form is in ``form``/
    # ``root_forms``; ``file_type`` is the *exhibit* type (never the form); the
    # accession is ``adsh`` and also prefixes ``_id``.
    payload: dict[str, Any] = {
        "hits": {
            "hits": [
                {
                    "_id": "0001234-26-000123:ex99.htm",
                    "_source": {
                        "form": "424B5",
                        "root_forms": ["424B5"],
                        "file_type": "EX-99.1",  # exhibit type, must NOT win
                        "file_date": "2026-04-02",
                        "adsh": "0001234-26-000123",
                    },
                },
                {  # fallback: no ``form`` → use ``root_forms[0]``; accession from _id
                    "_id": "0009999-26-000777:d.htm",
                    "_source": {
                        "root_forms": ["8-K"],
                        "file_type": "EX-10.1",
                        "file_date": "2026-04-05",
                    },
                },
            ]
        }
    }
    refs = parse_efts_hits(payload)
    assert len(refs) == 2
    assert refs[0].form == "424B5"  # the real form, not the EX-99.1 exhibit type
    assert refs[0].filing_date == "2026-04-02"
    assert refs[0].accession == "0001234-26-000123"  # from adsh
    assert refs[1].form == "8-K"  # root_forms fallback
    assert refs[1].accession == "0009999-26-000777"  # from _id prefix


# ---- composite --------------------------------------------------------------


def _high_risk_inputs(*, insider_buying: bool = False) -> DilutionInputs:
    return DilutionInputs(
        filings=[
            FilingRef("S-3", "2026-03-11", "s1", offering_amount=75_000_000),
            FilingRef("424B3", "2026-05-01", "b1"),
            FilingRef("424B3", "2026-05-20", "b2"),
        ],
        share_series=[
            ShareCountPoint("2025-03-31", 10_000_000),
            ShareCountPoint("2025-06-30", 14_000_000),
            ShareCountPoint("2025-09-30", 20_000_000),
        ],
        market_cap=40_000_000,
        financing_texts=[
            "convertible note with beneficial ownership limitation and variable rate"
        ],
        insider_buying=insider_buying,
    )


def test_compute_dilution_high_risk() -> None:
    profile = compute_dilution(_high_risk_inputs())
    assert profile.severity == "high"
    assert {
        "DILUTION-SHELF-LARGE",
        "ACTIVE-ATM",
        "TOXIC-FINANCING",
        "DILUTION-VELOCITY-HIGH",
    } <= set(profile.flags)
    assert profile.shelf.pct_of_market_cap == pytest.approx(187.5)
    assert profile.score == 70


def test_compute_dilution_insider_buying_softens() -> None:
    profile = compute_dilution(_high_risk_inputs(insider_buying=True))
    assert profile.insider_buying_offset is True
    assert profile.score == 60  # 70 - 10 offset


def test_compute_dilution_clean() -> None:
    clean = DilutionInputs(
        filings=[FilingRef("10-K", "2026-02-01", "x")],
        share_series=[
            ShareCountPoint("2025-03-31", 10_000_000),
            ShareCountPoint("2025-06-30", 10_000_000),
        ],
        market_cap=40_000_000,
    )
    profile = compute_dilution(clean)
    assert profile.severity == "none"
    assert profile.flags == []


# ---- SIC + the live assembler (submissions + companyfacts + EFTS) -----------


def test_parse_submissions_sic() -> None:
    assert parse_submissions_sic(
        {"sic": "6282", "sicDescription": "Investment Advice"}
    ) == (6282, "Investment Advice")
    # description missing but code present → falls back to the code string
    assert parse_submissions_sic({"sic": "1234"}) == (1234, "1234")
    # no SIC at all → suppressed, not imputed
    assert parse_submissions_sic({}) == (None, "")
    assert parse_submissions_sic({"sic": "", "sicDescription": ""}) == (None, "")
    # non-numeric SIC → code suppressed, description preserved
    assert parse_submissions_sic({"sic": "N/A", "sicDescription": "X"}) == (None, "X")


class _FakeClient:
    """Routes get_json by URL to canned submissions / EFTS payloads."""

    def __init__(self, submissions: Any, efts: Any) -> None:
        self._submissions = submissions
        self._efts = efts

    def get_json(self, url: str, **kwargs: Any) -> Any:
        if "submissions" in url:
            if isinstance(self._submissions, Exception):
                raise self._submissions
            return self._submissions
        if "search-index" in url:
            return self._efts
        raise AssertionError(f"unexpected URL {url}")


_SHARES_CF: dict[str, Any] = {
    "facts": {
        "us-gaap": {
            "CommonStockSharesOutstanding": {
                "units": {
                    "shares": [
                        {"end": "2025-06-30", "val": 10_000_000, "filed": "2025-08-01"},
                        {"end": "2025-09-30", "val": 14_000_000, "filed": "2025-11-01"},
                    ]
                }
            }
        }
    }
}


def test_get_dilution_evidence_assembles_inputs_and_sic() -> None:
    submissions = {
        "sic": "2836",
        "sicDescription": "Biological Products",
        "filings": {
            "recent": {
                "form": ["S-3", "424B5", "424B5", "8-K"],
                "filingDate": ["2026-01-02", "2026-03-01", "2026-04-01", "2026-04-02"],
                "accessionNumber": ["a1", "b1", "b2", "c1"],
            }
        },
    }
    efts = {  # one hit for the toxic phrase → toxic-financing present
        "hits": {
            "hits": [
                {
                    "_id": "0000000001-26-000001:p.htm",
                    "_source": {
                        "form": "424B5",
                        "file_date": "2026-03-01",
                        "adsh": "b1",
                    },
                }
            ],
            "total": {"value": 1},
        }
    }
    provider = EdgarDilutionProvider(_FakeClient(submissions, efts))  # type: ignore[arg-type]
    ev = provider.get_dilution_evidence(
        "0000000001",
        companyfacts=_SHARES_CF,
        submissions=submissions,  # shared by the live provider, not re-fetched
        revenue=500_000,
    )
    assert ev.sic_code == 2836 and ev.sic_sector == "Biological Products"
    assert ev.inputs is not None
    assert [f.form for f in ev.inputs.filings] == ["S-3", "424B5", "424B5", "8-K"]
    assert len(ev.inputs.share_series) == 2  # from the passed companyfacts
    assert ev.inputs.financing_texts == [EdgarDilutionProvider.TOXIC_EFTS_PHRASE]
    # the assembled inputs compute a real, flagged dilution profile
    profile = compute_dilution(ev.inputs)
    assert profile.shelf.present  # S-3 shelf
    assert profile.velocity.death_spiral  # +40% QoQ share growth
    assert profile.toxic.present  # EFTS-derived toxic-financing language
    assert profile.severity in {"medium", "high"}


def test_get_dilution_evidence_degrades_submissions_keeps_share_series() -> None:
    # submissions unavailable (the shared fetch failed) → filings + SIC
    # suppressed and flagged, but the companyfacts-derived share series
    # (velocity/splits) still computes.
    provider = EdgarDilutionProvider(
        _FakeClient(None, {"hits": {"hits": []}})  # type: ignore[arg-type]
    )
    ev = provider.get_dilution_evidence(
        "0000000009", companyfacts=_SHARES_CF, submissions=None
    )
    assert ev.sic_code is None and ev.sic_sector == ""
    assert ev.inputs is not None and ev.inputs.filings == []
    assert len(ev.inputs.share_series) == 2  # survives the submissions failure
    assert any("submissions" in note for note in ev.completeness)


# ---- 8-K event tape: dilution un-gate + 3.01 no-double-count -----------------


def test_event_tape_ungates_auditor_change_and_restatement() -> None:
    # Without an event tape the 8-K-driven detections stay suppressed.
    base = DilutionInputs(share_series=[ShareCountPoint("2025-12-31", 10_000_000)])
    assert "RESTATEMENT" not in compute_dilution(base).flags
    assert "AUDITOR-CHURN" not in compute_dilution(base).flags
    # A 4.02 (restatement) + two 4.01 (auditor change) 8-Ks un-gate the dilution
    # auditor/restatement detections.
    tape = build_event_tape(
        [
            build_event("a1", "2026-05-01", "8-K", "4.02"),
            build_event("a2", "2026-04-01", "8-K", "4.01"),
            build_event("a3", "2026-03-01", "8-K", "4.01"),
        ]
    )
    ungated = compute_dilution(
        DilutionInputs(event_tape=tape, share_series=base.share_series)
    )
    assert "RESTATEMENT" in ungated.flags  # 4.02 un-gated
    assert "AUDITOR-CHURN" in ungated.flags  # 2 × 4.01 → repeated changes
    assert ungated.score > compute_dilution(base).score


def test_8k_item_301_does_not_feed_dilution_no_double_count() -> None:
    # 3.01 (delisting deficiency) is consumed by the DELISTING module only; it
    # must NOT add to the dilution score (no double-penalty for the same item).
    base = DilutionInputs(share_series=[ShareCountPoint("2025-12-31", 10_000_000)])
    tape = build_event_tape([build_event("a1", "2026-05-01", "8-K", "3.01,9.01")])
    with_301 = DilutionInputs(event_tape=tape, share_series=base.share_series)
    assert compute_dilution(with_301).score == compute_dilution(base).score
    assert "RESTATEMENT" not in compute_dilution(with_301).flags
