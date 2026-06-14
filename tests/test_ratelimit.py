"""Rate-limiter and 429-backoff tests."""

import pytest
import tenacity

from pennytune.providers.base import RateLimitError
from pennytune.ratelimit import RateLimiter, with_retry


def test_token_bucket_limits_rate() -> None:
    limiter = RateLimiter({"edgar": 2})
    acquired = [limiter.try_acquire("edgar") for _ in range(5)]
    assert acquired[:2] == [True, True]  # within the per-second budget
    assert not all(acquired)  # the bucket exhausts within the window


def test_unknown_provider_is_unlimited() -> None:
    limiter = RateLimiter({"edgar": 2})
    assert all(limiter.try_acquire("not-configured") for _ in range(50))


def test_retry_on_429_then_succeeds() -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimitError("429")
        return "ok"

    result = with_retry(flaky, max_attempts=5, wait=tenacity.wait_none())
    assert result == "ok"
    assert calls["n"] == 3


def test_retry_gives_up_after_max_attempts() -> None:
    def always_limited() -> str:
        raise RateLimitError("429")

    with pytest.raises(RateLimitError):
        with_retry(always_limited, max_attempts=3, wait=tenacity.wait_none())


def test_other_errors_are_not_retried() -> None:
    calls = {"n": 0}

    def boom() -> str:
        calls["n"] += 1
        raise ValueError("not a rate limit")

    with pytest.raises(ValueError):
        with_retry(boom, max_attempts=5, wait=tenacity.wait_none())
    assert calls["n"] == 1  # only RateLimitError triggers a retry
