"""The hosted check-in script, and the one rule that keeps the host's words
out of the wearer's numbers."""

from __future__ import annotations

from datetime import date, timedelta

from speech_vitals.elicitation import (
    CLOSING,
    KINDS,
    PROMPT_BANK,
    host_lines_for,
    is_host_line,
    opener_for,
    prompts_for,
    strip_host,
)


def test_three_prompts_one_of_each_kind_every_day():
    for n in range(60):
        d = date(2026, 10, 1) + timedelta(days=n)
        ps = prompts_for(d)
        assert [p["kind"] for p in ps] == list(KINDS)
        assert len({p["text"] for p in ps}) == 3


def test_no_prompt_repeats_inside_four_days():
    for n in range(60):
        d = date(2026, 10, 1) + timedelta(days=n)
        window = [p["text"] for k in range(4) for p in prompts_for(d + timedelta(days=k))]
        assert len(window) == len(set(window)), d


def test_every_prompt_is_a_real_question_of_twelve_to_twenty_five_words():
    for kind, prompts in PROMPT_BANK.items():
        for p in prompts:
            n = len(p.split())
            assert 12 <= n <= 25, (kind, p, n)


def test_opener_declares_a_check_in_in_its_first_words():
    line = opener_for("2026-10-19")
    assert line == "Bellwether check-in, October nineteenth."
    assert "bellwether" in line.lower().split()[0]


def test_host_lines_are_opener_three_numbered_prompts_and_a_closing():
    lines = host_lines_for(date(2026, 10, 19))
    assert lines[0].startswith("Bellwether check-in")
    assert lines[1] == "Question one." and lines[3] == "Question two." and lines[5] == "Question three."
    assert lines[-1] == CLOSING
    assert len(lines) == 8


def test_host_words_are_recognised_as_the_bee_hears_them():
    lines = host_lines_for(date(2026, 10, 19))
    # Exact, hyphen lost, date as digits, line cut in two.
    assert is_host_line("Bellwether check in, October 19th.", lines)
    assert is_host_line("Question one", lines)
    # The day's description prompt, cut in two by the device.
    prompt = lines[4].split()
    first, second = " ".join(prompt[:6]), " ".join(prompt[6:])
    assert is_host_line(first, lines) and is_host_line(second, lines)
    assert is_host_line("Thank you that is today's check-in", lines)


def test_the_wearers_own_answer_is_never_taken_for_the_host():
    lines = host_lines_for(date(2026, 10, 19))
    answers = [
        "The room.",
        "I am in the room where I work, it has a desk and two windows.",
        "I woke up at seven and had tea before anything else.",
        "Someone on the phone? No, I was alone all morning.",
        "I make coffee first, then I open the laptop.",
    ]
    assert strip_host(answers, lines) == answers


def test_strip_host_keeps_only_the_wearer():
    lines = host_lines_for(date(2026, 10, 19))
    session = [lines[0], lines[1], lines[2], "I woke up late and walked to the station.", lines[3], lines[4],
               "There is a lamp, a desk, and a window on the left.", lines[-1]]
    kept = strip_host(session, lines)
    assert kept == ["I woke up late and walked to the station.", "There is a lamp, a desk, and a window on the left."]
