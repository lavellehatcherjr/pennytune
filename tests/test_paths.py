"""Cross-platform path resolution tests."""

from pathlib import Path

from pennytune import paths


def test_dirs_are_paths() -> None:
    for resolver in (
        paths.config_dir,
        paths.cache_dir,
        paths.data_dir,
        paths.results_dir,
    ):
        resolved = resolver()
        assert isinstance(resolved, Path)
        assert str(resolved)


def test_config_file_under_config_dir() -> None:
    assert paths.config_file().parent == paths.config_dir()
    assert paths.config_file().name == "config.toml"


def test_results_dir_name() -> None:
    assert paths.results_dir().name == "results"


def test_ensure_dir_creates(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir"
    created = paths.ensure_dir(target)
    assert created == target
    assert target.is_dir()
