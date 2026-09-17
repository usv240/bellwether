"""Every number this project claims in public, checked against the fixtures
that produced it.

A figure in a README is a claim. A figure a test re-derives from committed
output is a fact, and it cannot silently drift: change the headline without
regenerating the personas, or regenerate them and get a different answer,
and this file fails.

Two assertions here are doing more than bookkeeping.

*The controlled comparison.* The two personas share a seed and differ only
in whether a gradual change is injected from day 35. If their feature
values were ever to diverge before that day, the drift persona would not be
evidence that the engine detects drift; it would be evidence that the
engine detects two different people.

*The freeze.* An adaptive baseline that keeps updating while it is
signalling will absorb the very change it is meant to report, and quietly
return to "stable" without anything having improved. The freeze is the
safety property that prevents it, and because it is invisible in ordinary
operation it is exactly the kind of thing that rots. It is asserted here
against real fixture output rather than only in a unit test.

Regenerate the fixtures: python fixtures/personas/generate.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PERSONAS = REPO / "fixtures" / "personas"

# Files where a public claim could be made, so drift is caught wherever it lands.
PUBLIC_FILES = [
    "README.md",
    "docs/SUBMISSION.md",
    "docs/EVIDENCE.md",
    "docs/DESIGN.md",
    "skills/bellwether/SKILL.md",
]


def load(persona: str, name: str):
    return json.loads((PERSONAS / persona / f"{name}.json").read_text(encoding="utf8"))


def feature(day: dict, name: str):
    """Excluded days carry no features, so callers must handle None."""
    found = [f for f in day["features"] if f["name"] == name]
    return found[0] if found else None


@pytest.fixture(scope="module")
def public_text():
    out = []
    for rel in PUBLIC_FILES:
        p = REPO / rel
        if p.exists():
            out.append((rel, p.read_text(encoding="utf8")))
    return out


def stated_in(public_text, needle: str):
    return [name for name, text in public_text if needle in text]


# --------------------------------------------------------------------------
# The comparison is controlled
# --------------------------------------------------------------------------


def test_personas_are_identical_until_the_injected_change():
    """Same seed, same speech, right up to the day the change begins.

    This is what makes the drift persona evidence about the engine rather
    than evidence about two unrelated speakers.
    """
    stable = load("alex-stable", "assessments")
    drift = load("alex-drift", "assessments")
    assert len(stable) == len(drift) == 56

    drift_start = load("alex-drift", "meta")["drift_start_date"]
    assert drift_start == "2026-08-31"

    for a, b in zip(stable, drift):
        assert a["date"] == b["date"]
        if a["date"] >= drift_start:
            break
        a_values = [(f["name"], f["value"]) for f in a["features"]]
        b_values = [(f["name"], f["value"]) for f in b["features"]]
        assert a_values == b_values, (
            f"personas diverge on {a['date']}, before the injected change"
        )


def test_the_stable_persona_has_no_injected_change_at_all():
    meta = load("alex-stable", "meta")
    assert meta["drift_start_day"] is None
    assert set(meta["drift_level_by_date"].values()) == {0.0}


def test_both_personas_are_labelled_simulated():
    # Nothing in this project may present synthetic speech as a real person.
    for persona in ("alex-stable", "alex-drift"):
        assert load(persona, "meta")["label"] == "SIMULATED"


# --------------------------------------------------------------------------
# The stable persona: quiet, and quiet for the number of days we claim
# --------------------------------------------------------------------------


def test_stable_persona_is_quiet_for_47_consecutive_assessed_days(public_text):
    days = load("alex-stable", "assessments")
    assessed = [d for d in days if d["tier"] not in ("learning", "excluded")]
    assert len(assessed) == 47
    assert {d["tier"] for d in assessed} == {"stable"}

    summary = load("alex-stable", "summary")
    assert summary["stable_streak_days"] == 47
    assert summary["tier"] == "stable"
    assert stated_in(public_text, "47 consecutive assessed days")


def test_stable_persona_raises_zero_false_alarms(public_text):
    """The false-positive count, stated as an exact zero.

    A drift detector that fires on an unchanging person is worse than no
    detector, because every alarm it raises costs a family a frightened
    week. If this stops being zero the product claim has changed and a
    human has to decide what to say instead.
    """
    days = load("alex-stable", "assessments")
    alarms = [d["date"] for d in days if d["tier"] in ("watch", "discuss")]
    assert alarms == []
    assert stated_in(public_text, "zero false alarms")


def test_stable_persona_never_freezes_its_baseline():
    """The counterpart to the freeze: a quiet person's baseline keeps learning."""
    days = [d for d in load("alex-stable", "assessments") if d["tier"] == "stable"]
    means = [feature(d, "mattr")["baseline_mean"] for d in days]
    assert len(set(means)) > 1, "a stable baseline that never moves is not adapting"


# --------------------------------------------------------------------------
# The drift persona: detected, and detected when we say it is
# --------------------------------------------------------------------------


def test_drift_reaches_watch_two_days_into_the_change(public_text):
    days = load("alex-drift", "assessments")
    meta = load("alex-drift", "meta")
    ramp = sorted(d for d, lvl in meta["drift_level_by_date"].items() if lvl > 0)
    assert ramp[0] == meta["drift_start_date"]

    first_watch = next(d["date"] for d in days if d["tier"] == "watch")
    assert first_watch == "2026-09-01"
    # Day one of the ramp is the start date itself, so the second day is index 1.
    assert ramp.index(first_watch) == 1
    assert stated_in(public_text, "two days into")


def test_drift_escalates_to_discuss_and_stays_there():
    days = load("alex-drift", "assessments")
    first_discuss = next(d["date"] for d in days if d["tier"] == "discuss")
    assert first_discuss == "2026-09-03"
    after = [d["tier"] for d in days if d["date"] >= first_discuss]
    assert set(after) == {"discuss"}, "a real signal should not flicker back"

    summary = load("alex-drift", "summary")
    assert summary["tier"] == "discuss"
    assert summary["since"] == first_discuss
    assert summary["stable_streak_days"] == 0


def test_the_worked_example_in_the_skill_matches_the_fixture(public_text):
    """SKILL.md quotes a tier and a date. Prose figures rot quietly."""
    summary = load("alex-drift", "summary")
    skill = dict(public_text).get("skills/bellwether/SKILL.md")
    assert skill is not None
    assert '"' + summary["since"] + '"' in skill
    assert '"' + summary["tier"] + '"' in skill


def test_drift_names_every_contributing_feature_with_a_direction():
    summary = load("alex-drift", "summary")
    last = load("alex-drift", "assessments")[-1]
    names = {f["name"] for f in last["features"]}

    assert set(summary["contributors"]) <= names
    assert len(summary["contributors"]) == 9, "all nine measures moved by the end"
    for f in last["features"]:
        assert f["direction"] in ("lower_is_concerning", "higher_is_concerning")

    # Every contributor is explained in words, with the date it started.
    for name in summary["contributors"]:
        assert any(name in line for line in summary["explanation"]), name


def test_a_stable_persona_names_no_contributors():
    """The other half of attribution: silence when there is nothing to attribute."""
    assert load("alex-stable", "summary")["contributors"] == []


# --------------------------------------------------------------------------
# The safety property
# --------------------------------------------------------------------------


def test_the_baseline_freezes_once_the_engine_is_signalling():
    """It cannot learn its way out of a signal.

    From the first non-stable day onward, every feature's baseline must be
    the value it held before that day and must not move again. Without
    this, twenty days of altered speech would gradually become the new
    normal and the tier would fall back to stable with nothing resolved.
    """
    days = [d for d in load("alex-drift", "assessments") if d["features"]]
    signalling = [d for d in days if d["tier"] in ("watch", "discuss")]
    assert len(signalling) >= 14, "need a long enough signal for the freeze to matter"

    names = [f["name"] for f in signalling[0]["features"]]
    for name in names:
        means = {feature(d, name)["baseline_mean"] for d in signalling}
        assert len(means) == 1, f"{name} baseline moved while the engine was signalling"


def test_the_composite_keeps_rising_while_frozen():
    """The freeze holds the baseline still; it does not mute the signal."""
    days = [d for d in load("alex-drift", "assessments") if d["composite"] is not None]
    signalling = [d for d in days if d["tier"] in ("watch", "discuss")]
    assert signalling[-1]["composite"] > signalling[0]["composite"]
    assert signalling[-1]["composite_cusum"] > signalling[0]["composite_cusum"]


# --------------------------------------------------------------------------
# Exposure honesty
# --------------------------------------------------------------------------


@pytest.mark.parametrize("persona", ["alex-stable", "alex-drift"])
def test_low_exposure_days_are_excluded_and_say_why(persona):
    """A day with too little speech is not a day with normal speech.

    Scoring a 38-word day against a baseline built from full days would
    manufacture a deviation out of a quiet afternoon.
    """
    days = load(persona, "assessments")
    excluded = [d for d in days if not d["eligible"]]
    assert [d["date"] for d in excluded] == load(persona, "meta")["low_exposure_days"]
    for d in excluded:
        assert d["tier"] == "excluded"
        assert d["reason"] and "below 150" in d["reason"]
        assert d["composite"] is None, "an excluded day must not produce a score"

    summary = load(persona, "summary")
    assert summary["excluded_days"] == len(excluded)
    assert summary["eligible_days"] + summary["excluded_days"] == len(days)


@pytest.mark.parametrize("persona", ["alex-stable", "alex-drift"])
def test_warmup_produces_no_tier_at_all(persona):
    """Seven days of learning, during which the product says nothing."""
    days = load(persona, "assessments")
    learning = [d for d in days if d["tier"] == "learning"]
    assert len(learning) == 7
    assert all(d["composite"] is None for d in learning)
    assert [d["date"] for d in learning] == [d["date"] for d in days[:7]]
    assert load(persona, "summary")["in_warmup"] is False
