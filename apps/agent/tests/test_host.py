"""The Check-in Host, without a speaker, a Bee or a network.

What is pinned: the host speaks exactly the lines the service returned,
in order, waits after each prompt and not elsewhere, writes every spoken
line to the host file the ingest reads, says so when a check-in already
happened today, and reads the coaching note back as text plus actions. The
waiting rule for the Bee is pinned too: a session counts as written down
only when its utterance count has stopped growing.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / "check_in_host.py"
spec = importlib.util.spec_from_file_location("check_in_host", HOST)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)

SCRIPT = {
    "date": "2026-10-19",
    "opener": "Bellwether check-in, October nineteenth.",
    "prompts": [{"kind": "narrative", "text": "Tell me about your day."},
                {"kind": "description", "text": "Describe the room."},
                {"kind": "procedure", "text": "Explain your morning drink."}],
    "closing": "Thank you. That is today's check-in.",
    "answer_seconds": 30,
    "eligible_days": 2,
    "warmup_days": 7,
    "already_started_today": None,
}


class FakeMcp:
    def __init__(self, start=SCRIPT, note=None):
        self.start, self.note, self.calls = start, note or {"text": "Day two of seven counted.", "actions": ["Check in tomorrow."]}, []

    def call(self, name, args=None):
        self.calls.append((name, args or {}))
        return dict(self.start) if name == "start_check_in" else dict(self.note)


class FakeSpeaker:
    def __init__(self):
        self.said = []

    def say(self, text):
        self.said.append(text)


def test_the_host_speaks_the_script_verbatim_and_waits_after_each_prompt(tmp_path):
    mcp, sp, waits = FakeMcp(), FakeSpeaker(), []
    hf = tmp_path / "host.json"
    out = host.run_check_in(mcp, sp, "me-voice", "2026-10-19", waits.append, host_file=str(hf), log=lambda *_: None)
    assert sp.said == [
        SCRIPT["opener"], "Question one.", "Tell me about your day.", "Question two.", "Describe the room.",
        "Question three.", "Explain your morning drink.", SCRIPT["closing"],
    ]
    assert waits == [30, 30, 30]
    assert mcp.calls[0] == ("start_check_in", {"profile_id": "me-voice", "host": host.HOST_NAME, "date": "2026-10-19"})
    assert out["spoken"] == sp.said
    assert json.loads(hf.read_text(encoding="utf-8")) == {"2026-10-19": sp.said}


def test_a_second_check_in_the_same_day_is_announced_and_still_runs(tmp_path):
    start = {**SCRIPT, "already_started_today": {"at": "2026-10-19T20:01:00Z", "host": "check-in-host"}}
    sp = FakeSpeaker()
    host.run_check_in(FakeMcp(start), sp, "me-voice", "2026-10-19", lambda s: None, host_file=str(tmp_path / "h.json"), log=lambda *_: None)
    assert sp.said[0].startswith("You already checked in today")
    assert sp.said[1] == SCRIPT["opener"]


def test_the_answer_window_can_be_overridden(tmp_path):
    waits = []
    host.run_check_in(FakeMcp(), FakeSpeaker(), "me-voice", "2026-10-19", waits.append, answer_seconds=5,
                      host_file=str(tmp_path / "h.json"), log=lambda *_: None)
    assert waits == [5, 5, 5]


def test_the_host_file_accumulates_without_duplicates(tmp_path):
    hf = str(tmp_path / "h.json")
    host.record_spoken(hf, "2026-10-19", ["A.", "B."])
    host.record_spoken(hf, "2026-10-19", ["B.", "C."])
    host.record_spoken(hf, "2026-10-20", ["D."])
    assert json.loads(Path(hf).read_text(encoding="utf-8")) == {"2026-10-19": ["A.", "B.", "C."], "2026-10-20": ["D."]}


def test_coaching_is_read_back_as_text_then_actions():
    sp = FakeSpeaker()
    note = host.speak_coaching(FakeMcp(), sp, "me-voice", log=lambda *_: None)
    assert sp.said == ["Day two of seven counted. Check in tomorrow."]
    assert note["actions"] == ["Check in tomorrow."]


def test_waiting_for_the_bee_needs_the_count_to_stop_growing():
    started = 1_000_000.0
    polls = iter([
        [],
        [{"id": 7, "start_time": (started + 30) * 1000, "utterances_count": 3}],
        [{"id": 7, "start_time": (started + 30) * 1000, "utterances_count": 9}],
        [{"id": 7, "start_time": (started + 30) * 1000, "utterances_count": 9}],
    ])
    now = [started]

    def clock():
        return now[0]

    def sleep(s):
        now[0] += s

    conv = host.wait_for_the_bee(started, poll=lambda: next(polls), every=60, limit=600, clock=clock, sleep=sleep, log=lambda *_: None)
    assert conv["id"] == 7 and now[0] == started + 180


def test_waiting_ignores_sessions_from_another_time_and_gives_up():
    started = 1_000_000.0
    now = [started]
    polls = lambda: [{"id": 1, "start_time": (started - 3600) * 1000, "utterances_count": 50}]
    said = []
    conv = host.wait_for_the_bee(started, poll=polls, every=100, limit=300, clock=lambda: now[0],
                                 sleep=lambda s: now.__setitem__(0, now[0] + s), log=said.append)
    assert conv is None
    assert "No session began on the Bee" in said[-1]


def test_the_host_never_reads_a_transcript():
    """The host's own source does not fetch utterances or print text from
    the Bee: it polls the conversation list for counts and runs `mine`."""
    src = HOST.read_text(encoding="utf-8")
    assert "conversations get" not in src
    assert "utterances\"]" not in src and "['utterances']" not in src
    assert "bee conversations list" in src and "utterances_count" in src


def test_the_count_uses_the_projects_own_ingest_when_installed():
    cmd = host._ingest_command()
    assert cmd and ("bellwether-ingest" in cmd[0] or cmd[-1] == "bellwether_ingest.cli")
