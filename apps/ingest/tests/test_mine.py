"""The wearer's first day, rehearsed without a device or a network.

The command a family actually runs. Each way it can stop is pinned, and
so is the one thing it must never do: print a word of speech.
"""

from __future__ import annotations

import json

from bellwether_ingest.bee import BeeCli
from bellwether_ingest.cli import reduce_to_days
from bellwether_ingest.mine import MIN_WORDS, first_day

NOTE = "Walked to the market with Priya and argued about the pharmacy bill " * 14  # over 150 words


def runner_with(note_text: str | None, conversations: bool = True):
    def runner(argv: list[str]) -> tuple[int, str, str]:
        if "journals" in argv:
            items = [] if note_text is None else [{"id": "j1", "text": note_text, "state": "processed", "created_at": 1791400000000}]
            return (0, json.dumps({"journals": items, "next_cursor": None}), "")
        if "conversations" in argv and "list" in argv:
            rows = [{"id": 7, "start_time": 1791400000000, "end_time": 1791401000000, "short_summary": "Breakfast"}] if conversations else []
            return (0, json.dumps({"conversations": rows, "next_cursor": None}), "")
        if "conversations" in argv and "get" in argv:
            return (0, json.dumps({"conversation": {"id": 7, "start_time": 1791400000000, "transcriptions": [{"utterances": [
                {"text": "Could you pass the salt please, the eggs are bland today.", "speaker": "Unknown", "spoken_at": 1791400010000}]}]}}), "")
        if "status" in argv:
            return (0, "logged in", "")
        return (1, "", "unexpected")
    return runner


def harness(note_text, conversations=True):
    sent, lines = [], []
    cli = BeeCli(runner=runner_with(note_text, conversations))
    cli.installed = lambda: True  # type: ignore[method-assign]
    code = first_day(cli, post=lambda days, profile: sent.append((profile, days)) or {"stored": len(days)},
                     reduce=reduce_to_days, log=lines.append)
    return code, sent, "\n".join(lines)


def test_both_streams_are_posted_to_their_own_profiles():
    code, sent, out = harness(NOTE)
    assert code == 0
    assert [p for p, _ in sent] == ["me-voice", "me"]
    assert "voice notes: 1 day(s) read, 1 count" in out
    assert "/app/?profile=me-voice" in out


def test_not_one_word_of_speech_is_printed():
    _, sent, out = harness(NOTE)
    for word in ("Priya", "pharmacy", "market", "salt", "eggs"):
        assert word not in out
        assert word not in json.dumps(sent)


def test_a_short_note_is_read_but_does_not_count():
    code, sent, out = harness("Just testing, one two three.")
    assert code == 0
    assert "voice notes: 1 day(s) read, 0 count" in out
    assert f"at least {MIN_WORDS} words" in out


def test_nothing_recorded_says_what_to_do_and_sends_nothing():
    code, sent, out = harness(None, conversations=False)
    assert code == 4 and sent == []
    assert "record one voice note" in out


def test_not_logged_in_uses_the_apps_words():
    from bellwether_ingest.bee import BeeNotAuthenticated

    cli = BeeCli(runner=lambda argv: (1, "", "not logged in"))
    cli.installed = lambda: True  # type: ignore[method-assign]
    lines = []
    def boom(*a, **k):
        raise BeeNotAuthenticated("x")
    import bellwether_ingest.mine as m
    orig = m.ingest_journals; m.ingest_journals = boom
    try:
        code = first_day(cli, post=lambda d, p: None, reduce=reduce_to_days, log=lines.append)
    finally:
        m.ingest_journals = orig
    assert code == 3 and "bee login" in "\n".join(lines)
