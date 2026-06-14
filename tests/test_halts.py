"""SEC trading-suspension risk tests.

The gate must fire only on an ACTIVE/recent suspension; an expired one is
historical context (never gated). A name not on the list is clean (not
degraded); an unreachable list is degraded.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from pennytune.features.halts import (
    EdgarSuspensionProvider,
    HaltProfile,
    Suspension,
    compute_halt_risk,
    normalize_company,
    parse_sec_suspensions,
)
from pennytune.providers.base import ProviderError

NOW = datetime(2026, 6, 1, tzinfo=UTC)


# ---- parser (real SEC HTML shape: company name + "Month DD, YYYY", no ticker) -


def test_parse_sec_suspensions_real_html_shape() -> None:
    html = """
    <table><thead><th>Date</th><th>Respondents</th></thead>
    <tr><td>June 11, 2026</td><td>Happy City Holdings Limited</td>
        <td>Release No. 34-105675</td></tr>
    <tr><td>Sept. 26, 2023</td><td>Green Automotive Company</td>
        <td>Release No. 34-98519</td></tr>
    <tr><td>Feb. 30, 2026</td><td>Bad Date Co</td>
        <td>Release No. 34-99999</td></tr>
    </table>
    """
    suspensions = parse_sec_suspensions(html)
    # the impossible Feb 30 date is dropped (never gate on an unparseable date)
    assert [s.company for s in suspensions] == [
        "Happy City Holdings Limited",
        "Green Automotive Company",
    ]
    assert suspensions[0].date == "2026-06-11"  # "Month DD, YYYY" → ISO
    assert suspensions[1].date == "2023-09-26"  # abbreviated "Sept." handled
    assert suspensions[0].release == "34-105675"
    assert suspensions[0].symbol == ""  # the SEC list carries no ticker


def test_normalize_company_strips_suffixes() -> None:
    assert normalize_company("Happy City Holdings Limited") == "HAPPY CITY HOLDINGS"
    assert normalize_company("Acme, Inc.") == "ACME"
    # descriptive words (Holdings/Group) are kept — only entity designators drop
    assert normalize_company("U S Global Investors Inc") == "U S GLOBAL INVESTORS"


# ---- the gate: active gates, expired does NOT (compute_halt_risk unchanged) ---


def test_recent_suspension_gates() -> None:
    suspensions = [
        Suspension("ZZZ", "ZZZ Corp", "2026-05-20", "promotional activity", "34-1")
    ]
    profile = compute_halt_risk("ZZZ", suspensions, now=NOW)
    assert profile.tier == "suspended" and profile.hard_exclude is True
    assert "SEC-SUSPENSION" in profile.flags
    assert any("promotional activity" in e for e in profile.evidence)


def test_expired_suspension_does_not_gate() -> None:
    # A suspension from years ago must NOT gate the stock today.
    suspensions = [Suspension("ZZZ", "ZZZ Corp", "2021-05-20", "fraud", "34-9")]
    profile = compute_halt_risk("ZZZ", suspensions, now=NOW)
    assert profile.tier == "none" and profile.hard_exclude is False
    assert profile.flags == []


def test_clean_name_no_suspension_risk() -> None:
    profile = compute_halt_risk("CLEAN", [], now=NOW)
    assert profile.tier == "none" and profile.hard_exclude is False


# ---- the live provider (matched by company name; clean vs degraded) ----------


class _FakeClient:
    def __init__(self, html: str | None = None, error: Exception | None = None) -> None:
        self._html = html
        self._error = error

    def get_text(self, url: str, **kwargs: Any) -> str:
        if self._error is not None:
            raise self._error
        assert self._html is not None
        return self._html


def _row(d: date, company: str, release: str) -> str:
    when = f"{d.strftime('%B')} {d.day}, {d.year}"
    return f"<tr><td>{when}</td><td>{company}</td><td>Release No. {release}</td></tr>"


def test_provider_active_gates_expired_clean_and_degraded() -> None:
    now = datetime.now(UTC)
    recent = now.date() - timedelta(days=5)  # within the 180-day window
    old = now.date() - timedelta(days=400)  # expired
    html = (
        "<table>"
        + _row(recent, "Acme Suspended Inc", "34-100001")
        + _row(old, "Old Expired Corp", "34-90001")
        + "</table>"
    )
    provider = EdgarSuspensionProvider(_FakeClient(html))  # type: ignore[arg-type]

    # active/recent suspension → HARD GATE
    active = provider.get_halt_evidence("ACME", "Acme Suspended, Inc.", now=now)
    assert active.halt is not None
    assert active.halt.tier == "suspended" and active.halt.hard_exclude is True
    assert active.completeness == []

    # expired suspension (>180d) → surfaced historically, NOT gated
    expired = provider.get_halt_evidence("OLDX", "Old Expired Corp", now=now)
    assert expired.halt is not None
    assert expired.halt.tier == "none" and expired.halt.hard_exclude is False

    # a name not on the list → clean (tier none), NOT degraded
    clean = provider.get_halt_evidence("GROW", "U S Global Investors Inc", now=now)
    assert clean.halt is not None and clean.halt.tier == "none"
    assert clean.completeness == []  # checked-and-clean is not a degraded flag


def test_provider_degrades_when_list_unreachable() -> None:
    provider = EdgarSuspensionProvider(
        _FakeClient(error=ProviderError("HTTP 503"))  # type: ignore[arg-type]
    )
    ev = provider.get_halt_evidence("ANY", "Any Co", now=NOW)
    assert ev.halt is None  # could not check → not gated, but flagged
    assert any("could not check" in note for note in ev.completeness)


def test_provider_returns_haltprofile_type() -> None:
    provider = EdgarSuspensionProvider(
        _FakeClient("<table></table>")  # type: ignore[arg-type]
    )
    ev = provider.get_halt_evidence("X", "X Co", now=NOW)
    # empty list parses to nothing → treated as could-not-verify (degraded)
    assert ev.halt is None and ev.completeness
    assert isinstance(compute_halt_risk("X", [], now=NOW), HaltProfile)
