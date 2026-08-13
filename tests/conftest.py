"""Session-wide guard: the suite must not write into the working tree.

``scan --format csv`` exports to ``paths.results_dir()``, which is
``Path.cwd() / "results"``. Any CLI test that invokes it without first chdir-ing
to a tmp_path drops scan exports into the checkout, where .gitignore hides them
and nobody notices.

This compares the tree before and after the run and fails on anything added, so
a test writing to the wrong place is caught here rather than by someone reading
``git status`` weeks later.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

# Transient by design: caches and build metadata churn on every run and are
# not what this guard is about.
_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "node_modules",
        "venv",
    }
)


def _tree() -> set[Path]:
    """Every file in the repo, minus the directories that churn by design."""
    found: set[Path] = set()
    for path in _REPO.rglob("*"):
        if any(
            part in _IGNORED_DIRS or part.endswith(".egg-info") for part in path.parts
        ):
            continue
        if path.is_file():
            found.add(path)
    return found


@pytest.fixture(scope="session", autouse=True)
def _no_artifacts_in_the_working_tree() -> Iterator[None]:
    before = _tree()
    yield
    added = sorted(path.relative_to(_REPO) for path in _tree() - before)
    assert not added, (
        f"the test suite wrote {len(added)} file(s) into the repository; "
        f"tests must write under tmp_path: {[str(p) for p in added]}"
    )
