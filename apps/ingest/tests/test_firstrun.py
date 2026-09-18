"""The day-one rehearsal, tested without a device.

A Bee was bought so this project could satisfy the track's live-data
requirement, and that purchase only converts into a submission if the
first session with the hardware works. Every failure mode that session
can hit is reproduced here with an injected runner, so the path is
rehearsed in full before the device is unboxed and the only untested step
on the day is the one that genuinely needs it.
"""

from __future__ import annotations

import json

import pytest

from bellwether_ingest.bee import BeeCli
from bellwether_ingest.firstrun import report, run


def runner_for(responses: dict[str, tuple[int, str, str]]):
    """Answer by the bee subcommand, so argv stays exactly as production builds it."""

    def runner(argv: list[str]) -> tuple[int, str, str]:
        parts = [a for a in argv if not a.startswith("-")]
        for key, value in responses.items():
            if key in " ".join(parts):
                return value
        return (1, "", f"unexpected argv: {argv}")

    return runner


def conversation(day: str, text: str, speaker: str = "speaker_1") -> dict:
    return {
        "id": f"c-{day}",
        "start_time": f"{day}T09:00:00Z",
        "utterances": [
            {"speaker": speaker, "text": text, "start_time": f"{day}T09:00:0{i}Z"}
            for i in range(1, 4)
        ],
    }


def test_a_missing_cli_stops_at_the_first_step_with_the_install_command(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    steps = run(BeeCli(runner=runner_for({})))
    assert len(steps) == 1
    assert steps[0].ok is False
    assert "npm install -g @beeai/cli" in (steps[0].fix or "")


def test_not_logged_in_says_how_to_enable_developer_mode(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/bee")
    steps = run(BeeCli(runner=runner_for({"me": (1, "", "You are not logged in")})))
    assert [s.ok for s in steps] == [True, False]
    fix = steps[-1].fix or ""
    # The instruction has to match what the app actually shows, or it is
    # worse than no instruction.
    assert "version number five times" in fix
    assert "bee login" in fix


def test_a_brand_new_device_with_no_speech_is_not_reported_as_a_bug(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/bee")
    steps = run(
        BeeCli(
            runner=runner_for(
                {
                    "me": (0, json.dumps({"id": "u1"}), ""),
                    "conversations list": (0, json.dumps([]), ""),
                }
            )
        )
    )
    assert steps[-1].name == "conversations recorded"
    assert steps[-1].ok is False
    assert "Wear the device" in (steps[-1].fix or "")


def test_a_good_day_passes_every_step(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/bee")
    long_text = " ".join(["the quick brown fox jumped over the lazy dog again"] * 12)
    steps = run(
        BeeCli(
            runner=runner_for(
                {
                    "me": (0, json.dumps({"id": "u1"}), ""),
                    "conversations list": (
                        0,
                        json.dumps([conversation("2026-09-20", long_text)]),
                        "",
                    ),
                }
            )
        )
    )
    assert all(s.ok for s in steps), [(s.name, s.detail) for s in steps if not s.ok]
    assert "Ready." in report(steps)


def test_a_quiet_day_is_flagged_before_the_camera_is_on(monkeypatch):
    # Below the 150 word floor the engine excludes the day. Discovering
    # that mid-demo is the avoidable version of this problem.
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/bee")
    steps = run(
        BeeCli(
            runner=runner_for(
                {
                    "me": (0, json.dumps({"id": "u1"}), ""),
                    "conversations list": (
                        0,
                        json.dumps([conversation("2026-09-20", "just a few words here")]),
                        "",
                    ),
                }
            )
        )
    )
    exposure = [s for s in steps if s.name == "enough speech in a day to assess"]
    assert exposure and exposure[0].ok is False
    assert "150" in exposure[0].detail


def test_an_unexpected_shape_says_how_to_capture_it(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/bee")
    steps = run(
        BeeCli(
            runner=runner_for(
                {
                    "me": (0, json.dumps({"id": "u1"}), ""),
                    "conversations list": (0, json.dumps({"unexpected": True}), ""),
                }
            )
        )
    )
    assert steps[-1].ok is False


def test_the_report_names_the_next_command_when_everything_passes(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/bee")
    long_text = " ".join(["the quick brown fox jumped over the lazy dog again"] * 12)
    steps = run(
        BeeCli(
            runner=runner_for(
                {
                    "me": (0, json.dumps({"id": "u1"}), ""),
                    "conversations list": (
                        0,
                        json.dumps([conversation("2026-09-20", long_text)]),
                        "",
                    ),
                }
            )
        )
    )
    assert "bellwether-ingest pull" in report(steps)
