"""Cross-platform application paths.

All per-OS locations resolve through ``platformdirs`` so config, cache, and
data land in the correct place on Linux, macOS, and Windows. User-facing scan
artifacts default to ``./results`` in the working directory (matching the
output display and the repository ``.gitignore``); this is overridable via
the ``output_dir`` config setting.
"""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import PlatformDirs

__all__ = [
    "APP_NAME",
    "config_dir",
    "data_dir",
    "results_dir",
    "config_file",
    "ensure_dir",
]

APP_NAME = "pennytune"

# appauthor=False keeps Windows paths as ...\pennytune (no author subfolder),
# matching the "<os-config-dir>/pennytune/" convention.
_DIRS = PlatformDirs(appname=APP_NAME, appauthor=False)


def _resolve(env_var: str, default: str) -> Path:
    """Honor an env override (handy for tests/power users) else the per-OS dir."""
    override = os.environ.get(env_var)
    return Path(override) if override else Path(default)


def config_dir() -> Path:
    """Per-OS user config directory (holds ``config.toml``)."""
    return _resolve("PENNYTUNE_CONFIG_DIR", _DIRS.user_config_dir)


def data_dir() -> Path:
    """Per-OS user data directory (app state, watchlist DB)."""
    return _resolve("PENNYTUNE_DATA_DIR", _DIRS.user_data_dir)


def results_dir() -> Path:
    """Default directory for exported scan results (``./results``)."""
    return Path.cwd() / "results"


def config_file() -> Path:
    """Default path to the TOML config file."""
    return config_dir() / "config.toml"


def ensure_dir(path: Path) -> Path:
    """Create ``path`` (and parents) if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
