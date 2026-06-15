"""Hardened HTTP client for all provider egress.

Enforces: HTTPS-only requests to an allow-list of documented data-source
domains (re-checked after redirects), TLS verification, a per-request timeout,
a response-size cap, and JSON parsing via the stdlib only (no eval/pickle of
untrusted data). Integrates the per-provider rate limiter and the 429-backoff
retrier (:mod:`pennytune.ratelimit`).

Synchronous ``requests`` is used (mockable with the ``responses`` library in
tests); httpx remains available for any future async needs.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any, cast
from urllib.parse import urlsplit

import requests

from pennytune.providers.base import (
    DisallowedDomainError,
    ProviderError,
    RateLimitError,
    ResponseTooLargeError,
)
from pennytune.ratelimit import RateLimiter, make_retrying

__all__ = ["SafeHttpClient", "ALLOWED_DOMAIN_SUFFIXES", "host_allowed"]

# Documented data sources only. Subdomains of these are allowed.
ALLOWED_DOMAIN_SUFFIXES: tuple[str, ...] = (
    "sec.gov",  # data.sec.gov, efts.sec.gov, www.sec.gov (the only data source)
)

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_BYTES = 50_000_000  # 50 MB hard cap per response


def host_allowed(host: str | None) -> bool:
    """True if ``host`` is one of, or a subdomain of, an allowed domain."""
    if not host:
        return False
    host = host.lower()
    return any(
        host == suffix or host.endswith(f".{suffix}")
        for suffix in ALLOWED_DOMAIN_SUFFIXES
    )


class SafeHttpClient:
    """A small ``requests`` wrapper enforcing the safe-egress policy."""

    def __init__(
        self,
        *,
        limiter: RateLimiter | None = None,
        user_agent: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        retrier_factory: Callable[[], Any] = make_retrying,
    ) -> None:
        self._session = requests.Session()
        self._limiter = limiter
        self._user_agent = user_agent
        self._timeout = timeout
        self._max_bytes = max_bytes
        self._retrier_factory = retrier_factory

    def _validate_url(self, url: str) -> None:
        parts = urlsplit(url)
        if parts.scheme != "https":
            raise DisallowedDomainError(f"non-HTTPS URL rejected: {url}")
        if not host_allowed(parts.hostname):
            raise DisallowedDomainError(f"domain not on allow-list: {parts.hostname!r}")

    def _raw_get(
        self,
        url: str,
        *,
        provider: str | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> requests.Response:
        self._validate_url(url)
        if self._limiter is not None and provider is not None:
            if not self._limiter.acquire(provider, timeout=self._timeout):
                raise RateLimitError(
                    f"could not acquire a rate-limit token for {provider!r}"
                )

        merged: dict[str, str] = {}
        if self._user_agent:
            merged["User-Agent"] = self._user_agent
        if headers:
            merged.update(headers)

        try:
            response = self._session.get(
                url,
                headers=merged,
                params=dict(params) if params else None,
                timeout=self._timeout,
                verify=True,  # TLS verification
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"request to {url} failed: {exc}") from exc

        # Re-check the final URL host in case of redirects.
        if not host_allowed(urlsplit(str(response.url)).hostname):
            raise DisallowedDomainError(
                f"redirected off the allow-list: {response.url}"
            )

        status = int(response.status_code)
        if status == 429:
            raise RateLimitError(f"HTTP 429 (rate limited) from {url}")
        if status >= 400:
            raise ProviderError(f"HTTP {status} from {url}")

        size = len(response.content)
        if size > self._max_bytes:
            raise ResponseTooLargeError(
                f"response from {url} is {size} bytes (cap {self._max_bytes})"
            )
        return response

    def get_bytes(
        self,
        url: str,
        *,
        provider: str | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        retry: bool = True,
    ) -> bytes:
        """GET raw bytes, with optional 429-backoff retry."""

        def _call() -> bytes:
            return self._raw_get(
                url, provider=provider, headers=headers, params=params
            ).content

        if retry:
            return cast(bytes, self._retrier_factory()(_call))
        return _call()

    def get_text(
        self,
        url: str,
        *,
        provider: str | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        retry: bool = True,
    ) -> str:
        return self.get_bytes(
            url, provider=provider, headers=headers, params=params, retry=retry
        ).decode("utf-8", errors="replace")

    def get_json(
        self,
        url: str,
        *,
        provider: str | None = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        retry: bool = True,
    ) -> Any:
        raw = self.get_bytes(
            url, provider=provider, headers=headers, params=params, retry=retry
        )
        try:
            return json.loads(raw)  # stdlib only - no eval/pickle
        except json.JSONDecodeError as exc:
            raise ProviderError(f"invalid JSON from {url}: {exc}") from exc

    def close(self) -> None:
        self._session.close()
