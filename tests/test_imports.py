"""Smoke tests for the package scaffold.

These assert the package imports cleanly and the core public objects exist -
the CLI app, the exit-code enum, and the three disclaimer constants.
"""

import re

import typer

import pennytune
from pennytune.cli import app
from pennytune.disclaimer import EXPORT_HEADER, FULL_DISCLAIMER, SHORT_DISCLAIMER
from pennytune.exit_codes import ExitCode


def test_package_version() -> None:
    # Shape only. Pinning the literal makes every release edit this test, which
    # is the edit that hides a drift. The exact match against pyproject.toml
    # lives in test_packaging.py.
    assert re.fullmatch(r"\d+\.\d+\.\d+", pennytune.__version__)


def test_cli_app_exists() -> None:
    assert app is not None
    assert isinstance(app, typer.Typer)


def test_exit_codes() -> None:
    # Compare the underlying int values of the exit-code contract. Using
    # ``.value`` keeps the comparison int-vs-int, which mypy's
    # strict_equality accepts.
    assert ExitCode.SUCCESS.value == 0
    assert ExitCode.PARTIAL_FAILURE.value == 1
    assert ExitCode.USAGE_ERROR.value == 2
    assert ExitCode.CONFIG_ERROR.value == 3
    assert ExitCode.NO_NETWORK_NO_CACHE.value == 4
    assert ExitCode.INTERRUPTED.value == 5


def test_disclaimer_constants_present() -> None:
    # Full disclaimer must carry the header and the final acceptance clause
    # verbatim and must not be abridged.
    assert FULL_DISCLAIMER.startswith("DISCLAIMER — PLEASE READ CAREFULLY")
    assert "14. ACCEPTANCE." in FULL_DISCLAIMER
    assert FULL_DISCLAIMER.strip().endswith("do not install or use the software.")
    # Spot-check the low sections; test_doc_claims owns the real count invariant.
    for n in range(1, 13):
        assert f"\n{n}. " in "\n" + FULL_DISCLAIMER

    assert SHORT_DISCLAIMER.startswith("Research and educational tool only.")
    assert "total loss" in SHORT_DISCLAIMER

    assert EXPORT_HEADER.startswith("# PennyTune —")
    assert "not investment advice" in EXPORT_HEADER
