"""8-K item-code event-engine tests. Fixture submissions only."""

from typing import Any

from pennytune.features.events import (
    build_event,
    build_event_tape,
    classify_item,
    parse_submissions_8k_events,
)


def test_classify_each_code() -> None:
    assert classify_item("1.03") == ("distress", 5.0)  # bankruptcy, max
    assert classify_item("4.02") == ("distress", 5.0)  # restatement, max forensic
    assert classify_item("2.04") == ("distress", 4.0)  # covenant breach
    assert classify_item("3.01") == ("distress", 4.0)  # delisting notice
    assert classify_item("3.02") == ("financing", 3.0)  # unregistered equity
    assert classify_item("1.01") == ("financing", 2.0)  # material agreement
    assert classify_item("5.02") == ("governance", 2.0)  # officer change
    assert classify_item("2.02") == ("operational", 1.0)  # earnings
    assert classify_item("7.01") == ("promotional", 1.0)  # Reg FD
    assert classify_item("8.01") == ("promotional", 1.0)  # other events
    assert classify_item("9.01") == ("operational", 0.0)  # exhibits boilerplate
    assert classify_item("6.99") == ("uncategorized", 0.0)  # unknown


def test_classify_with_description_text() -> None:
    assert classify_item("5.02 Departure of Directors or Certain Officers") == (
        "governance",
        2.0,
    )


def test_multi_item_highest_severity_all_retained() -> None:
    event = build_event("a1", "2026-05-30", "8-K", "1.01,3.02,9.01")
    assert event.severity == 3.0  # max(2.0, 3.0, 0.0)
    assert event.category == "financing"  # the 3.02 item drives it
    assert event.item_codes == ["1.01", "3.02", "9.01"]  # ALL items retained
    assert "financing" in event.categories
    assert "operational" in event.categories


def test_amendment_noted() -> None:
    event = build_event("a2", "2026-05-12", "8-K/A", "4.02")
    assert event.is_amendment is True
    assert event.category == "distress"
    assert event.severity == 5.0


def test_uncategorized_passed_through_not_dropped() -> None:
    event = build_event("a3", "2026-05-30", "8-K", "6.99")
    assert event.item_codes == ["6.99"]  # retained, not dropped
    assert event.category == "uncategorized"
    assert event.severity == 0.0


def test_parse_submissions_only_8k() -> None:
    submissions: dict[str, Any] = {
        "cik": "0000000111",
        "filings": {
            "recent": {
                "form": ["8-K", "10-Q", "8-K/A", "8-K"],
                "accessionNumber": ["0001", "0002", "0003", "0004"],
                "filingDate": ["2026-05-30", "2026-05-08", "2026-05-12", "2026-04-02"],
                "items": ["3.02,9.01", "", "5.02", "1.01,7.01"],
            }
        },
    }
    events = parse_submissions_8k_events(submissions)
    assert len(events) == 3  # the 10-Q is skipped
    assert events[0].item_codes == ["3.02", "9.01"]
    assert events[1].is_amendment is True  # the 8-K/A
    assert events[2].item_codes == ["1.01", "7.01"]


def test_promotional_cadence_fires_on_sustained() -> None:
    events = [
        build_event("a", "2026-05-01", "8-K", "8.01"),
        build_event("b", "2026-05-10", "8-K", "7.01"),
        build_event("c", "2026-05-20", "8-K", "8.01"),
    ]
    tape = build_event_tape(events)
    assert tape.promotional_cadence is True
    assert "promotional-8k-cadence" in tape.flags


def test_promotional_cadence_not_on_single_press_release() -> None:
    tape = build_event_tape([build_event("a", "2026-05-01", "8-K", "8.01")])
    assert tape.promotional_cadence is False
    assert tape.flags == []


def test_promotional_cadence_suppressed_by_earnings_substance() -> None:
    events = [
        build_event("a", "2026-05-01", "8-K", "8.01"),
        build_event("b", "2026-05-10", "8-K", "7.01"),
        build_event("c", "2026-05-20", "8-K", "8.01"),
        build_event("d", "2026-05-25", "8-K", "2.02"),  # real earnings substance
    ]
    tape = build_event_tape(events)
    assert tape.signals.earnings_count == 1
    assert tape.promotional_cadence is False  # not "no earnings substance"


def test_302_surfaced_for_dilution_and_forensics() -> None:
    tape = build_event_tape([build_event("a", "2026-05-30", "8-K", "3.02,9.01")])
    assert tape.signals.has_unregistered_equity_sale is True
    assert tape.signals.unregistered_equity_count == 1
    assert tape.signals.issuance_indicator is True  # sets the Dechow issuance indicator


def test_delisting_and_bankruptcy_signals() -> None:
    tape = build_event_tape(
        [
            build_event("a", "2026-04-30", "8-K", "3.01"),
            build_event("b", "2026-04-15", "8-K", "1.03"),
        ]
    )
    assert tape.signals.has_delisting_notice is True
    assert tape.signals.has_bankruptcy is True


def test_aggregate_counts() -> None:
    events = [
        build_event("a", "2026-05-30", "8-K", "3.02,9.01"),
        build_event("b", "2026-05-20", "8-K", "5.02"),
    ]
    tape = build_event_tape(events)
    assert tape.item_counts["3.02"] == 1
    assert tape.item_counts["9.01"] == 1
    assert tape.category_counts["financing"] == 1  # the 3.02 event
    assert tape.category_counts["governance"] == 1  # the 5.02 event
