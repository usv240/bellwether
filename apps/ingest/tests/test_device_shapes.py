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


def test_backfill_pages_the_whole_history_and_fetches_every_row():
    """``bee changed`` with no cursor answers with recent changes only: the
    first pull after ten days on the wrist, 2026-10-08, came back with two
    days of 132 conversations. The backfill pages ``conversations list``
    to the end and fetches each row for its words."""
    from bellwether_ingest.bee import OwnerFilter, ingest_backfill

    pages = {
        None: {"conversations": [LIST_ROW, {**LIST_ROW, "id": 2}], "next_cursor": "p2"},
        "p2": {"conversations": [{**LIST_ROW, "id": 3}], "next_cursor": None},
    }
    gets: list[str] = []

    def runner(argv: list[str]):
        if "list" in argv:
            cursor = argv[argv.index("--cursor") + 1] if "--cursor" in argv else None
            return (0, json.dumps(pages[cursor]), "")
        if "get" in argv:
            gets.append(argv[argv.index("get") + 1])
            return (0, json.dumps(get_response(4)), "")
        return (1, "", "unexpected")

    utts = ingest_backfill(BeeCli(runner=runner), OwnerFilter())
    assert sorted(gets) == ["10824219", "2", "3"]
    assert len(utts) == 12


def test_long_sessions_and_media_are_not_taken_for_the_wearer():
    """Every speaker on the account is Unknown, so the backfill can only
    drop what is plainly not the wearer: a six-hour training, a film."""
    from bellwether_ingest.bee import keep_conversation

    hour = 3_600_000
    talk = {**LIST_ROW, "end_time": LIST_ROW["start_time"] + 20 * 60_000, "short_summary": "Planning a birthday"}
    training = {**talk, "end_time": talk["start_time"] + 6 * hour, "short_summary": "Leadership training"}
    film = {**talk, "short_summary": "Watching a movie with friends"}
    assert keep_conversation(talk, 60) is True
    assert keep_conversation(training, 60) is False
    assert keep_conversation(film, 60) is False


def test_voice_notes_are_the_wearers_own_speech_and_stamped_when_made():
    """Bee voice notes are recorded by the wearer on purpose, so they are
    the one stream whose speaker is certain while every conversation
    utterance reads Unknown. Shape from bee-cli 0.7.3's journals resource:
    id, text, created_at in epoch milliseconds."""
    from bellwether_ingest.bee import WEARER, ingest_journals

    pages = {
        None: {"journals": [
            {"id": "j1", "text": "Today I walked to the market and talked with my sister.",
             "state": "processed", "created_at": 1791400000000, "updated_at": 1791400000000},
            {"id": "j2", "text": None, "state": "processing", "created_at": 1791401000000},
        ], "next_cursor": "n2"},
        "n2": {"journals": [
            {"id": "j3", "text": "A quieter day, mostly reading.", "state": "processed",
             "created_at": 1791486400000, "updated_at": 1791486400000},
        ], "next_cursor": None},
    }

    def runner(argv: list[str]):
        if "journals" in argv:
            cursor = argv[argv.index("--cursor") + 1] if "--cursor" in argv else None
            return (0, json.dumps(pages[cursor]), "")
        return (1, "", "unexpected")

    utts = ingest_journals(BeeCli(runner=runner))
    assert [u.conversation_id for u in utts] == ["journal-j1", "journal-j3"]
    assert all(u.speaker == WEARER for u in utts)
    assert utts[0].ts.startswith("2026-10-07") and utts[1].ts.startswith("2026-10-08")


def test_post_sends_only_the_day_rows(monkeypatch):
    """--post carries exactly what --out would write: feature rows with a
    date and a count, and no field that could hold the words."""
    import urllib.request

    from bellwether_ingest.cli import post_days

    sent = {}

    class Res:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"stored": 1, "profile_id": "me-voice", "tier": "learning", "eligible_days": 1}'

    def fake_urlopen(req, timeout):
        sent["url"], sent["body"] = req.full_url, json.loads(req.data)
        return Res()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    row = {"date": "2026-10-13", "utterances": 3, "token_count_day": 180, "mattr": 0.7}
    res = post_days([row], "me-voice", "https://api.example/")
    assert sent["url"] == "https://api.example/v1/profiles/me-voice/days"
    assert sent["body"] == [row]
    assert res["tier"] == "learning"


def _checkin_runner(conv_start_ms: int, session_text: str, note_text: str = "Today is Wednesday and I am recording my note", note_ms: int = 1792090293000):
    """A note, and one conversation whose words may or may not open with it."""
    def runner(argv: list[str]):
        if "journals" in argv:
            return (0, json.dumps({"journals": [{"id": "n1", "text": note_text, "state": "READY", "created_at": note_ms}], "next_cursor": None}), "")
        if "conversations" in argv and "list" in argv:
            return (0, json.dumps({"conversations": [{"id": 77, "start_time": conv_start_ms, "end_time": conv_start_ms + 120000, "utterances_count": 3}], "next_cursor": None}), "")
        if "conversations" in argv and "get" in argv:
            words = session_text.split()
            utts = [{"text": " ".join(words[i:i + 6]), "speaker": "Unknown", "spoken_at": conv_start_ms + i * 4000} for i in range(0, len(words), 6)]
            return (0, json.dumps({"conversation": {"id": 77, "start_time": conv_start_ms, "transcriptions": [{"utterances": utts}]}}), "")
        return (1, "", "unexpected")
    return runner


def test_a_check_in_is_the_note_plus_the_session_it_anchors():
    """The band opened a session 18 seconds after the note and its first
    words are the note's words: that session is the wearer's check-in."""
    from bellwether_ingest.bee import WEARER, ingest_checkins

    note_ms = 1792090293000
    session = "today is wednesday and i am recording my note the morning was quiet and I walked to the market and then worked on the project until lunch"
    utts = ingest_checkins(BeeCli(runner=_checkin_runner(note_ms + 18000, session)))
    assert [u.conversation_id for u in utts][:2] == ["journal-n1", "checkin-77"]
    assert all(u.speaker == WEARER for u in utts)
    assert sum(len(u.text.split()) for u in utts) > 20


def test_a_session_that_does_not_open_with_the_note_is_not_a_check_in():
    """Same minute, different words: a conversation that happened to start
    near the note, not the wearer's check-in."""
    from bellwether_ingest.bee import ingest_checkins

    note_ms = 1792090293000
    utts = ingest_checkins(BeeCli(runner=_checkin_runner(note_ms + 18000, "could you pass the salt the eggs are bland and the train was late again this morning")))
    assert [u.conversation_id for u in utts] == ["journal-n1"]


def test_a_session_that_started_long_before_the_note_is_not_a_check_in():
    """On 2026-10-13 the two notes matched a 596-utterance session that had
    started fourteen minutes earlier: a meeting the wearer spoke in, not a
    check-in. The start window keeps it out."""
    from bellwether_ingest.bee import ingest_checkins

    note_ms = 1792090293000
    session = "today is wednesday and i am recording my note and then a long meeting continues"
    utts = ingest_checkins(BeeCli(runner=_checkin_runner(note_ms - 14 * 60000, session)))
    assert [u.conversation_id for u in utts] == ["journal-n1"]


def test_a_check_in_keeps_ten_minutes_and_not_the_rest_of_the_day():
    from bellwether_ingest.bee import ingest_checkins

    note_ms = 1792090293000
    session = "today is wednesday and i am recording my note " + "and more words follow for a long time " * 60
    utts = ingest_checkins(BeeCli(runner=_checkin_runner(note_ms + 5000, session)))
    kept = [u for u in utts if u.conversation_id == "checkin-77"]
    from bellwether_ingest.bee import _ms
    assert kept and max(_ms(u.ts) for u in kept) <= note_ms + 10 * 60000
    assert len(kept) < 70  # the session ran about 7 minutes of utterances; most are inside the window


def test_a_one_word_note_anchors_nothing():
    from bellwether_ingest.bee import ingest_checkins

    note_ms = 1792090293000
    utts = ingest_checkins(BeeCli(runner=_checkin_runner(note_ms + 5000, "okay so the morning was quiet", note_text="okay")))
    assert [u.conversation_id for u in utts] == ["journal-n1"]


def test_a_session_the_wearer_opens_by_declaring_it_is_a_check_in():
    """No voice note at all. The session's first words say what it is,
    which is what the wearer on this account does naturally: "vlog for
    October 17", "today's vlog", "log voice note for October 16"."""
    from bellwether_ingest.bee import WEARER, checkins_from

    def rec(cid, start_ms, text):
        words = text.split()
        utts = [{"text": " ".join(words[i:i + 6]), "speaker": "Unknown", "spoken_at": start_ms + i * 4000} for i in range(0, len(words), 6)]
        return {"id": cid, "start_time": start_ms, "transcriptions": [{"utterances": utts}]}

    records = [
        rec(1, 1792300000000, "vlog for october seventeenth around nine pm continuing my last voice note i woke up late and worked through the afternoon"),
        rec(2, 1792310000000, "could you pass the salt the eggs are bland and the train was late again"),
        rec(3, 1792320000000, "so anyway as i was saying yesterday in my vlog the meeting ran long"),
    ]
    utts = checkins_from([], records)
    assert {u.conversation_id for u in utts} == {"checkin-1"}
    assert all(u.speaker == WEARER for u in utts)


def test_a_hosted_check_in_keeps_the_wearers_answers_and_drops_the_hosts_lines(tmp_path):
    """A voice assistant opened the session: it spoke the day's opener, three
    numbered questions and a closing, and the wearer answered each. The
    opener anchors the session; every host line, including one the device
    cut in two and the date it heard as digits, is removed; the answers
    stay. A host file with an extra, unscripted line is honoured too."""
    import json

    from speech_vitals.elicitation import host_lines_for

    from bellwether_ingest.bee import WEARER, checkins_from, load_host_lines

    start_ms = 1792350000000  # 2026-10-18 UTC
    from datetime import datetime, timezone
    day = datetime.fromtimestamp(start_ms / 1000, timezone.utc).date()
    host = host_lines_for(day)
    answers = [
        "I woke up around seven and had tea and then I walked to the station because the car is in the garage.",
        "There is a desk with two monitors and a window on the left with a plant on the sill and a lamp.",
        "First I boil the kettle then I grind the beans then I pour slowly and wait about four minutes.",
    ]
    extra = "Take your time, there is no hurry at all."
    heard = [
        host[0].replace("nineteenth", "19th").replace("eighteenth", "18th").replace("check-in", "check in"),
        host[1], host[2], answers[0],
        host[3], " ".join(host[4].split()[:6]), " ".join(host[4].split()[6:]), extra, answers[1],
        host[5], host[6], answers[2],
        host[7],
    ]
    utts = [{"text": t, "speaker": "Unknown", "spoken_at": start_ms + i * 9000} for i, t in enumerate(heard)]
    records = [{"id": 9, "start_time": start_ms, "transcriptions": [{"utterances": utts}]}]

    hf = tmp_path / ".bellwether-host.json"
    hf.write_text(json.dumps({day.isoformat(): [extra]}), encoding="utf-8")

    kept = checkins_from([], records, host_lines=load_host_lines(str(hf)))
    assert [u.text for u in kept] == answers
    assert all(u.speaker == WEARER and u.conversation_id == "hosted-9" for u in kept)

    # Without the host file the unscripted line stays; everything scripted still goes.
    kept2 = [u.text for u in checkins_from([], records)]
    assert kept2 == [answers[0], extra, answers[1], answers[2]]


def test_mine_reads_the_device_once_and_finds_check_ins_in_the_same_records():
    from bellwether_ingest.bee import ingest_checkins

    calls = []

    def runner(argv):
        calls.append(argv)
        if "journals" in argv:
            return (0, json.dumps({"journals": [], "next_cursor": None}), "")
        return (1, "", "unexpected")

    records = [{"id": 9, "start_time": 1792300000000, "transcriptions": [{"utterances": [
        {"text": "bellwether check in for friday i walked to the shops", "speaker": "Unknown", "spoken_at": 1792300001000}]}]}]
    utts = ingest_checkins(BeeCli(runner=runner), records=records)
    assert [u.conversation_id for u in utts] == ["checkin-9"]
    assert not [a for a in calls if "conversations" in a]


def _tonight_shaped_session(start_ms):
    """The shape of the first live hosted check-in, 2026-10-19, with the
    wearer's answers replaced: the band was already recording when the host
    began; it merged the opener, "Question one" and the first prompt into
    one utterance and misheard parts of it; it wrote "Question 2"; it merged
    the third question with its prompt; it split and garbled the closing;
    and the wearer went on talking afterwards."""
    s = start_ms
    rows = [
        (0, "okay so the band is on now"), (3, "testing"),
        (175, "Phone number checked in October 19th. Question one. Tell me about your day so far, from when you can vote us right now."),
        (185, "I woke up late and made tea, then I spent the morning on the project and walked to the shop at noon."),
        (212, "After lunch I fixed two bugs and called my brother for a while."),
        (229, "Question 2."),
        (231, "Describe what you can see from the nearest window, in as much detail as you can."),
        (238, "There is a street light, a parked car and the dark outline of the trees across the road."),
        (245, "In the day you can see the hills and a school behind the houses."),
        (281, "Question third, explain how do you plan a day out for a visitor who has never been to your town."),
        (290, "I would start with breakfast at the market, then the river walk and the museum."),
        (316, "For someone who has never been to the town I would end with dinner by the water."),
        (332, "Thank you."), (334, "That is to this check."),
        (336, "No matter what kind of life the Bee has written you down."),
        (343, "right, that was the check-in, now back to work on the slides for tomorrow"),
    ]
    utts = [{"text": t, "speaker": "Unknown", "spoken_at": s + k * 1000} for k, t in rows]
    return {"id": 11, "start_time": s, "transcriptions": [{"utterances": utts}]}


def test_a_hosted_check_in_inside_an_open_session_by_timing():
    from bellwether_ingest.bee import checkins_from

    start = 1792383085000  # 2026-10-19 04:11 UTC
    rec = _tonight_shaped_session(start)
    # When the host played each line, two seconds ahead of the device's clock.
    plays = [(173.0, 175.5), (176.4, 177.5), (178.1, 181.3), (227.0, 228.1), (229.0, 233.2),
             (278.9, 280.0), (280.8, 284.8), (330.6, 336.4)]
    spans = [(start + int(a * 1000), start + int(b * 1000), "") for a, b in plays]
    kept = [u.text for u in checkins_from([], [rec], host_spans=spans)]
    assert kept == [rec["transcriptions"][0]["utterances"][i]["text"] for i in (3, 4, 7, 8, 10, 11)]


def test_a_hosted_check_in_inside_an_open_session_by_text_alone():
    """No timing recorded (a host elsewhere, an Echo): the misheard opener
    is still found mid-session, the misheard lines still dropped, the
    wearer's echo of a question kept, and the check-in ends at the closing."""
    from bellwether_ingest.bee import checkins_from

    start = 1792383085000
    rec = _tonight_shaped_session(start)
    kept = [u.text for u in checkins_from([], [rec])]
    assert kept == [rec["transcriptions"][0]["utterances"][i]["text"] for i in (3, 4, 7, 8, 10, 11)]
