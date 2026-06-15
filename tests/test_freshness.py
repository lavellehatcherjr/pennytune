"""Data-freshness stamping tests."""

from datetime import UTC, datetime

from pennytune import freshness as fresh
from pennytune.freshness import FreshnessClass, FreshnessReport


def test_report_stamps_and_renders() -> None:
    report = FreshnessReport()
    now = datetime(2026, 6, 12, 14, 5, tzinfo=UTC)
    report.stamp(fresh.filings_news(now))
    report.stamp(fresh.financials("Q1-2026", "2026-05-08"))
    lines = report.render_lines()
    assert len(lines) == 2
    joined = "\n".join(lines)
    assert "filings/news" in joined
    assert "2026-06-12 14:05 UTC" in joined


def test_13f_lag_label() -> None:
    item = fresh.institutional_13f("Q1 2026")
    assert item.freshness == FreshnessClass.LAGGED
    assert "quarterly" in item.label


def test_financials_latest_filed() -> None:
    item = fresh.financials("Q1-2026", "2026-05-08")
    assert item.freshness == FreshnessClass.LATEST_FILED
    assert "Q1-2026" in item.as_of
    assert "2026-05-08" in item.as_of
