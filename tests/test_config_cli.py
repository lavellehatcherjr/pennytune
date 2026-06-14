"""CLI tests for `config get` / `config set` and their exit codes."""

from pathlib import Path

from typer.testing import CliRunner

from pennytune.cli import app

runner = CliRunner()


def test_config_set_then_get_roundtrip(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    result = runner.invoke(
        app, ["--config", str(cfg), "config", "set", "weights.valuation", "1.7"]
    )
    assert result.exit_code == 0, result.output
    got = runner.invoke(
        app, ["--config", str(cfg), "config", "get", "weights.valuation"]
    )
    assert got.exit_code == 0
    assert "1.7" in got.output


def test_config_set_unknown_key_exits_2(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    result = runner.invoke(
        app, ["--config", str(cfg), "config", "set", "weights.bogus", "1.0"]
    )
    assert result.exit_code == 2


def test_config_set_bad_value_exits_2(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    result = runner.invoke(
        app, ["--config", str(cfg), "config", "set", "weights.valuation", "-5"]
    )
    assert result.exit_code == 2


def test_config_get_redacts_email(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    runner.invoke(
        app,
        [
            "--config",
            str(cfg),
            "config",
            "set",
            "edgar_identity",
            "Dana Lee dana@example.com",
        ],
    )
    result = runner.invoke(
        app, ["--config", str(cfg), "config", "get", "edgar_identity"]
    )
    assert result.exit_code == 0
    assert "d***@example.com" in result.output
    assert "dana@example.com" not in result.output


def test_config_set_profile_resets_weights(tmp_path: Path) -> None:
    cfg = tmp_path / "c.toml"
    result = runner.invoke(
        app, ["--config", str(cfg), "config", "set", "profile", "trader"]
    )
    assert result.exit_code == 0
    got = runner.invoke(
        app, ["--config", str(cfg), "config", "get", "weights.sentiment"]
    )
    assert "1.4" in got.output  # trader bundle sentiment weight
