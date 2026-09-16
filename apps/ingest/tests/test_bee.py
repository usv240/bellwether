"""Bee integration tests, without a device.

Two kinds of claim are pinned here. First, that every shape the Bee docs
describe (and the plausible alternates a real device might emit) normalises
to the same Utterance. Second, that each BeeCli method produces exactly the
argv the Bee CLI documents, so the code-level integration the track requires
is asserted rather than assumed. A fake runner stands in for the binary.
"""

from __future__ import annotations

import json

import pytest

from bellwether_ingest import (
    BeeCli,
    BeeCliError,
    BeeNotAuthenticated,
    CursorStore,
    OwnerFilter,
    ingest_changed,
    ingest_now,
    normalize_conversation,
    normalize_utterance,
    parse_stream_line,
    parse_sync_markdown,
    speaker_label,
    to_iso,
)
from bellwether_ingest.cli import reduce_to_days
from speech_vitals import Utterance

# ---- normalisation ---------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2026-09-16T08:12:03Z", "2026-09-16T08:12:03Z"),
        ("2026-09-16T08:12:03+00:00", "2026-09-16T08:12:03Z"),
        ("2026-09-16T10:12:03+02:00", "2026-09-16T08:12:03Z"),
        (1789732323, "2026-09-18T11:52:03Z"),
        (1789732323000, "2026-09-18T11:52:03Z"),
        ("1789732323000", "2026-09-18T11:52:03Z"),
        (None, None),
        ("", None),
        ("not a time", None),
    ],
)
def test_to_iso_accepts_every_documented_time_shape(value, expected):
    assert to_iso(value) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("speaker_1", "speaker_1"),
        ("Speaker 1", "speaker_1"),
        ("SPEAKER-2", "speaker_2"),
        ({"id": "speaker_1", "name": "Alex"}, "speaker_1"),
        ({"name": "Alex"}, "alex"),
        ({"label": "Speaker 3"}, "speaker_3"),
        (None, None),
        ("", None),
    ],
)
def test_speaker_label_is_stable_across_shapes(raw, expected):
    assert speaker_label(raw) == expected


def test_normalize_utterance_documented_shape():
    u = normalize_utterance(
        {"text": "Good morning.", "speaker": "speaker_1", "start_time": "2026-09-16T08:00:00Z", "end_time": "2026-09-16T08:00:02Z"},
        conversation_id="c1",
    )
    assert u == Utterance(ts="2026-09-16T08:00:00Z", text="Good morning.", speaker="speaker_1", conversation_id="c1")


def test_normalize_utterance_alternate_shapes():
    assert normalize_utterance({"content": "Hi", "speaker": {"id": "speaker_2"}, "created_at": 1789732323000}).speaker == "speaker_2"
    assert normalize_utterance({"text": "Hi", "timestamp": "2026-01-01T00:00:00Z"}).ts == "2026-01-01T00:00:00Z"
    assert normalize_utterance({"text": "Hi"}, fallback_ts="2026-01-02T00:00:00Z").ts == "2026-01-02T00:00:00Z"


def test_normalize_utterance_rejects_empty_or_timeless():
    assert normalize_utterance({"text": "   ", "start_time": "2026-01-01T00:00:00Z"}) is None
    assert normalize_utterance({"text": "Hi"}) is None
    assert normalize_utterance("not a dict") is None


def test_normalize_conversation_flat_and_nested():
    flat = {
        "id": "c1",
        "start_time": "2026-09-16T08:00:00Z",
        "utterances": [
            {"text": "Second", "speaker": "speaker_1", "start_time": "2026-09-16T08:00:05Z"},
            {"text": "First", "speaker": "speaker_2", "start_time": "2026-09-16T08:00:01Z"},
            {"text": "No time, uses conversation start", "speaker": "speaker_1"},
        ],
    }
    out = normalize_conversation(flat)
    assert [u.text for u in out] == ["No time, uses conversation start", "First", "Second"]
    assert all(u.conversation_id == "c1" for u in out)

    nested = {"uuid": "c2", "transcriptions": [{"utterances": [{"text": "Nested", "speaker": "speaker_1", "start_time": "2026-09-16T09:00:00Z"}]}]}
    assert normalize_conversation(nested)[0].conversation_id == "c2"


def test_parse_sync_markdown():
    md = """# Conversation
- id: 42
## Summary
Talked about the garden.
### Transcription 1
- Speaker 1: The roses came up early this year.
- Speaker 2: They did, didn't they?
- Speaker 1: I should, um, cut them back.
## Suggested links
- Speaker 1: this is not a transcript line
"""
    out = parse_sync_markdown(md, conversation_id="42", day="2026-09-16")
    assert [u.speaker for u in out] == ["speaker_1", "speaker_2", "speaker_1"]
    assert out[0].text == "The roses came up early this year."
    assert all(u.ts == "2026-09-16T00:00:00Z" for u in out)
    assert len(out) == 3  # the line under Suggested links is not a transcript


def test_parse_stream_line_only_new_utterances():
    ev = json.dumps({"type": "new-utterance", "conversation_uuid": "c9", "utterance": {"text": "Live", "speaker": "speaker_1", "start_time": "2026-09-16T10:00:00Z"}})
    u = parse_stream_line(ev)
    assert u.text == "Live" and u.conversation_id == "c9"
    assert parse_stream_line(json.dumps({"type": "update-conversation", "id": "c9"})) is None
    assert parse_stream_line("") is None
    assert parse_stream_line("not json") is None


# ---- owner isolation -------------------------------------------------------


def test_owner_filter_uses_configured_label_or_most_frequent():
    us = [
        Utterance("2026-09-16T08:00:00Z", "a", "speaker_1"),
        Utterance("2026-09-16T08:00:01Z", "b", "speaker_1"),
        Utterance("2026-09-16T08:00:02Z", "c", "speaker_2"),
    ]
    assert OwnerFilter().resolve(us) == "speaker_1"
    assert [u.text for u in OwnerFilter().apply(us)] == ["a", "b"]
    assert [u.text for u in OwnerFilter("Speaker 2").apply(us)] == ["c"]
    assert OwnerFilter().apply([]) == []


# ---- cursor ----------------------------------------------------------------


def test_cursor_store_roundtrip_holds_only_a_token(tmp_path):
    store = CursorStore(str(tmp_path / ".bee-cursor"))
    assert store.load() is None
    store.save("abc123")
    assert store.load() == "abc123"
    assert json.loads((tmp_path / ".bee-cursor").read_text()) == {"cursor": "abc123"}


# ---- the CLI, with a fake binary -------------------------------------------


class FakeRunner:
    """Maps the argv tail (after the binary and any cmd /c shim) to a result
    and records every call so tests can assert the exact Bee invocation."""

    def __init__(self, responses: dict[tuple, object], not_logged_in: bool = False):
        self.responses = responses
        self.calls: list[list[str]] = []
        self.not_logged_in = not_logged_in

    def __call__(self, argv: list[str]):
        tail = argv[:]
        if tail[:2] == ["cmd", "/c"]:
            tail = tail[2:]
        tail = tail[1:]  # drop the binary path
        self.calls.append(tail)
        if self.not_logged_in:
            return 1, "", "Not logged in."
        key = tuple(tail)
        if key not in self.responses:
            return 1, "", f"unexpected: {tail}"
        body = self.responses[key]
        return 0, json.dumps(body) if not isinstance(body, str) else body, ""


def test_bee_cli_produces_the_documented_argv():
    runner = FakeRunner({
        ("me", "--json"): {"id": "u1"},
        ("now", "--json"): {"conversations": []},
        ("changed", "--json"): {"items": []},
        ("changed", "--cursor", "cur1", "--json"): {"items": []},
        ("conversations", "list", "--limit", "10", "--json"): {"conversations": []},
        ("conversations", "get", "c1", "--json"): {"id": "c1"},
        ("conversations", "transcript", "c1", "--json"): {"utterances": []},
        ("conversations", "transcript", "c1", "--since", "1700000000000", "--json"): {"utterances": []},
    })
    cli = BeeCli(runner=runner)
    cli.me(); cli.now(); cli.changed(); cli.changed("cur1")
    cli.conversations_list(limit=10); cli.conversation_get("c1")
    cli.conversation_transcript("c1"); cli.conversation_transcript("c1", since_ms=1700000000000)
    assert runner.calls == [
        ["me", "--json"],
        ["now", "--json"],
        ["changed", "--json"],
        ["changed", "--cursor", "cur1", "--json"],
        ["conversations", "list", "--limit", "10", "--json"],
        ["conversations", "get", "c1", "--json"],
        ["conversations", "transcript", "c1", "--json"],
        ["conversations", "transcript", "c1", "--since", "1700000000000", "--json"],
    ]


def test_bee_cli_reports_not_logged_in_distinctly():
    cli = BeeCli(runner=FakeRunner({}, not_logged_in=True))
    with pytest.raises(BeeNotAuthenticated):
        cli.now()


def test_bee_cli_reports_bad_json_and_failures():
    cli = BeeCli(runner=FakeRunner({("now", "--json"): "this is not json"}))
    with pytest.raises(BeeCliError):
        cli.now()
    cli2 = BeeCli(runner=FakeRunner({}))
    with pytest.raises(BeeCliError):
        cli2.me()


def test_ingest_changed_end_to_end_with_owner_and_cursor(tmp_path):
    runner = FakeRunner({
        ("changed", "--json"): {
            "items": [
                {"type": "conversation", "id": "c1"},
                {"type": "todo", "id": "t9"},
                {"entity": "Conversation", "entity_id": "c2"},
            ],
            "next_cursor": "cur-next",
        },
        ("conversations", "transcript", "c1", "--json"): {
            "utterances": [
                {"text": "Mine one", "speaker": "speaker_1", "start_time": "2026-09-16T08:00:00Z"},
                {"text": "Theirs", "speaker": "speaker_2", "start_time": "2026-09-16T08:00:01Z"},
                {"text": "Mine two", "speaker": "speaker_1", "start_time": "2026-09-16T08:00:02Z"},
            ]
        },
        ("conversations", "transcript", "c2", "--json"): [
            {"text": "Mine three", "speaker": "speaker_1", "start_time": "2026-09-17T08:00:00Z"},
        ],
    })
    cli = BeeCli(runner=runner)
    cursors = CursorStore(str(tmp_path / ".bee-cursor"))
    utterances, new_cursor = ingest_changed(cli, cursors, OwnerFilter())
    assert [u.text for u in utterances] == ["Mine one", "Mine two", "Mine three"]
    assert new_cursor == "cur-next"
    # The cursor is not saved by ingest_changed: the caller saves it after
    # features are persisted, which is what makes processing exactly-once.
    assert cursors.load() is None
    # The todo was never fetched as a conversation.
    assert ["conversations", "transcript", "t9", "--json"] not in runner.calls


def test_ingest_now_reduces_to_features_without_retaining_text():
    runner = FakeRunner({
        ("now", "--json"): {"conversations": [{
            "id": "c1", "start_time": "2026-09-16T08:00:00Z",
            "utterances": [
                {"text": "The garden looked lovely this evening, and the roses had opened.", "speaker": "speaker_1", "start_time": "2026-09-16T18:00:00Z"},
                {"text": "It did.", "speaker": "speaker_2", "start_time": "2026-09-16T18:00:03Z"},
            ],
        }]},
    })
    utterances = ingest_now(BeeCli(runner=runner), OwnerFilter())
    days = reduce_to_days(utterances)
    assert len(days) == 1 and days[0]["date"] == "2026-09-16"
    assert days[0]["utterances"] == 1
    assert "garden" not in json.dumps(days)
