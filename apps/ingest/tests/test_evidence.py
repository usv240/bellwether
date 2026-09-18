"""The evidence file is publishable even though its input never could be.

Bee data is somebody's day. A transcript of real conversations is the most
sensitive thing this project will ever touch, and the entire premise is
that it does not leave the machine. This file is therefore designed to be
committed to a public repository, which means the redaction has to be a
property that is tested rather than a habit that is followed.

The test that matters feeds the capture a conversation full of real
sentences and asserts that not one of those words appears anywhere in the
output, including in fields nobody thought of as text.
"""

from __future__ import annotations

import json

from bellwether_ingest.bee import BeeCli
from bellwether_ingest.evidence import capture, redact, to_markdown

SECRET_SENTENCES = [
    "I saw Doctor Ramirez about the pain in my shoulder on Tuesday",
    "my daughter Priya is flying in from Chicago next weekend",
    "the account number is four four seven two and the password is hunter two",
]


def conversation() -> dict:
    return {
        "id": "conv-1",
        "title": SECRET_SENTENCES[0],
        "summary": SECRET_SENTENCES[1],
        "start_time": "2026-09-20T09:00:00Z",
        "utterances": [
            {"speaker": "speaker_1", "text": text, "start_time": f"2026-09-20T09:0{i}:00Z"}
            for i, text in enumerate(SECRET_SENTENCES)
        ],
    }


OTHER_SENTENCES = [
    "we drove past the lighthouse before breakfast yesterday morning",
    "Kenji brought marmalade sandwiches to the allotment committee",
    "quarterly turnover exceeded projections despite shipping delays",
]


def conversation_of(sentences: list[str]) -> dict:
    return {
        "id": "conv-2",
        "title": sentences[0],
        "summary": sentences[1],
        "start_time": "2026-09-21T09:00:00Z",
        "utterances": [
            {"speaker": "speaker_1", "text": text, "start_time": f"2026-09-21T09:0{i}:00Z"}
            for i, text in enumerate(sentences)
        ],
    }


def runner_for(sentences: list[str]):
    def inner(argv: list[str]) -> tuple[int, str, str]:
        joined = " ".join(argv)
        if "me" in joined:
            return (0, json.dumps({"id": "u2", "name": "Other", "email": "x@y.z"}), "")
        if "now" in joined:
            return (0, json.dumps({"conversations": [conversation_of(sentences)]}), "")
        if "conversations" in joined:
            return (0, json.dumps([conversation_of(sentences)]), "")
        return (1, "", "unexpected")

    return inner


def runner(argv: list[str]) -> tuple[int, str, str]:
    joined = " ".join(argv)
    if "me" in joined:
        return (0, json.dumps({"id": "u1", "name": "Ujwal", "email": "a@b.c"}), "")
    if "now" in joined:
        return (0, json.dumps({"conversations": [conversation()]}), "")
    if "conversations" in joined:
        return (0, json.dumps([conversation()]), "")
    return (1, "", "unexpected")


def words_of(text: str) -> set[str]:
    return {w.strip(".,").lower() for w in text.split() if len(w.strip(".,")) >= 4}


def test_no_word_from_the_transcript_reaches_the_output():
    """Isolate the file's own vocabulary from the speaker's.

    Substring-matching the secrets against the whole file flags words the
    template itself uses: the call label "account", the sentence "only the
    numbers left the machine". Those are false alarms and a test that
    cries wolf gets deleted.

    So the capture runs twice over two completely different conversations.
    Any word appearing in both outputs belongs to the template, because no
    word is in both transcripts. Anything left that also appears in a
    transcript is a real leak.
    """
    first = capture(BeeCli(runner=runner))
    second = capture(BeeCli(runner=runner_for(OTHER_SENTENCES)))

    blob_a = json.dumps(first) + to_markdown(first)
    blob_b = json.dumps(second) + to_markdown(second)
    template = words_of(blob_a) & words_of(blob_b)

    leaked = set()
    for sentence in SECRET_SENTENCES:
        for word in words_of(sentence):
            if word in words_of(blob_a) and word not in template:
                leaked.add(word)
    assert not leaked, f"transcript words reached the evidence: {sorted(leaked)}"

    # A redaction test that checked nothing would pass silently, which is
    # the worst possible outcome for this particular test.
    assert len(words_of(" ".join(SECRET_SENTENCES))) >= 15


def test_names_and_contact_details_do_not_survive_either():
    data = capture(BeeCli(runner=runner))
    blob = json.dumps(data) + to_markdown(data)
    for secret in ("Ujwal", "a@b.c", "Ramirez", "Priya", "Chicago", "hunter"):
        assert secret.lower() not in blob.lower()


def test_a_title_is_treated_as_speech_because_it_usually_is():
    # A conversation title is a string, and a title is often a sentence
    # somebody actually said. The redactor must not trust field names.
    out = redact({"title": "I saw Doctor Ramirez about the pain"})
    assert "Ramirez" not in json.dumps(out)
    assert "chars" in json.dumps(out)


def test_the_numbers_do_survive_because_they_are_the_point():
    data = capture(BeeCli(runner=runner))
    assert data["days"], "a day with speech should produce a feature row"
    day = data["days"][0]
    assert day["token_count_day"] > 0
    for name in ("mattr", "mean_utt_len", "filler_rate"):
        assert name in day


def test_the_file_states_words_read_against_words_published():
    data = capture(BeeCli(runner=runner))
    assert data["totals"]["wordsSeen"] > 0
    assert data["totals"]["wordsPublished"] == 0
    assert "Words written to this file: 0" in to_markdown(data)


def test_a_failed_command_is_recorded_rather_than_hidden():
    def broken(argv: list[str]) -> tuple[int, str, str]:
        return (1, "", "bee exploded")

    data = capture(BeeCli(runner=broken))
    assert all(c["ok"] is False for c in data["calls"])
    assert "failed" in to_markdown(data)
