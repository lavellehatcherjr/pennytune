"""Stable, documented process exit codes.

The CLI is meant to be scriptable, so these codes are part of the public
contract and must not change meaning between releases.
"""

from __future__ import annotations

from enum import IntEnum

__all__ = ["ExitCode"]


class ExitCode(IntEnum):
    """Exit codes returned by the ``pennytune`` CLI."""

    #: Results produced, even if some tickers failed to enrich.
    SUCCESS = 0
    #: Partial failure above threshold (e.g. >X% of tickers failed to enrich);
    #: results are still written and a warning is shown.
    PARTIAL_FAILURE = 1
    #: Usage error - bad flags or arguments.
    USAGE_ERROR = 2
    #: Configuration error - e.g. missing EDGAR identity, or the risk
    #: acknowledgment has not been recorded.
    CONFIG_ERROR = 3
    #: No network and no usable cache for an online command.
    NO_NETWORK_NO_CACHE = 4
    #: Interrupted by the user (Ctrl-C); partial results flushed where safe.
    INTERRUPTED = 5
