"""Packaging smoke tests.

The module entry point (``python -m pennytune`` == the ``pennytune`` console
script) launches and runs cache-only - exercising the installed package's entry
point and confirming the disclaimer ships inside it. Runs everywhere, including
in the normal test matrix.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _module(*args: str) -> list[str]:
    return [sys.executable, "-m", "pennytune", *args]


def _isolated_env(tmp_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PENNYTUNE_CONFIG_DIR"] = str(tmp_path / "config")
    env["PENNYTUNE_CACHE_DIR"] = str(tmp_path / "cache")
    env["PENNYTUNE_DATA_DIR"] = str(tmp_path / "data")
    env["NO_COLOR"] = "1"
    return env


# ---- module entry point (always runs) ---------------------------------------


def test_module_entrypoint_version() -> None:
    result = subprocess.run(
        _module("--version"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "PennyTune" in result.stdout


def test_module_entrypoint_disclaimer() -> None:
    result = subprocess.run(
        _module("--disclaimer"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "DISCLAIMER" in result.stdout
    assert "NOT INVESTMENT ADVICE" in result.stdout.upper()


def test_module_entrypoint_scan_offline(tmp_path: Path) -> None:
    env = _isolated_env(tmp_path)
    init = subprocess.run(
        _module(
            "init",
            "--identity",
            "Dana Lee dana@example.com",
            "--i-understand-the-risks",
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=120,
    )
    assert init.returncode == 0, init.stderr
    scan = subprocess.run(
        _module("--offline", "scan"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=120,
    )
    assert scan.returncode == 0, scan.stderr
    # Piped (non-TTY) → the full banner is suppressed; the disclaimer still ships.
    assert "Not investment advice" in scan.stdout
    assert "Tune out the noise." not in scan.stdout  # banner suppressed when piped
