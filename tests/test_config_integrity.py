"""A config write must never produce a config that cannot be read back.

There is no repair path through the CLI for a config that will not load, so a
bad write bricks every command. Two independent ways in:

* the write side: ``presets`` is a ``dict[str, PresetRiskBundle]``, and
  assigning into a plain dict does not fire pydantic's ``validate_assignment``,
  so a scalar reaches disk unchecked. Direct model fields are safe because
  ``setattr`` does validate.
* the read side: an unguarded ``load_config`` turns an already-bad config -
  hand edit, version skew, partial write - into a traceback and exit 1 instead
  of a named CONFIG_ERROR.

Both are pinned at the CLI boundary the user actually touches.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pennytune.cli import app
from pennytune.config import (
    _PRESET_NAMES,
    default_config,
    flatten,
    get_value,
    load_config,
    set_value,
)
from pennytune.exit_codes import ExitCode

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PENNYTUNE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("PENNYTUNE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PENNYTUNE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)


def _initialized(tmp_path: Path) -> Path:
    """A config file written by a successful ``init``."""
    cfg = tmp_path / "config.toml"
    result = runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "init",
            "--identity",
            "Test User test@example.com",
            "--i-understand-the-risks",
        ],
    )
    assert result.exit_code == 0, result.output
    return cfg


# ---- the write side ----------------------------------------------------------


@pytest.mark.parametrize("preset", _PRESET_NAMES)
def test_setting_a_preset_table_to_a_scalar_is_rejected(
    tmp_path: Path, preset: str
) -> None:
    """Every preset key, not just whichever one someone hits first."""
    cfg = _initialized(tmp_path)
    result = runner.invoke(
        app, ["--config", str(cfg), "config", "set", f"presets.{preset}", "hello"]
    )
    assert result.exit_code == int(ExitCode.USAGE_ERROR), (
        f"presets.{preset} accepted a scalar: exit={result.exit_code} "
        f"output={result.output!r}"
    )


@pytest.mark.parametrize("preset", _PRESET_NAMES)
def test_a_rejected_preset_write_leaves_the_config_loadable(
    tmp_path: Path, preset: str
) -> None:
    """The headline: a refused write must not be a write."""
    cfg = _initialized(tmp_path)
    before = cfg.read_bytes()
    runner.invoke(
        app, ["--config", str(cfg), "config", "set", f"presets.{preset}", "hello"]
    )
    assert cfg.read_bytes() == before, "the refused write still touched the file"
    load_config(cfg)  # raises if the file is corrupt


def test_the_tool_still_works_after_a_rejected_preset_write(tmp_path: Path) -> None:
    """Not bricked: the commands that read config still run."""
    cfg = _initialized(tmp_path)
    runner.invoke(
        app, ["--config", str(cfg), "config", "set", "presets.penny", "hello"]
    )
    after = runner.invoke(app, ["--config", str(cfg), "config", "get"])
    assert after.exit_code == 0, f"config get is broken: {after.output!r}"


def test_the_rejection_names_the_key_and_says_what_to_do(tmp_path: Path) -> None:
    """An error the user can act on, not just a refusal."""
    cfg = _initialized(tmp_path)
    result = runner.invoke(
        app, ["--config", str(cfg), "config", "set", "presets.penny", "hello"]
    )
    assert "presets.penny" in result.output, result.output
    assert "presets.penny." in result.output, (
        f"the message does not point at a settable field: {result.output!r}"
    )


def test_no_serializer_warning_escapes_on_a_rejected_write(tmp_path: Path) -> None:
    """Refuse before serialization, so the warning is never emitted at all.

    Under ``-W error::UserWarning`` a serializer warning aborts the write
    mid-save, leaving a half-written file. Rejecting the value earlier keeps
    that path unreachable.
    """
    cfg = _initialized(tmp_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        runner.invoke(
            app, ["--config", str(cfg), "config", "set", "presets.penny", "hello"]
        )
    serializer = [w for w in caught if "serializer" in str(w.message).lower()]
    assert not serializer, f"pydantic serializer warning still reachable: {serializer}"


# ---- what must keep working --------------------------------------------------


def test_a_field_inside_a_preset_is_still_settable(tmp_path: Path) -> None:
    """Reject on the leaf, not the parent.

    ``presets.broad.dilution`` legitimately walks THROUGH a BaseModel to a
    float. Rejecting on the parent breaks all 65 preset field keys.
    """
    cfg = _initialized(tmp_path)
    result = runner.invoke(
        app, ["--config", str(cfg), "config", "set", "presets.penny.dilution", "1.5"]
    )
    assert result.exit_code == 0, result.output
    assert load_config(cfg).presets["penny"].dilution == 1.5


def test_every_dotted_key_that_worked_before_still_works() -> None:
    """Every leaf key reachable through ``flatten`` stays settable.

    Guards against tightening the rejection until nested keys stop working. If
    this set shrinks, the guard is too broad.
    """
    # Keys whose validator wants a specific shape, not merely the right type.
    special = {
        "edgar_identity": "Probe User probe@example.com",
        "preset": "micro",
        "profile": "trader",
    }

    def sample(value: object) -> str:
        if isinstance(value, bool):
            return "true"
        if isinstance(value, int):
            return "3"
        if isinstance(value, float):
            return "1.5"
        if isinstance(value, list):
            return ",".join(str(v) for v in value) if value else "edgar"
        # Literal/str fields (filters.exchange, output_format, output_dir):
        # write back what is already there, which is always admissible.
        return str(value)

    keys = sorted(flatten(default_config()))
    failed: list[str] = []
    for key in keys:
        cfg = default_config()
        try:
            set_value(cfg, key, special.get(key, sample(get_value(cfg, key))))
        except Exception as exc:  # noqa: BLE001 - the point is to catch any
            failed.append(f"{key}: {type(exc).__name__}: {exc}")
    assert not failed, f"{len(failed)} of {len(keys)} keys regressed:\n" + "\n".join(
        failed
    )
    assert len(keys) == 98, f"the key surface changed: {len(keys)} keys, expected 98"


# ---- the read side: recovery from an already-bad config ----------------------

_CORRUPTIONS = {
    "schema": '[presets]\npenny = "hello"\n',
    "syntax": "this is not = = valid toml\n",
    "type": "risk_acknowledged = 12345\n",
}

# Every CLI entry point that loads config.
_LOAD_SITES = {
    "config get": ["config", "get"],
    "config set": ["config", "set", "weights.growth", "2"],
    "scan": ["scan", "AAPL"],
    "init": ["init", "--identity", "A B a@b.com", "--i-understand-the-risks"],
}


@pytest.mark.parametrize("site", sorted(_LOAD_SITES))
@pytest.mark.parametrize("corruption", sorted(_CORRUPTIONS))
def test_a_bad_config_exits_config_error_naming_the_file(
    tmp_path: Path, site: str, corruption: str
) -> None:
    """Exit 3 and a path the user can go fix, never a traceback."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(_CORRUPTIONS[corruption], encoding="utf-8")
    result = runner.invoke(app, ["--config", str(cfg), *_LOAD_SITES[site]])
    assert result.exit_code == int(ExitCode.CONFIG_ERROR), (
        f"{site} on a {corruption}-corrupt config exited {result.exit_code}, "
        f"expected {int(ExitCode.CONFIG_ERROR)}. Output: {result.output!r}"
    )
    assert str(cfg) in result.output, (
        f"{site} did not name the config file: {result.output!r}"
    )
    assert "Traceback" not in result.output, (
        f"{site} leaked a traceback: {result.output!r}"
    )


@pytest.mark.parametrize("site", sorted(_LOAD_SITES))
def test_a_bad_config_raises_no_exception_out_of_the_cli(
    tmp_path: Path, site: str
) -> None:
    """``CliRunner`` records what escaped; nothing should."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(_CORRUPTIONS["schema"], encoding="utf-8")
    result = runner.invoke(app, ["--config", str(cfg), *_LOAD_SITES[site]])
    assert result.exception is None or isinstance(result.exception, SystemExit), (
        f"{site} let {result.exception!r} escape the CLI"
    )
