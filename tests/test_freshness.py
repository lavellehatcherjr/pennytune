"""Data-freshness stamping tests."""

from datetime import UTC, datetime

from pennytune import freshness as fresh
from pennytune.freshness import FreshnessClass, FreshnessReport


def test_report_stamps_and_renders() -> None:
    report = FreshnessReport()
    now = datetime(2026, 6, 12, 14, 5, tzinfo=UTC)
    report.stamp(fresh.filings_news(now))
    report.stamp(fresh.financials("Q1-2026", "2026-05-08"))
    report.stamp(fresh.current_price(now))
    report.stamp(fresh.universe(now, from_cache=True))
    lines = report.render_lines()
    assert len(lines) == 4
    joined = "\n".join(lines)
    assert "filings/news" in joined
    assert "2026-06-12 14:05 UTC" in joined


def test_current_price_label_states_no_history() -> None:
    item = fresh.current_price()
    assert item.freshness == FreshnessClass.DELAYED_SNAPSHOT
    assert "no price history" in item.label


def test_universe_cached_flag_renders() -> None:
    item = fresh.universe(from_cache=True)
    assert item.from_cache
    assert "(cached)" in item.render()


def test_13f_lag_label() -> None:
    item = fresh.institutional_13f("Q1 2026")
    assert item.freshness == FreshnessClass.LAGGED
    assert "quarterly" in item.label


def test_financials_latest_filed() -> None:
    item = fresh.financials("Q1-2026", "2026-05-08")
    assert item.freshness == FreshnessClass.LATEST_FILED
    assert "Q1-2026" in item.as_of
    assert "2026-05-08" in item.as_of
