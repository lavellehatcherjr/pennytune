"""Output & export - how ranked results leave the tool.

How results leave the tool: a colored, glyph-annotated Rich console table; the
full ranked set exported to CSV/Parquet/JSON/Markdown; and a clean
machine-readable JSON mode for piping. The short-form disclaimer ends every
ranked console output, and the one-line disclaimer header travels inside every
exported file (in Parquet via schema metadata). Color always reinforces a
glyph ([X]/[!]/[+]/[~]) - never the sole signal - and is removed under
``--no-color`` / ``NO_COLOR`` / non-TTY.
"""

from __future__ import annotations

import io
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from pennytune.disclaimer import EXPORT_HEADER, SHORT_DISCLAIMER
from pennytune.scoring import RankedResult, ScoreBreakdown

__all__ = [
    "result_to_records",
    "to_json",
    "render_console",
    "export",
    "read_parquet_disclaimer",
]

# Penalty modules that are critical (red) vs caution (yellow) for the flag glyph.
_CRITICAL_MODULES = frozenset(
    {"delisting", "distress", "manipulation", "beneish", "halt_suspension"}
)


def result_to_records(result: RankedResult) -> list[dict[str, Any]]:
    """Flatten the full ranked set (ranked + high-risk) into export records."""
    records: list[dict[str, Any]] = []
    for breakdown in result.full:
        rank = result.sector_ranks.get(breakdown.ticker)
        records.append(
            {
                "ticker": breakdown.ticker,
                "composite": round(breakdown.composite, 4),
                "sic_sector": breakdown.sic_sector,
                "sector_rank": rank[0] if rank else None,
                "sector_size": rank[1] if rank else None,
                "gated": breakdown.gated,
                "gate_reasons": list(breakdown.gate_reasons),
                "penalty_flags": sorted(breakdown.penalty_contributions),
                "na_modules": list(breakdown.na_modules),
                "positive_contributions": {
                    k: round(v, 4) for k, v in breakdown.positive_contributions.items()
                },
                "penalty_contributions": {
                    k: round(v, 4) for k, v in breakdown.penalty_contributions.items()
                },
                "notes": list(breakdown.notes),
            }
        )
    return records


def to_json(result: RankedResult, *, attributions: Sequence[str] = ()) -> str:
    """Clean machine-readable JSON for ``--json`` (no banner/decoration).

    Contains no secrets (results hold no identity/credentials). The one-line
    disclaimer travels as ``_disclaimer``; mandatory source credits (e.g. the
    mandatory GDELT attribution) travel as ``_attributions``.
    """
    payload: dict[str, Any] = {
        "_disclaimer": EXPORT_HEADER,
        "results": result_to_records(result),
    }
    if attributions:
        payload["_attributions"] = list(attributions)
    return json.dumps(payload, indent=2, default=str)


def _flag_glyph(breakdown: ScoreBreakdown) -> tuple[str, str]:
    """Return (glyph-prefixed flag text, color style) for the console row."""
    if breakdown.gated:
        return f"[X] excluded: {'; '.join(breakdown.gate_reasons)}", "red"
    penalties = set(breakdown.penalty_contributions)
    if penalties & _CRITICAL_MODULES:
        return f"[X] {', '.join(sorted(penalties))}", "red"
    if penalties:
        return f"[!] {', '.join(sorted(penalties))}", "yellow"
    return "-", ""


def render_console(
    result: RankedResult,
    *,
    no_color: bool = False,
    quiet: bool = False,
    top_only: bool = True,
) -> str:
    """Render the ranked table + short disclaimer to a string (Rich)."""
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    buffer = io.StringIO()
    console = Console(
        file=buffer,
        no_color=no_color,
        force_terminal=not no_color,
        width=120,
        highlight=False,
    )
    table = Table(
        title=None if quiet else "PennyTune — ranked candidates", expand=False
    )
    for column in ("Rank", "Ticker", "Score", "Sector", "Flags"):
        table.add_column(column)
    rows = result.top if top_only else result.ranked
    for position, breakdown in enumerate(rows, start=1):
        flag_text, style = _flag_glyph(breakdown)
        table.add_row(
            str(position),
            breakdown.ticker,
            f"{breakdown.composite:.1f}",
            breakdown.sic_sector,
            Text(flag_text, style=style),
        )
    console.print(table)

    if result.high_risk and not quiet:
        console.print("── HIGH-RISK / EXCLUDED ──")
        for breakdown in result.high_risk:
            console.print(
                Text(
                    f"[X] {breakdown.ticker}: {'; '.join(breakdown.gate_reasons)}",
                    style="red",
                )
            )

    console.print(SHORT_DISCLAIMER)
    return buffer.getvalue()


def _tabular_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Build a tabular DataFrame, JSON-stringifying dict/list columns."""
    flat: list[dict[str, Any]] = []
    for record in records:
        row = {
            key: (json.dumps(value) if isinstance(value, dict | list) else value)
            for key, value in record.items()
        }
        flat.append(row)
    return pd.DataFrame(flat)


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def export(
    result: RankedResult,
    path: Path,
    fmt: str,
    *,
    attributions: Sequence[str] = (),
) -> Path:
    """Export the FULL ranked set with the one-line disclaimer header.

    Mandatory source credits (``attributions`` - e.g. the mandatory GDELT
    attribution when a result used GDELT coverage) travel inside every format: a
    comment line in CSV/Markdown, ``_attributions`` in JSON, schema metadata in
    Parquet.
    """
    records = result_to_records(result)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        path.write_text(to_json(result, attributions=attributions), encoding="utf-8")
        return path

    frame = _tabular_frame(records)
    if fmt == "csv":
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(EXPORT_HEADER + "\n")
            for attribution in attributions:
                handle.write(f"# {attribution}\n")
            frame.to_csv(handle, index=False)
    elif fmt == "markdown":
        with path.open("w", encoding="utf-8") as handle:
            handle.write(EXPORT_HEADER + "\n\n")
            for attribution in attributions:
                handle.write(f"> {attribution}\n\n")
            handle.write(_markdown_table(frame) + "\n")
    elif fmt == "parquet":
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pa.Table.from_pandas(frame, preserve_index=False)
        metadata = dict(table.schema.metadata or {})
        metadata[b"disclaimer"] = EXPORT_HEADER.encode("utf-8")
        if attributions:
            metadata[b"attributions"] = "\n".join(attributions).encode("utf-8")
        table = table.replace_schema_metadata(metadata)
        pq.write_table(table, path)
    else:
        raise ValueError(f"unknown export format: {fmt!r}")
    return path


def read_parquet_disclaimer(path: Path) -> str | None:
    """Read the disclaimer back from a Parquet file's schema metadata."""
    import pyarrow.parquet as pq

    metadata = pq.read_schema(path).metadata or {}
    raw = metadata.get(b"disclaimer")
    return raw.decode("utf-8") if raw is not None else None
