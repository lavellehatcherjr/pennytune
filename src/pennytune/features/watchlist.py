"""Watchlist & change-tracking.

A persistent list of tickers the user cares about, with run-over-run change
detection - turning periodic scans into an early-warning system. Stored in
local SQLite (the app-state layer); each scan records a per-ticker snapshot
(score + flags), and deltas (score change, newly-triggered/cleared flags) are
computed against the prior snapshot. Material new flags or a sharp score drop
raise an alert that surfaces at the top of the next scan.

The delta logic (:func:`diff_snapshots`) is a pure function, independently
testable without the database.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pennytune import paths

__all__ = [
    "MATERIAL_ALERT_FLAGS",
    "SCORE_ALERT_DROP",
    "Snapshot",
    "SnapshotDiff",
    "WatchEntry",
    "diff_snapshots",
    "Watchlist",
]

# New appearance of any of these flags raises a watchlist alert.
MATERIAL_ALERT_FLAGS = frozenset(
    {
        "DILUTION-HIGH",
        "DILUTION-SHELF-LARGE",
        "ACTIVE-ATM",
        "TOXIC-FINANCING",
        "SERIAL-SPLITTER",
        "OVERHANG-HIGH",
        "DELISTING-DEFICIENCY",
        "DELISTING-DETERMINATION",
        "PRICE-SUB-10C",
        "SEC-SUSPENSION",
        "HALTED",
        "RESTATEMENT",
        "NT-RESTATEMENT",
        "GOING-CONCERN",
        "MANIPULATION-HIGH",
    }
)
SCORE_ALERT_DROP = 10.0  # a score drop of this magnitude raises an alert


@dataclass
class Snapshot:
    ticker: str
    scanned_at: str
    score: float | None
    flags: list[str] = field(default_factory=list)


@dataclass
class SnapshotDiff:
    score_delta: float | None = None
    new_flags: list[str] = field(default_factory=list)
    cleared_flags: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)

    @property
    def is_alert(self) -> bool:
        return bool(self.alerts)


@dataclass
class WatchEntry:
    ticker: str
    added_at: str
    last_score: float | None = None
    score_delta: float | None = None
    alerts: list[str] = field(default_factory=list)


def diff_snapshots(prior: Snapshot | None, current: Snapshot) -> SnapshotDiff:
    """Compare two snapshots → score delta, new/cleared flags, and alerts.

    A first-ever snapshot (no prior) is a baseline: no deltas, no alerts.
    """
    if prior is None:
        return SnapshotDiff()  # baseline set, no deltas
    prior_flags = set(prior.flags)
    current_flags = set(current.flags)
    new_flags = [f for f in current.flags if f not in prior_flags]
    cleared_flags = [f for f in prior.flags if f not in current_flags]
    delta = (
        current.score - prior.score
        if (current.score is not None and prior.score is not None)
        else None
    )
    alerts: list[str] = []
    for flag in new_flags:
        if flag in MATERIAL_ALERT_FLAGS:
            alerts.append(f"new flag {flag}")
    if delta is not None and delta <= -SCORE_ALERT_DROP:
        alerts.append(f"score {delta:+.0f}")
    return SnapshotDiff(
        score_delta=delta,
        new_flags=new_flags,
        cleared_flags=cleared_flags,
        alerts=alerts,
    )


def _now(now: datetime | None) -> str:
    return (now if now is not None else datetime.now(UTC)).isoformat()


class Watchlist:
    """SQLite-backed watchlist + per-scan snapshot store."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (paths.data_dir() / "pennytune.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS watchlist "
            "(ticker TEXT PRIMARY KEY, added_at TEXT NOT NULL)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS snapshots ("
            " ticker TEXT NOT NULL, scanned_at TEXT NOT NULL, score REAL, flags TEXT,"
            " PRIMARY KEY (ticker, scanned_at))"
        )
        self._conn.commit()

    def add(self, tickers: list[str], *, now: datetime | None = None) -> list[str]:
        stamp = _now(now)
        added: list[str] = []
        for raw in tickers:
            ticker = raw.strip().upper()
            if not ticker:
                continue
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO watchlist (ticker, added_at) VALUES (?, ?)",
                [ticker, stamp],
            )
            if cursor.rowcount:
                added.append(ticker)
        self._conn.commit()
        return added

    def remove(self, tickers: list[str]) -> list[str]:
        removed: list[str] = []
        for raw in tickers:
            ticker = raw.strip().upper()
            cursor = self._conn.execute(
                "DELETE FROM watchlist WHERE ticker = ?", [ticker]
            )
            if cursor.rowcount:
                removed.append(ticker)
        self._conn.commit()
        return removed

    def list_tickers(self) -> list[tuple[str, str]]:
        rows = self._conn.execute(
            "SELECT ticker, added_at FROM watchlist ORDER BY added_at, ticker"
        ).fetchall()
        return [(row[0], row[1]) for row in rows]

    def is_watched(self, ticker: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM watchlist WHERE ticker = ?", [ticker.strip().upper()]
        ).fetchone()
        return row is not None

    def record_snapshot(
        self,
        ticker: str,
        score: float | None,
        flags: list[str],
        *,
        now: datetime | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO snapshots "
            "(ticker, scanned_at, score, flags) VALUES (?, ?, ?, ?)",
            [ticker.strip().upper(), _now(now), score, json.dumps(flags)],
        )
        self._conn.commit()

    def latest_two(self, ticker: str) -> tuple[Snapshot | None, Snapshot | None]:
        rows = self._conn.execute(
            "SELECT ticker, scanned_at, score, flags FROM snapshots "
            "WHERE ticker = ? ORDER BY scanned_at DESC LIMIT 2",
            [ticker.strip().upper()],
        ).fetchall()
        snaps = [
            Snapshot(r[0], r[1], r[2], json.loads(r[3]) if r[3] else []) for r in rows
        ]
        latest = snaps[0] if snaps else None
        prior = snaps[1] if len(snaps) > 1 else None
        return latest, prior

    def list_entries(self) -> list[WatchEntry]:
        entries: list[WatchEntry] = []
        for ticker, added_at in self.list_tickers():
            latest, prior = self.latest_two(ticker)
            diff = (
                diff_snapshots(prior, latest) if latest is not None else SnapshotDiff()
            )
            entries.append(
                WatchEntry(
                    ticker=ticker,
                    added_at=added_at,
                    last_score=latest.score if latest else None,
                    score_delta=diff.score_delta,
                    alerts=diff.alerts,
                )
            )
        return entries

    def alerts(self) -> list[str]:
        messages: list[str] = []
        for entry in self.list_entries():
            for alert in entry.alerts:
                messages.append(f"{entry.ticker}: {alert}")
        return messages

    def close(self) -> None:
        self._conn.close()
