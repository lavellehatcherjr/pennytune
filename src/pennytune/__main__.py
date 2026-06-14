"""``python -m pennytune`` entry point.

Keeping the launch logic in one tiny module lets ``python -m pennytune`` work
and mirrors the ``pennytune`` console script (``[project.scripts]``).
"""

from __future__ import annotations

from pennytune.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
