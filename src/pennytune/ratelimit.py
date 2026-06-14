"""Per-provider rate limiting and HTTP-429 backoff.

Token-bucket limiters (pyrate-limiter 4.x) sized to each free tier - EDGAR
~8/sec (10/sec hard ceiling), GDELT polite polling - and a tenacity
exponential-backoff retrier for HTTP 429 (≈2/4/8/16s).
There are no keyed/price providers, so there are no per-key quotas to manage.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import tenacity
from pyrate_limiter import Duration, Limiter, Rate
from tenacity.wait import wait_base

from pennytune.providers.base import RateLimitError

__all__ = ["RateLimiter", "make_retrying", "with_retry", "DEFAULT_MAX_ATTEMPTS"]

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 5


class RateLimiter:
    """Holds one token-bucket :class:`Limiter` per provider name.

    Rates are requests/second; fractional rates round up to at least 1/second
    (the limiters are a polite-polling guard, not a precise scheduler).
    """

    def __init__(self, rates: dict[str, float]) -> None:
        self._limiters: dict[str, Limiter] = {}
        for name, rps in rates.items():
            limit = max(1, int(round(rps)))
            self._limiters[name] = Limiter(Rate(limit, Duration.SECOND))

    def providers(self) -> list[str]:
        return list(self._limiters)

    def try_acquire(self, name: str, weight: int = 1) -> bool:
        """Non-blocking: return True if a token was available, else False."""
        limiter = self._limiters.get(name)
        if limiter is None:
            return True  # no limit configured for this provider
        return bool(limiter.try_acquire(name, weight=weight, blocking=False))

    def acquire(self, name: str, *, timeout: float = 30.0, weight: int = 1) -> bool:
        """Blocking: wait up to ``timeout`` seconds for a token."""
        limiter = self._limiters.get(name)
        if limiter is None:
            return True
        return bool(
            limiter.try_acquire(name, weight=weight, blocking=True, timeout=timeout)
        )


def make_retrying(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    wait: wait_base | None = None,
) -> tenacity.Retrying:
    """Build a tenacity retrier that retries on :class:`RateLimitError`.

    Default backoff is exponential ≈2/4/8/16s.
    Tests inject a no-wait strategy for speed.
    """
    return tenacity.Retrying(
        retry=tenacity.retry_if_exception_type(RateLimitError),
        wait=wait
        if wait is not None
        else tenacity.wait_exponential(multiplier=2, min=2, max=16),
        stop=tenacity.stop_after_attempt(max_attempts),
        reraise=True,
    )


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    wait: wait_base | None = None,
) -> T:
    """Call ``fn`` with 429 backoff retries, returning its result."""
    return make_retrying(max_attempts=max_attempts, wait=wait)(fn)
