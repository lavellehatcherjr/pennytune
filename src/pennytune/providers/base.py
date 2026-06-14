"""Provider interface, error types, and the cascade/fallback runner.

Each data role is its own small abstract interface so sources are swappable.
``cascade`` tries an ordered list of providers and falls through to the next on
any :class:`ProviderError`, raising :class:`AllProvidersFailedError` only if
every provider fails - so one source being down never aborts the run.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

__all__ = [
    "ProviderError",
    "RateLimitError",
    "ResponseTooLargeError",
    "DisallowedDomainError",
    "AllProvidersFailedError",
    "DataProvider",
    "FundamentalsProvider",
    "cascade",
]


class ProviderError(Exception):
    """Base class for recoverable provider/data-fetch failures."""


class RateLimitError(ProviderError):
    """Raised on HTTP 429 or when a rate-limit token cannot be acquired."""


class ResponseTooLargeError(ProviderError):
    """Raised when a response exceeds the configured size cap."""


class DisallowedDomainError(ProviderError):
    """Raised when a URL is not HTTPS or its host is not on the allow-list."""


class AllProvidersFailedError(ProviderError):
    """Raised when every provider in a cascade failed."""

    def __init__(self, errors: Sequence[tuple[str, Exception]]) -> None:
        self.errors = list(errors)
        detail = (
            "; ".join(f"{name}: {exc}" for name, exc in self.errors) or "no providers"
        )
        super().__init__(f"all providers failed ({detail})")


class DataProvider(ABC):
    """A swappable data source."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable, human-readable provider identifier (e.g. ``"edgar"``)."""


class FundamentalsProvider(DataProvider):
    @abstractmethod
    def get_fundamentals(self, cik: str) -> Any:
        """Return filed financial-statement facts for a CIK."""


# NOTE: there is intentionally NO PriceHistoryProvider / get_price_history role
# - price/technicals are out of scope (no OHLCV, no API keys).

P = TypeVar("P", bound=DataProvider)
T = TypeVar("T")


def cascade(providers: Sequence[P], call: Callable[[P], T]) -> T:
    """Try each provider's ``call`` in order, falling through on ProviderError.

    Returns the first successful result. Raises :class:`AllProvidersFailedError`
    if every provider fails (or the list is empty).
    """
    errors: list[tuple[str, Exception]] = []
    for provider in providers:
        try:
            return call(provider)
        except ProviderError as exc:
            errors.append((provider.name, exc))
    raise AllProvidersFailedError(errors)
