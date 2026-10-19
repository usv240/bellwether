"""The second opinion's gate, without a model or a network."""

from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "second_opinion.py"
spec = importlib.util.spec_from_file_location("second_opinion", HERE)
so = importlib.util.module_from_spec(spec)
spec.loader.exec_module(so)

W = {
    "profile_id": "alex-drift", "simulated": True, "tier": "discuss", "since": "2026-09-03",
    "change": [{"id": "C1", "claim": "Flagged on 18 of 18 readable days since 2026-09-03."},
               {"id": "C3", "claim": "The change score peaked at 26.1, where 0 is this person's own baseline."}],
    "ordinary": [{"id": "O1", "claim": "The person's notes are not near the change: the closest is 2026-08-16, 18 days before it began."},
                 {"id": "O5", "claim": "No spoken check has been logged."}],
}

GOOD = ("The case for a real change is stronger, because it was flagged on 18 of 18 days [C1] and the only note is 18 days "
        "earlier [O1]. Some more weeks of days would settle it. This week, run the spoken check and bring the report to a "
        "clinician you trust.")


def test_a_note_inside_the_evidence_passes():
    assert so.gate(GOOD, W) == (True, "ok")


def test_a_note_that_names_a_condition_is_refused():
    ok, why = so.gate(GOOD + " This looks like early dementia.", W)
    assert not ok and "condition" in why


def test_a_note_with_an_invented_number_is_refused():
    ok, why = so.gate(GOOD.replace("18 of 18", "17 of 18"), W)
    assert not ok and "17" in why


def test_a_note_that_cites_only_one_side_is_refused():
    ok, why = so.gate("It was flagged on 18 of 18 days [C1]. Run the spoken check.", W)
    assert not ok and "both sides" in why


def test_a_note_citing_an_item_that_does_not_exist_is_refused():
    ok, why = so.gate(GOOD + " See also [C9].", W)
    assert not ok and "C9" in why


def test_the_fallback_always_passes_its_own_gate():
    assert so.gate(so.fallback(W), W)[0]


def test_the_debate_runs_three_turns_and_the_referee_sees_both_arguments():
    seen = []

    def ask(system, prompt):
        seen.append((system, prompt))
        return {0: "It is real [C1].", 1: "It is an ordinary week [O1].", 2: GOOD}[len(seen) - 1]

    out = so.debate(W, ask)
    assert len(seen) == 3
    assert "It is real [C1]." in seen[2][1] and "It is an ordinary week [O1]." in seen[2][1]
    assert out["note"] == GOOD and out["note_source"] == "referee"


def test_a_referee_that_fails_the_gate_is_replaced_by_the_evidence_note():
    out = so.debate(W, lambda s, p: "This is Alzheimer's [C1] [O1].")
    assert out["note_source"].startswith("evidence")
    assert out["note"] == so.fallback(W)


def test_a_number_written_as_a_word_is_held_to_the_evidence_too():
    ok, why = so.gate(GOOD + " Record for five minutes.", W)
    assert not ok and "5" in why


def test_markdown_and_dashes_are_cleaned_before_anyone_sees_them():
    raw = "# Heading\n**Bold** point — and more\n- a list item"
    assert so.clean(raw) == "Heading Bold point, and more a list item"


def test_an_argument_that_names_a_condition_is_withheld():
    replies = {so.ADVOCATE: "This is early dementia [C1].", so.SCEPTIC: "An ordinary week [O1].", so.REFEREE: GOOD}
    out = so.debate(W, lambda s, p: replies[s])
    assert out["advocate"].startswith("(withheld") and out["note"] == GOOD


def test_a_refused_note_gets_one_retry_with_the_reason_and_is_recorded():
    prompts = []
    replies = iter(["It is real [C1].", "An ordinary week [O1].", "Too sure, no ordinary side [C1].", GOOD])

    def ask(system, prompt):
        prompts.append(prompt)
        return next(replies)

    out = so.debate(W, ask)
    assert out["note"] == GOOD and out["note_source"] == "referee"
    assert out["rejected"][0]["why"] == "does not cite both sides"
    assert "Your note was rejected: does not cite both sides" in prompts[3]


def test_a_date_written_without_its_leading_zero_is_the_same_number():
    assert so.gate(GOOD.replace("is stronger", "is stronger since September 3rd"), W)[0]


def test_a_rounded_number_is_still_refused():
    ok, why = so.gate(GOOD + " It has held for nearly twenty days.", W)
    assert not ok and "20" in why
