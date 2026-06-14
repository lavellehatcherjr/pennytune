"""Watchlist & change-tracking tests."""

from datetime import datetime
from pathlib import Path

from pennytune.features.watchlist import Snapshot, Watchlist, diff_snapshots


def test_add_list_remove_persistence(tmp_path: Path) -> None:
    wl = Watchlist(tmp_path / "db.sqlite")
    assert wl.add(["grow", "nukk", "ocgn"]) == ["GROW", "NUKK", "OCGN"]
    assert {t for t, _ in wl.list_tickers()} == {"GROW", "NUKK", "OCGN"}
    assert wl.add(["grow"]) == []  # idempotent
    assert len(wl.list_tickers()) == 3
    assert wl.remove(["VRMX", "NUKK"]) == ["NUKK"]  # only the present one
    assert {t for t, _ in wl.list_tickers()} == {"GROW", "OCGN"}
    wl.close()


def test_diff_new_material_flag_and_score_drop() -> None:
    prior = Snapshot("VRMX", "2026-05-12T00:00:00", 73, [])
    current = Snapshot("VRMX", "2026-06-12T00:00:00", 61, ["DILUTION-HIGH"])
    diff = diff_snapshots(prior, current)
    assert diff.score_delta == -12
    assert "DILUTION-HIGH" in diff.new_flags
    assert diff.is_alert
    assert any("DILUTION-HIGH" in a for a in diff.alerts)
    assert any("score -12" in a for a in diff.alerts)


def test_diff_baseline_has_no_alerts() -> None:
    diff = diff_snapshots(None, Snapshot("X", "t", 70, ["DILUTION-HIGH"]))
    assert diff.score_delta is None
    assert diff.alerts == []
    assert diff.is_alert is False


def test_diff_minor_change_no_alert() -> None:
    prior = Snapshot("X", "t1", 70, [])
    current = Snapshot("X", "t2", 69, ["minor-note"])  # not material, delta -1
    diff = diff_snapshots(prior, current)
    assert "minor-note" in diff.new_flags
    assert diff.is_alert is False


def test_record_snapshots_and_alert_banner(tmp_path: Path) -> None:
    wl = Watchlist(tmp_path / "db.sqlite")
    wl.add(["VRMX"])
    wl.record_snapshot("VRMX", 73, [], now=datetime(2026, 5, 12))
    wl.record_snapshot("VRMX", 61, ["DILUTION-HIGH"], now=datetime(2026, 6, 12))
    entry = next(e for e in wl.list_entries() if e.ticker == "VRMX")
    assert entry.last_score == 61
    assert entry.score_delta == -12
    assert entry.alerts
    assert any("VRMX" in a and "DILUTION-HIGH" in a for a in wl.alerts())
    wl.close()
