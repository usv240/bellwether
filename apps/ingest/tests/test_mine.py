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
    assert "check-ins: 1 day(s) read, 1 count" in out
    assert "/app/?profile=me-voice" in out


def test_not_one_word_of_speech_is_printed():
    _, sent, out = harness(NOTE)
    for word in ("Priya", "pharmacy", "market", "salt", "eggs"):
        assert word not in out
        assert word not in json.dumps(sent)


def test_a_short_note_is_read_but_does_not_count():
    code, sent, out = harness("Just testing, one two three.")
    assert code == 0
    assert "check-ins: 1 day(s) read, 0 count" in out
    assert f"at least {MIN_WORDS} words" in out


def test_nothing_recorded_says_what_to_do_and_sends_nothing():
    code, sent, out = harness(None, conversations=False)
    assert code == 4 and sent == []
    assert "check in once" in out


def test_not_logged_in_uses_the_apps_words():
    from bellwether_ingest.bee import BeeNotAuthenticated

    cli = BeeCli(runner=lambda argv: (1, "", "not logged in"))
    cli.installed = lambda: True  # type: ignore[method-assign]
    lines = []
    def boom(*a, **k):
        raise BeeNotAuthenticated("x")
    import bellwether_ingest.mine as m
    orig = m.ingest_checkins; m.ingest_checkins = boom
    try:
        code = first_day(cli, post=lambda d, p: None, reduce=reduce_to_days, log=lines.append)
    finally:
        m.ingest_checkins = orig
    assert code == 3 and "bee login" in "\n".join(lines)


def test_a_short_day_puts_one_reminder_on_the_bee_and_never_two():
    """The ask goes where the wearer will see it, their own Bee's todos,
    only when the day is short, and an open reminder is not repeated."""
    created, todos = [], []

    def runner(argv: list[str]) -> tuple[int, str, str]:
        if "todos" in argv and "list" in argv:
            return (0, json.dumps({"todos": todos, "next_cursor": None}), "")
        if "todos" in argv and "create" in argv:
            created.append(argv[argv.index("--text") + 1])
            return (0, json.dumps({"todo": {"id": "t1"}}), "")
        return runner_with("Just testing, one two three.")(argv)

    cli = BeeCli(runner=runner)
    cli.installed = lambda: True  # type: ignore[method-assign]
    lines = []
    assert first_day(cli, post=lambda d, p: {"stored": 1}, reduce=reduce_to_days, log=lines.append, remind=True) == 0
    assert len(created) == 1 and created[0].startswith("Bellwether:") and "145 more words" in created[0]
    assert "testing" not in created[0]
    assert "reminder was added" in "\n".join(lines)

    todos.append({"id": "t1", "text": created[0], "completed": False})
    first_day(cli, post=lambda d, p: {"stored": 1}, reduce=reduce_to_days, log=lines.append, remind=True)
    assert len(created) == 1


def test_a_full_day_adds_no_reminder():
    created = []

    def runner(argv: list[str]) -> tuple[int, str, str]:
        if "todos" in argv:
            created.append(argv)
            return (0, json.dumps({"todos": []}), "")
        return runner_with(NOTE)(argv)

    cli = BeeCli(runner=runner)
    cli.installed = lambda: True  # type: ignore[method-assign]
    first_day(cli, post=lambda d, p: {"stored": 1}, reduce=reduce_to_days, log=lambda s: None, remind=True)
    assert not [a for a in created if "create" in a]


def test_mine_claims_both_profiles_on_the_first_run_and_stops_if_one_is_someone_elses():
    import urllib.error

    claimed, lines = [], []
    code = first_day(_cli(NOTE), post=lambda d, p: {"stored": 1}, reduce=reduce_to_days, log=lines.append,
                     claim=lambda p: claimed.append(p) or "claimed")
    assert code == 0 and claimed == ["me-voice", "me"]
    assert "now your profile" in "\n".join(lines)

    def refused(days, profile):
        raise urllib.error.HTTPError("u", 403, "claimed", {}, None)

    lines.clear()
    code = first_day(_cli(NOTE), post=refused, reduce=reduce_to_days, log=lines.append, claim=lambda p: "already")
    assert code == 5 and "--profile <name>" in "\n".join(lines)


def test_mine_sends_a_named_profile_and_its_voice_twin():
    sent = []
    first_day(_cli(NOTE), post=lambda d, p: sent.append(p) or {"stored": 1}, reduce=reduce_to_days, log=lambda s: None, profile="grandma")
    assert sent == ["grandma-voice", "grandma"]


def _cli(note_text):
    cli = BeeCli(runner=runner_with(note_text))
    cli.installed = lambda: True  # type: ignore[method-assign]
    return cli


def test_days_stops_paging_at_the_first_older_conversation():
    """A daily run reads a day, not a month: the list comes newest first,
    so paging stops as soon as a page reaches past the window, and only
    conversations inside it are fetched for their words."""
    import time

    from bellwether_ingest.bee import OwnerFilter, ingest_backfill

    now_ms = int(time.time() * 1000)
    pages = {
        None: {"conversations": [{"id": 1, "start_time": now_ms - 3600_000}, {"id": 2, "start_time": now_ms - 30 * 86400_000}], "next_cursor": "p2"},
        "p2": {"conversations": [{"id": 3, "start_time": now_ms - 40 * 86400_000}], "next_cursor": None},
    }
    calls = []

    def runner(argv):
        calls.append(argv)
        if "list" in argv:
            cur = argv[argv.index("--cursor") + 1] if "--cursor" in argv else None
            return (0, json.dumps(pages[cur]), "")
        if "get" in argv:
            cid = argv[argv.index("get") + 1]
            return (0, json.dumps({"conversation": {"id": int(cid), "start_time": now_ms - 3600_000, "transcriptions": [{"utterances": [
                {"text": "a quiet morning and a walk", "speaker": "Unknown", "spoken_at": now_ms - 3500_000}]}]}}), "")
        return (1, "", "unexpected")

    ingest_backfill(BeeCli(runner=runner), OwnerFilter(None), since_ms=now_ms - 2 * 86400_000)
    assert not [a for a in calls if "--cursor" in a]
    assert [a[a.index("get") + 1] for a in calls if "get" in a] == ["1"]


def test_the_count_reported_is_the_one_the_service_holds():
    lines = []
    first_day(_cli(NOTE), post=lambda d, p: {"stored": 1, "eligible_days": 4}, reduce=reduce_to_days, log=lines.append)
    assert "Day 4 of 7 counted." in "\n".join(lines)
    assert "3 more day(s)" in "\n".join(lines)


def test_a_short_run_never_posts_a_day_outside_its_window():
    """An old voice note is still on the account when a two-day run reads
    only two days of sessions. Posting its day would overwrite the full
    day already on the service with a sentence. Found on the first real
    run, which turned a counted day into an excluded one."""
    import time

    now_ms = int(time.time() * 1000)
    old_ms = now_ms - 9 * 86400_000

    def runner(argv):
        if "journals" in argv:
            return (0, json.dumps({"journals": [{"id": "old", "text": "Today is a quiet Tuesday at home", "created_at": old_ms}], "next_cursor": None}), "")
        if "list" in argv:
            return (0, json.dumps({"conversations": [{"id": 5, "start_time": now_ms - 3600_000}], "next_cursor": None}), "")
        if "get" in argv:
            return (0, json.dumps({"conversation": {"id": 5, "start_time": now_ms - 3600_000, "transcriptions": [{"utterances": [
                {"text": "bellwether check in for today " + "and a long walk by the river " * 25, "speaker": "Unknown", "spoken_at": now_ms - 3500_000}]}]}}), "")
        return (1, "", "unexpected")

    cli = BeeCli(runner=runner)
    cli.installed = lambda: True  # type: ignore[method-assign]
    sent = []
    first_day(cli, post=lambda d, p: sent.append((p, [r["date"] for r in d])) or {"stored": 1}, reduce=reduce_to_days,
              log=lambda s: None, days=2)
    old_day = time.strftime("%Y-%m-%d", time.gmtime(old_ms / 1000))
    assert sent and all(old_day not in dates for _, dates in sent)
