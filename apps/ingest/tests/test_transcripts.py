"""Bellwether without a Bee: the transcript formats people already have.

Each format is pinned with a small real-shaped sample, and so is the one
thing the importer must never do: let anyone else's words into the
speaker's own day.
"""

from __future__ import annotations

import json

from bellwether_ingest.cli import main
from bellwether_ingest.transcripts import speakers, turns, utterances_from

ZOOM = """WEBVTT

1
00:00:01.000 --> 00:00:04.000
Priya Shah: Morning, everyone. Shall we start with the budget?

2
00:00:04.500 --> 00:00:09.000
Ujwal: Yes. I went through the numbers last night and the travel line is still too high.
"""

TEAMS = """WEBVTT

00:00:01.000 --> 00:00:04.000
<v Priya Shah>Morning, everyone.</v>

00:00:04.500 --> 00:00:09.000
<v Ujwal>I went through the numbers last night.</v>
"""

OTTER = """Priya Shah  0:01
Morning, everyone. Shall we start with the budget?

Ujwal  0:04
Yes. I went through the numbers last night
and the travel line is still too high.
"""

PLAIN = """Priya Shah: Morning, everyone.
Ujwal: Yes, the travel line is still too high.
"""


def test_each_format_attributes_every_turn():
    for sample in (ZOOM, TEAMS, OTTER, PLAIN):
        names = [s for s, _ in turns(sample)]
        assert names == ["Priya Shah", "Ujwal"], (sample[:20], names)


def test_otter_joins_a_turn_that_wraps_across_lines():
    said = dict(turns(OTTER))["Ujwal"]
    assert said.endswith("the travel line is still too high.")


def test_only_the_named_speaker_is_kept(tmp_path):
    f = tmp_path / "standup-2026-10-14.vtt"
    f.write_text(ZOOM, encoding="utf-8")
    utts = utterances_from(f, "ujwal")
    assert len(utts) == 1
    assert all("budget" not in u.text and "Morning" not in u.text for u in utts)
    assert utts[0].ts.startswith("2026-10-14")


def test_speakers_lists_names_and_word_counts_only():
    counts = speakers(ZOOM)
    assert counts["Ujwal"] > counts["Priya Shah"] > 0


def test_the_command_lists_names_without_a_word_of_speech(tmp_path, capsys):
    f = tmp_path / "standup-2026-10-14.vtt"
    f.write_text(ZOOM, encoding="utf-8")
    assert main(["file", str(f)]) == 0
    err = capsys.readouterr().err
    assert "Ujwal" in err and "Priya Shah" in err
    assert "budget" not in err and "travel" not in err


def test_the_command_writes_day_rows_and_no_text(tmp_path):
    long_turn = "Ujwal: " + "I went through the numbers last night and the travel line is still too high. " * 12
    f = tmp_path / "review-2026-10-15.txt"
    f.write_text("Priya Shah: Morning.\n" + long_turn + "\n", encoding="utf-8")
    out = tmp_path / "days.json"
    assert main(["file", str(f), "--speaker", "Ujwal", "--out", str(out)]) == 0
    rows = json.loads(out.read_text(encoding="utf-8"))
    assert [r["date"] for r in rows] == ["2026-10-15"]
    assert rows[0]["token_count_day"] >= 150
    assert "travel" not in out.read_text(encoding="utf-8")
