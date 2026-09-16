"""speech-vitals tests.

The claims under test are the ones a reviewer of a doctor report would
need: that the numbers are deterministic, that each feature measures what
its docstring says, that degenerate days do not crash or lie, and that
nothing in a DayFeatures record can give a sentence back.
"""

from __future__ import annotations

import json
from dataclasses import fields

import pytest

from speech_vitals import (
    FEATURE_NAMES,
    DayFeatures,
    Utterance,
    aggregate_day,
    extract_utterance,
    features_schema,
    mattr,
)
from speech_vitals.cli import main


def utt(text: str, ts: str = "2026-09-16T08:00:00Z", speaker: str = "speaker_1") -> Utterance:
    return Utterance(ts=ts, text=text, speaker=speaker)


# ---- extract_utterance -----------------------------------------------------


def test_counts_words_and_tokens_on_a_plain_sentence():
    f = extract_utterance("The quick brown fox jumped over the lazy dog.")
    assert f.words == 9
    assert f.tokens == 10  # the full stop is a token but not a word
    assert f.fillers == 0
    assert f.disfluencies == 0


def test_fillers_are_counted_lexically():
    f = extract_utterance("Um, I think, uh, we should, er, go now.")
    assert f.fillers == 3


def test_adjacent_repetition_is_a_disfluency_but_repeated_fillers_are_not():
    f = extract_utterance("I went to the the shop.")
    assert f.disfluencies == 1
    g = extract_utterance("Um um I went to the shop.")
    assert g.disfluencies == 0
    assert g.fillers == 2


def test_broken_off_word_is_a_disfluency():
    f = extract_utterance("I wan- I want to go home.")
    assert f.disfluencies >= 1


def test_pronoun_heavy_speech_has_more_pronouns_than_nouns():
    heavy = extract_utterance("He gave it to them and they put it there.")
    plain = extract_utterance("The doctor gave the letter to the nurse at the desk.")
    assert heavy.pronouns > heavy.nouns
    assert plain.nouns > plain.pronouns


def test_rare_words_are_counted_and_common_words_are_not():
    f = extract_utterance("The professor's soliloquy was ineffable.")
    assert f.low_freq_words >= 2  # soliloquy, ineffable
    g = extract_utterance("The man went to the shop and bought some bread.")
    assert g.low_freq_words == 0


def test_proper_nouns_do_not_count_as_rare_vocabulary():
    # A friend's name is rare in a corpus; it is not sophisticated vocabulary.
    f = extract_utterance("I spoke to Zbigniew about the garden.")
    assert f.low_freq_words == 0


def test_dependency_depth_grows_with_subordination():
    flat = extract_utterance("The dog barked.")
    nested = extract_utterance(
        "The dog that lived next to the house which my uncle bought barked because it heard a noise."
    )
    assert nested.dep_depth_max > flat.dep_depth_max


def test_extraction_is_deterministic():
    text = "Well, um, I suppose the weather has been rather changeable lately."
    assert extract_utterance(text) == extract_utterance(text)


def test_empty_text_does_not_crash():
    f = extract_utterance("")
    assert f.words == 0 and f.tokens == 0


# ---- mattr -----------------------------------------------------------------


def test_mattr_is_one_for_all_distinct_tokens():
    assert mattr([f"w{i}" for i in range(120)]) == pytest.approx(1.0)


def test_mattr_is_minimal_for_one_repeated_token():
    assert mattr(["a"] * 120, window=50) == pytest.approx(1 / 50)


def test_mattr_falls_back_to_ttr_for_short_streams():
    assert mattr(["a", "b", "a", "c"], window=50) == pytest.approx(3 / 4)


def test_mattr_does_not_fall_as_a_day_gets_longer():
    # Plain TTR would collapse here; MATTR is length-stable by construction.
    pattern = [f"w{i % 40}" for i in range(80)]
    short = mattr(pattern[:60])
    long = mattr(pattern * 5)
    assert abs(short - long) < 0.05


def test_mattr_empty():
    assert mattr([]) == 0.0


# ---- aggregate_day ---------------------------------------------------------


def test_aggregate_day_rates_and_shapes():
    day = aggregate_day(
        [
            utt("The tall man quickly ran and jumped over the fence."),
            utt("Um, then he, uh, sat down and, er, rested."),
        ]
    )
    assert isinstance(day, DayFeatures)
    assert day.date == "2026-09-16"
    assert day.utterances == 2
    assert day.token_count_day > 0
    assert 0.0 < day.mattr <= 1.0
    assert day.mean_utt_len == pytest.approx(day.token_count_day / 2, abs=1e-6)
    assert day.filler_rate > 0
    assert day.idea_density > 3.0  # verbs, adjectives, adverbs, prepositions, conjunctions


def test_empty_day_is_zeros_not_an_error():
    day = aggregate_day([], date="2026-09-01")
    assert day.utterances == 0
    assert day.token_count_day == 0
    assert day.mattr == 0.0
    assert day.date == "2026-09-01"


def test_a_day_of_only_punctuation_is_an_empty_day():
    day = aggregate_day([utt("..."), utt("!!")])
    assert day.token_count_day == 0


def test_day_features_carry_no_words():
    """The privacy guarantee, as a test: no field of DayFeatures is a string
    other than the date, and none can hold text."""
    day = aggregate_day([utt("A secret sentence that must not survive.")])
    for f in fields(DayFeatures):
        value = getattr(day, f.name)
        if f.name == "date":
            continue
        assert isinstance(value, (int, float)), f.name
    assert "secret" not in json.dumps(day.to_dict())


def test_aggregate_is_deterministic_and_order_independent():
    a = [utt("First thing said.", "2026-09-16T08:00:00Z"), utt("Second thing said.", "2026-09-16T09:00:00Z")]
    assert aggregate_day(a) == aggregate_day(list(reversed(a)))


# ---- schema ----------------------------------------------------------------


def test_schema_covers_every_feature_with_direction_and_basis():
    schema = features_schema()
    names = {s["name"] for s in schema}
    assert names == set(FEATURE_NAMES)
    for s in schema:
        assert s["direction"] in ("lower_is_concerning", "higher_is_concerning")
        assert len(s["basis"]) > 20
        assert len(s["plain"]) > 10


def test_every_feature_in_schema_exists_on_day_features():
    day_fields = {f.name for f in fields(DayFeatures)}
    for name in FEATURE_NAMES:
        assert name in day_fields, name


# ---- cli -------------------------------------------------------------------


def test_cli_analyze_groups_by_day_and_filters_speaker(tmp_path, capsys):
    p = tmp_path / "t.jsonl"
    rows = [
        {"ts": "2026-09-16T08:00:00Z", "text": "Good morning, how did you sleep?", "speaker": "speaker_1"},
        {"ts": "2026-09-16T08:00:05Z", "text": "Fine thanks, and you?", "speaker": "speaker_2"},
        {"ts": "2026-09-17T19:00:00Z", "text": "The garden looked lovely this evening.", "speaker": "speaker_1"},
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    out = tmp_path / "days.json"
    assert main(["analyze", str(p), "--speaker", "speaker_1", "--out", str(out)]) == 0
    days = json.loads(out.read_text(encoding="utf-8"))
    assert [d["date"] for d in days] == ["2026-09-16", "2026-09-17"]
    assert days[0]["utterances"] == 1  # speaker_2 was filtered out


def test_cli_schema_prints_registry(capsys):
    assert main(["schema"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert {s["name"] for s in printed} == set(FEATURE_NAMES)


def test_cli_rejects_malformed_lines(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"ts": "2026-09-16T08:00:00Z"}\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["analyze", str(p)])
