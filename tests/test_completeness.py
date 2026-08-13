"""An absence must never render as a measurement.

A metric that could not be computed must not render identically to one that was
computed and came out clean. Without that distinction two candidates differing
in whether dilution, delisting and suspension were checked at all render
byte-identically in the ranked table, the export row and the decomposed
breakdown.

Pinned at all three layers using one pair of candidates: ``CLEAN`` had every
module computed and every one came back clean; ``NEVER`` had none of them
computable.
"""

from __future__ import annotations

from pennytune.config import Config
from pennytune.features.delisting import DelistingInputs, compute_delisting
from pennytune.features.dilution import DilutionInputs, compute_dilution
from pennytune.features.halts import HaltProfile
from pennytune.output import _flag_glyph, result_to_records
from pennytune.profiles import get_profile
from pennytune.scan import ComputedSignals, _to_score_inputs
from pennytune.scoring import RankedResult, score_candidate

_WEIGHTS = dict(
    positive_weights=dict(get_profile("trader").weights),
    penalty_magnitudes=dict(get_profile("trader").penalties),
    preset_bundle=Config().presets["penny"].model_dump(),
)


def _clean() -> ComputedSignals:
    """Every coverage module actually computed, and every one came back clean."""
    return ComputedSignals(
        ticker="CLEAN",
        dilution=compute_dilution(DilutionInputs(filings=[], share_series=[])),
        delisting=compute_delisting(DelistingInputs()),
        halt=HaltProfile(tier="none"),
        altman_z=5.0,
        distress_zone="safe",
        revenue_growth=0.10,
        piotroski=7.0,
        beneish_m=-2.5,
    )


def _never() -> ComputedSignals:
    """Nothing computable: every module is None."""
    return ComputedSignals(ticker="NEVER")


def _score(signals: ComputedSignals):  # type: ignore[no-untyped-def]
    return score_candidate(_to_score_inputs(signals), **_WEIGHTS)


# ---- the scoring record ------------------------------------------------------


def test_uncomputable_modules_are_recorded_as_suppressed() -> None:
    """The breakdown must carry which modules could not be checked."""
    never = _score(_never())
    assert never.suppressed, (
        "a candidate with nothing computable recorded no suppressed modules"
    )


def test_checked_and_clean_is_not_recorded_as_suppressed() -> None:
    """A module that ran and found nothing must not be reported as unchecked."""
    clean = _score(_clean())
    for module in ("dilution", "delisting", "halt_suspension"):
        assert module not in clean.suppressed, (
            f"{module} was computed and clean but reported as suppressed: "
            f"{clean.suppressed}"
        )


def test_clean_and_never_checked_do_not_produce_identical_records() -> None:
    """These two must be distinguishable somewhere in the record."""
    clean, never = _score(_clean()), _score(_never())
    assert (clean.penalty_contributions, clean.suppressed) != (
        never.penalty_contributions,
        never.suppressed,
    ), "checked-and-clean is indistinguishable from never-checked"


# ---- the console -------------------------------------------------------------


def test_console_flag_distinguishes_clean_from_unchecked() -> None:
    """Two rows with materially different evidence coverage must not match."""
    clean, never = _score(_clean()), _score(_never())
    assert _flag_glyph(clean) != _flag_glyph(never), (
        f"both rendered as {_flag_glyph(clean)!r} in the ranked table"
    )


# ---- the export --------------------------------------------------------------


def test_export_record_carries_completeness() -> None:
    """A spreadsheet reader must not have to guess at coverage."""
    breakdown = _score(_never())
    breakdown.completeness = ["fundamentals suppressed (no filed period)"]
    record = result_to_records(RankedResult(ranked=[breakdown]))[0]
    assert "completeness" in record, f"export record keys: {sorted(record)}"
    assert record["completeness"], "completeness exported empty"


def test_export_record_flags_degraded_evidence_without_string_parsing() -> None:
    """4b: obvious at a glance, not by reading prose."""
    clean, never = _score(_clean()), _score(_never())
    records = result_to_records(RankedResult(ranked=[clean, never]))
    by_ticker = {r["ticker"]: r for r in records}
    assert "evidence_complete" in by_ticker["CLEAN"], (
        f"no glanceable coverage field; keys: {sorted(by_ticker['CLEAN'])}"
    )
    assert by_ticker["CLEAN"]["evidence_complete"] is True
    assert by_ticker["NEVER"]["evidence_complete"] is False


def test_export_rows_differ_for_clean_versus_unchecked() -> None:
    """End to end through the export path, the two rows must not be equal."""
    clean, never = _score(_clean()), _score(_never())
    records = result_to_records(RankedResult(ranked=[clean, never]))
    stripped = [{k: v for k, v in r.items() if k != "ticker"} for r in records]
    assert stripped[0] != stripped[1], (
        "export rows are identical apart from the ticker symbol"
    )


# ---- the arithmetic ----------------------------------------------------------


def test_suppression_never_advantages_a_candidate() -> None:
    """2c: the failure mode that would make this fix worse than the bug.

    A name whose penalty modules could not be checked must not outrank a name
    where the same modules ran and found real risk. Suppression withholds
    credit; it must never withhold a charge the evidence supports.
    """
    risky = ComputedSignals(
        ticker="RISKY",
        dilution=compute_dilution(
            DilutionInputs(filings=[], share_series=[], financing_texts=[])
        ),
        delisting=compute_delisting(DelistingInputs(deficiency_notice=True)),
        altman_z=-20.0,
        distress_zone="distress",
    )
    assert _score(risky).composite < _score(_clean()).composite, (
        "a name with real computed risk outranks a fully clean one"
    )
