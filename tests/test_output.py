"""Output & export tests."""

import json
from pathlib import Path

import pandas as pd

from pennytune.disclaimer import EXPORT_HEADER
from pennytune.output import (
    export,
    read_parquet_disclaimer,
    render_console,
    to_json,
)
from pennytune.scoring import (
    POSITIVE_KEYS,
    Gates,
    Penalty,
    PositiveSubScores,
    RankedResult,
    ScoreInputs,
    rank_candidates,
    score_candidate,
)

_WEIGHTS = {key: 1.0 for key in POSITIVE_KEYS}
_MAGS = {"dilution": 1.0}
_BUNDLE = {"dilution": 1.0}


def _build_result() -> RankedResult:
    aaa = score_candidate(
        ScoreInputs(
            "AAA",
            sic_sector="tech",
            positives=PositiveSubScores(valuation=0.9),
            penalties={"dilution": Penalty(0.5)},
        ),
        positive_weights=_WEIGHTS,
        penalty_magnitudes=_MAGS,
        preset_bundle=_BUNDLE,
    )
    bbb = score_candidate(
        ScoreInputs(
            "BBB", sic_sector="tech", positives=PositiveSubScores(valuation=0.3)
        ),
        positive_weights=_WEIGHTS,
        penalty_magnitudes=_MAGS,
        preset_bundle=_BUNDLE,
    )
    zzz = score_candidate(
        ScoreInputs("ZZZ", sic_sector="bio", gates=Gates(active_suspension=True)),
        positive_weights=_WEIGHTS,
        penalty_magnitudes=_MAGS,
        preset_bundle=_BUNDLE,
    )
    return rank_candidates([aaa, bbb, zzz], top_n=5)


def test_to_json_parses_and_is_clean() -> None:
    payload = json.loads(to_json(_build_result()))
    assert payload["_disclaimer"] == EXPORT_HEADER
    assert len(payload["results"]) == 3  # full set incl. the gated name
    tickers = {r["ticker"] for r in payload["results"]}
    assert tickers == {"AAA", "BBB", "ZZZ"}
    assert "\x1b[" not in to_json(_build_result())  # no ANSI/decoration


def test_export_csv_roundtrip_with_disclaimer(tmp_path: Path) -> None:
    path = export(_build_result(), tmp_path / "scan.csv", "csv")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == EXPORT_HEADER
    frame = pd.read_csv(path, skiprows=1)
    assert "ticker" in frame.columns
    assert len(frame) == 3


def test_export_parquet_roundtrip_with_metadata_disclaimer(tmp_path: Path) -> None:
    path = export(_build_result(), tmp_path / "scan.parquet", "parquet")
    frame = pd.read_parquet(path)
    assert len(frame) == 3
    assert read_parquet_disclaimer(path) == EXPORT_HEADER


def test_export_json_roundtrip(tmp_path: Path) -> None:
    path = export(_build_result(), tmp_path / "scan.json", "json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["_disclaimer"] == EXPORT_HEADER
    assert len(payload["results"]) == 3


def test_export_markdown(tmp_path: Path) -> None:
    path = export(_build_result(), tmp_path / "scan.md", "markdown")
    text = path.read_text(encoding="utf-8")
    assert text.startswith(EXPORT_HEADER)
    assert "| ticker |" in text
    assert "AAA" in text


def test_render_console_no_color_is_plain_text() -> None:
    out = render_console(_build_result(), no_color=True)
    assert "\x1b[" not in out  # no ANSI escapes when color is disabled
    assert "AAA" in out
    assert "Research and educational tool only" in out  # short disclaimer footer


def test_render_console_shows_high_risk_section() -> None:
    out = render_console(_build_result(), no_color=True)
    assert "HIGH-RISK" in out
    assert "ZZZ" in out  # the gated name is surfaced, not silently dropped
