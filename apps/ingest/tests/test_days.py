"""A day is the wearer's day, as the Bee reports it, not UTC's."""

from bellwether_ingest import days
from bellwether_ingest.bee import unwrap_conversation


def setup_function():
    days._reported = None


def teardown_function():
    days._reported = None


def test_without_a_reported_timezone_the_day_is_the_utc_day(monkeypatch):
    monkeypatch.delenv("BELLWETHER_TZ", raising=False)
    assert days.day_of("2026-10-23T03:29:10Z") == "2026-10-23"


def test_the_bee_reply_sets_the_wearer_timezone_and_the_evening_stays_that_evening(monkeypatch):
    monkeypatch.delenv("BELLWETHER_TZ", raising=False)
    unwrap_conversation({"conversation": {"id": 1}, "timezone": "America/New_York"})
    assert days.wearer_timezone() == "America/New_York"
    # 23:29 in New York on the 22nd is 03:29 UTC on the 23rd: the check-in is the 22nd's.
    assert days.day_of("2026-10-23T03:29:10Z") == "2026-10-22"
    assert days.day_of("2026-10-22T12:00:00Z") == "2026-10-22"


def test_the_first_reported_timezone_wins_and_the_environment_overrides_it(monkeypatch):
    unwrap_conversation({"conversation": {"id": 1}, "timezone": "America/New_York"})
    unwrap_conversation({"conversation": {"id": 2}, "timezone": "Asia/Kolkata"})
    assert days.wearer_timezone() == "America/New_York"
    monkeypatch.setenv("BELLWETHER_TZ", "Asia/Kolkata")
    assert days.day_of("2026-10-23T03:29:10Z") == "2026-10-23"


def test_an_unknown_timezone_name_falls_back_to_utc(monkeypatch):
    monkeypatch.setenv("BELLWETHER_TZ", "Not/AZone")
    assert days.day_of("2026-10-23T03:29:10Z") == "2026-10-23"
