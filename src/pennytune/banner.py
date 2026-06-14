"""Startup banner: the gold ASCII logo, tagline, and disclaimer reminder.

A gold ASCII-art "PennyTune" logo (pyfiglet) with the cyan tagline and a
one-line disclaimer reminder, shown on ``init`` and on a bare ``pennytune``
invocation. Suppressed when output is piped/non-TTY, or when ``--quiet`` /
``--json`` / ``--no-color`` is set, so it never pollutes machine-readable
output. Gold is used only here, never for status flags.
"""

from __future__ import annotations

import io

import pyfiglet

__all__ = ["TAGLINE", "REMINDER", "render_banner", "should_show_banner"]

TAGLINE = "Tune out the noise."
REMINDER = "Research tool — not investment advice."
_LOGO_GOLD = "#FFD700"  # true-gold; Rich degrades to ANSI bright-yellow elsewhere


def render_banner(*, no_color: bool = False) -> str:
    """Render the gold logo + cyan tagline + disclaimer reminder to a string."""
    from rich.console import Console
    from rich.text import Text

    art = pyfiglet.figlet_format("PennyTune", font="standard").rstrip("\n")
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        no_color=no_color,
        force_terminal=not no_color,
        width=80,
        highlight=False,
    )
    console.print(Text(art, style=_LOGO_GOLD))
    console.print(Text(TAGLINE, style="cyan"))
    console.print(Text(REMINDER, style="dim"))
    return buffer.getvalue()


def should_show_banner(
    *, is_tty: bool, no_color: bool, quiet: bool, json_output: bool
) -> bool:
    """The banner shows only on an interactive TTY with color and no quiet/json."""
    return is_tty and not (no_color or quiet or json_output)
