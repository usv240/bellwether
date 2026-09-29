"""The shapes the real device answered with, pinned.

The first session with the hardware, 2026-09-29, bee-cli 0.7.3, found
three things no fixture had guessed. ``bee conversations list`` carries
summaries and an ``utterances_count`` and not one utterance, so the
rehearsal reduced two recorded conversations to zero. ``bee conversations
get`` wraps the record in ``{"conversation": ..., "timezone": ...}``.
And each utterance carries ``spoken_at`` and ``created_at`` as epoch
milliseconds beside ``start`` and ``end`` as seconds into the
conversation, so a parser that reads ``start`` as a time puts every word
on the first of January 1970.

Every field here is the device's; every word is not. The texts are
placeholders of the same length class, because this file is public and
the transcript is not.
"""

from __future__ import annotations

import json

from bellwether_ingest.bee import (
    BeeCli,
    has_utterances,
    normalize_conversation,
    unwrap_conversation,
    with_utterances,
)
from bellwether_ingest.firstrun import run

LIST_ROW = {
    "id": 10824219,
    "start_time": 1790714170803,
    "end_time": 1790714326063,
    "device_type": "unknown",
    "summary": "## Summary\n\n(redacted)",
    "short_summary": "(redacted)",
    "state": "COMPLETED",
    "created_at": 1790714171000,
    "updated_at": 1790714545137,
    "utterances_count": 18,
    "primary_location": None,
}


def utterance(i: int, words: int = 12) -> dict:
    return {
        "id": 3547021300 + i,
        "realtime": True,
        "start": 1 + 11 * i,
        "end": 12 + 11 * i,
        "spoken_at": 1790714507000 + 11_000 * i,
        "text": " ".join(["word"] * words),
        "speaker": "Unknown",
        "created_at": 1790714545137 + 11_000 * i,
    }


def get_response(n: int = 18) -> dict:
    return {
        "conversation": {
            **LIST_ROW,
            "transcriptions": [{"id": 1, "realtime": True, "utterances": [utterance(i) for i in range(n)]}],
            "suggested_links": [],
        },
        "timezone": "America/New_York",
    }


def test_the_list_row_has_no_words_and_says_so():
    assert has_utterances(LIST_ROW) is False
    assert normalize_conversation(LIST_ROW) == []


def test_get_is_unwrapped_and_its_utterances_are_read():
    got = get_response()
    assert unwrap_conversation(got)["id"] == 10824219
    utts = normalize_conversation(got)
    assert len(utts) == 18
    assert all(u.conversation_id == "10824219" for u in utts)


def test_utterance_time_is_spoken_at_not_the_offset_into_the_conversation():
    utts = normalize_conversation(get_response(2))
    assert utts[0].ts == "2026-09-29T20:41:47Z"
    assert utts[1].ts == "2026-09-29T20:41:58Z"
    # A parser that read ``start`` (1, 12) as an instant would say 1970.
    assert not any(u.ts.startswith("1970") for u in utts)


def test_rows_without_words_are_fetched_one_by_one_and_bounded():
    calls: list[list[str]] = []

    def runner(argv: list[str]):
        calls.append(argv)
        if "get" in argv:
            return (0, json.dumps(get_response()), "")
        return (1, "", "unexpected")

    cli = BeeCli(runner=runner)
    rows = [LIST_ROW, {**LIST_ROW, "id": 10824046}, {**LIST_ROW, "id": 3}]
    records = with_utterances(cli, rows, limit=2)
    assert [has_utterances(r) for r in records] == [True, True, False]
    assert sum("get" in c for c in calls) == 2
    assert any("10824219" in c for c in calls[0])


def test_rows_that_already_carry_words_are_not_fetched_again():
    def runner(argv: list[str]):
        raise AssertionError(f"no call expected, got {argv}")

    bare = unwrap_conversation(get_response(3))
    assert with_utterances(BeeCli(runner=runner), [bare]) == [bare]


def test_firstrun_reaches_a_real_day_from_the_device_shapes(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/bee")

    def runner(argv: list[str]):
        joined = " ".join(argv)
        if " me " in joined + " ":
            return (0, json.dumps({"id": 53269}), "")
        if "conversations list" in joined:
            return (0, json.dumps({"conversations": [LIST_ROW], "next_cursor": None}), "")
        if "conversations get" in joined:
            return (0, json.dumps(get_response(40)), "")
        return (1, "", f"unexpected {argv}")

    steps = run(BeeCli(runner=runner))
    by_name = {s.name: s for s in steps}
    assert by_name["conversations recorded"].ok is True
    assert by_name["a real day reduces to nine features"].ok is True
    assert "1 day(s) extracted, 1 with speech" in by_name["a real day reduces to nine features"].detail
