"""Provider cascade + hardened HTTP client tests.

All HTTP is mocked with ``responses`` - no live network calls.
"""

import pytest
import responses
import tenacity

from pennytune.providers.base import (
    AllProvidersFailedError,
    DataProvider,
    ProviderError,
    RateLimitError,
    cascade,
)
from pennytune.providers.http import SafeHttpClient, host_allowed
from pennytune.ratelimit import make_retrying


class _Fake(DataProvider):
    def __init__(self, name: str, value: str | None = None, fail: bool = False) -> None:
        self._name = name
        self._value = value
        self._fail = fail

    @property
    def name(self) -> str:
        return self._name

    def fetch(self) -> str:
        if self._fail:
            raise ProviderError(f"{self._name} is down")
        assert self._value is not None
        return self._value


# ---- cascade ----------------------------------------------------------------


def test_cascade_returns_first_success() -> None:
    providers = [_Fake("a", value="A"), _Fake("b", value="B")]
    assert cascade(providers, lambda p: p.fetch()) == "A"


def test_cascade_falls_through_on_failure() -> None:
    providers = [_Fake("a", fail=True), _Fake("b", value="B")]
    assert cascade(providers, lambda p: p.fetch()) == "B"


def test_cascade_all_fail_raises() -> None:
    providers = [_Fake("a", fail=True), _Fake("b", fail=True)]
    with pytest.raises(AllProvidersFailedError) as excinfo:
        cascade(providers, lambda p: p.fetch())
    assert len(excinfo.value.errors) == 2


def test_cascade_empty_raises() -> None:
    empty: list[_Fake] = []
    with pytest.raises(AllProvidersFailedError):
        cascade(empty, lambda p: p.fetch())


# ---- SafeHttpClient: safe parsing + HTTPS-only egress ----------------------


def test_host_allowed() -> None:
    assert host_allowed("data.sec.gov")
    assert host_allowed("efts.sec.gov")
    assert host_allowed("api.gdeltproject.org")
    assert not host_allowed("evil.example.com")
    assert not host_allowed(None)


def test_rejects_non_https() -> None:
    client = SafeHttpClient()
    with pytest.raises(ProviderError):
        client.get_bytes("http://data.sec.gov/x", retry=False)


def test_rejects_disallowed_domain() -> None:
    client = SafeHttpClient()
    with pytest.raises(ProviderError):
        client.get_bytes("https://evil.example.com/x", retry=False)


@responses.activate
def test_get_json_ok() -> None:
    responses.add(
        responses.GET, "https://data.sec.gov/d.json", json={"ok": True}, status=200
    )
    client = SafeHttpClient()
    assert client.get_json("https://data.sec.gov/d.json", retry=False) == {"ok": True}


@responses.activate
def test_size_cap_enforced() -> None:
    responses.add(
        responses.GET, "https://data.sec.gov/big", body=b"x" * 100, status=200
    )
    client = SafeHttpClient(max_bytes=10)
    with pytest.raises(ProviderError):
        client.get_bytes("https://data.sec.gov/big", retry=False)


@responses.activate
def test_429_then_retry_succeeds() -> None:
    url = "https://data.sec.gov/retry"
    responses.add(responses.GET, url, status=429)
    responses.add(responses.GET, url, json={"ok": 1}, status=200)
    client = SafeHttpClient(
        retrier_factory=lambda: make_retrying(max_attempts=3, wait=tenacity.wait_none())
    )
    assert client.get_json(url) == {"ok": 1}


@responses.activate
def test_429_raises_without_retry() -> None:
    url = "https://data.sec.gov/429"
    responses.add(responses.GET, url, status=429)
    client = SafeHttpClient()
    with pytest.raises(RateLimitError):
        client.get_bytes(url, retry=False)


@responses.activate
def test_user_agent_header_sent() -> None:
    url = "https://data.sec.gov/ua"
    responses.add(responses.GET, url, json={}, status=200)
    client = SafeHttpClient(user_agent="Dana Lee dana@example.com")
    client.get_json(url, retry=False)
    assert (
        responses.calls[0].request.headers["User-Agent"] == "Dana Lee dana@example.com"
    )
