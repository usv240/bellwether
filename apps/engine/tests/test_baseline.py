"""Baseline engine tests.

Synthetic personas with known ground truth. The engine is judged on the
properties a family would need to trust it: it says nothing until it has
learned, it stays quiet on a stable person, it notices a real drift within
days and escalates honestly, it names the features behind a change, it
ignores days with too little speech, it does not learn its way out of a
signal, and it gives the same answer every time.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from bellwether_engine import DEFAULT_CONFIG, assess, summarize
from speech_vitals import FEATURE_NAMES

# Typical values for an adult's everyday speech under this feature set.
# (mean, sd). Chosen to be plausible, not fitted to anyone.
PROFILE = {
    "mattr": (0.72, 0.02),
    "mean_utt_len": (9.0, 0.8),
    "dep_depth_mean": (3.2, 0.25),
    "pronoun_noun_ratio": (0.35, 0.03),
    "filler_rate": (2.0, 0.4),
    "disfluency_rate": (1.0, 0.3),
    "low_freq_word_rate": (6.0, 0.8),
    "idea_density": (4.5, 0.3),
    "vocab_size_day": (320.0, 25.0),
}
EXPOSURE = (1800.0, 200.0)

# Features that move, and which way, in the drift persona. Directions match
# the literature: diversity, length, rare words and idea density fall;
# pronoun reliance rises.
DRIFT = {
    "mattr": -1,
    "mean_utt_len": -1,
    "pronoun_noun_ratio": +1,
    "idea_density": -1,
    "low_freq_word_rate": -1,
}

START = date(2026, 1, 1)


def day_str(i: int) -> str:
    return (START + timedelta(days=i)).isoformat()


def make_days(n: int, seed: int, drift_from: int | None = None, drift_sd: float = 2.0, low_days=()):
    rng = np.random.RandomState(seed)
    out = []
    for i in range(n):
        row = {"date": day_str(i), "utterances": 40}
        for name in FEATURE_NAMES:
            mean, sd = PROFILE[name]
            value = rng.normal(mean, sd)
            if drift_from is not None and i >= drift_from and name in DRIFT:
                value += DRIFT[name] * drift_sd * sd
            row[name] = float(value)
        tokens = rng.normal(*EXPOSURE)
        row["token_count_day"] = 50 if i in low_days else int(max(tokens, 400))
        out.append(row)
    return out


# ---- warmup ----------------------------------------------------------------


def test_first_warmup_days_are_learning_and_then_stop():
    days = make_days(12, seed=1)
    a = assess(days)
    tiers = [x.tier for x in a]
    assert tiers[: DEFAULT_CONFIG.warmup_days] == ["learning"] * DEFAULT_CONFIG.warmup_days
    assert tiers[DEFAULT_CONFIG.warmup_days] != "learning"
    assert "more day(s)" in a[0].explanation[0]
    assert "Baseline learned" in a[DEFAULT_CONFIG.warmup_days - 1].explanation[0]


# ---- stable person ---------------------------------------------------------


def test_a_stable_person_stays_stable():
    days = make_days(60, seed=11)
    a = assess(days)
    post = [x for x in a if x.tier not in ("learning", "excluded")]
    assert len(post) == 60 - DEFAULT_CONFIG.warmup_days
    assert all(x.tier == "stable" for x in post), [x.tier for x in post]
    assert all(x.contributors == () for x in post)
    assert summarize(a).tier == "stable"
    assert summarize(a).stable_streak_days == len(post)


# ---- drift -----------------------------------------------------------------


def test_a_real_drift_is_noticed_within_days_and_escalates_honestly():
    drift_from = 40
    days = make_days(70, seed=3, drift_from=drift_from, drift_sd=2.0)
    a = assess(days)
    tiers = {x.date: x.tier for x in a}

    # Quiet before the drift.
    before = [tiers[day_str(i)] for i in range(DEFAULT_CONFIG.warmup_days, drift_from)]
    assert all(t == "stable" for t in before), before

    # Watch within the first few days of drift.
    first_watch = next(i for i in range(drift_from, 70) if tiers[day_str(i)] in ("watch", "discuss"))
    assert first_watch - drift_from <= 4, first_watch - drift_from

    # Discuss once the signal has persisted, and not before it has.
    first_discuss = next(i for i in range(drift_from, 70) if tiers[day_str(i)] == "discuss")
    assert first_discuss - first_watch >= DEFAULT_CONFIG.discuss_consecutive - 1
    assert first_discuss - drift_from <= 12

    # It stays escalated while the drift persists.
    assert all(tiers[day_str(i)] == "discuss" for i in range(first_discuss, 70))


def test_the_change_is_attributed_to_the_features_that_moved():
    days = make_days(70, seed=3, drift_from=40, drift_sd=2.0)
    a = assess(days)
    late = a[-1]
    for name in ("mattr", "pronoun_noun_ratio"):
        assert name in late.contributors, late.contributors
    text = " ".join(late.explanation)
    assert "mattr has been lower than your baseline since" in text
    assert "pronoun_noun_ratio has been higher than your baseline since" in text
    # Features that did not move are not blamed.
    assert "filler_rate" not in late.contributors


def test_the_baseline_does_not_learn_its_way_out_of_a_signal():
    """The freeze: while signalling, the baseline stops updating. Without it
    a slow real drift would be absorbed into 'normal' and vanish."""
    days = make_days(70, seed=3, drift_from=40, drift_sd=2.0)
    a = assess(days)
    late = a[-1]
    mattr = next(f for f in late.features if f.name == "mattr")
    pre_drift_mean = PROFILE["mattr"][0]
    drifted_mean = pre_drift_mean - 2.0 * PROFILE["mattr"][1]
    # Closer to the pre-drift baseline than to the drifted level.
    assert abs(mattr.baseline_mean - pre_drift_mean) < abs(mattr.baseline_mean - drifted_mean)


def test_a_single_sharp_day_is_discuss_immediately():
    days = make_days(30, seed=5)
    # One day where every feature moves four standard deviations the wrong way.
    for name in FEATURE_NAMES:
        mean, sd = PROFILE[name]
        sign = -1 if name not in ("pronoun_noun_ratio", "filler_rate", "disfluency_rate") else +1
        days[20][name] = mean + sign * 4.0 * sd
    a = assess(days)
    assert a[20].tier == "discuss"
    assert "differs sharply" in a[20].explanation[0]
    # The day after is not automatically discuss: acute is one day's verdict.
    assert a[21].tier in ("stable", "watch")


# ---- exposure --------------------------------------------------------------


def test_low_exposure_days_are_excluded_and_do_not_count():
    days = make_days(20, seed=2, low_days=(3, 10))
    a = assess(days)
    assert a[3].tier == "excluded" and not a[3].eligible
    assert "low exposure" in a[3].reason
    assert "Not enough speech" in a[3].explanation[0]
    # Warmup counts eligible days only, so it ends one day later than index 7.
    learning = [x.date for x in a if x.tier == "learning"]
    assert len(learning) == DEFAULT_CONFIG.warmup_days
    assert day_str(3) not in learning
    s = summarize(a)
    assert s.excluded_days == 2
    assert s.eligible_days == 18


# ---- annotations -----------------------------------------------------------


def test_annotations_are_carried_into_the_explanation():
    days = make_days(15, seed=4)
    a = assess(days, annotations={day_str(10): "travel, slept badly"})
    assert a[10].annotation == "travel, slept badly"
    assert any("You noted: travel" in line for line in a[10].explanation)


# ---- determinism and summary ----------------------------------------------


def test_assess_is_deterministic():
    days = make_days(50, seed=9, drift_from=30)
    assert assess(days) == assess(days)


def test_summary_reports_since_and_contributors():
    days = make_days(70, seed=3, drift_from=40, drift_sd=2.0)
    s = summarize(assess(days))
    assert s.tier == "discuss"
    assert s.since is not None and s.since >= day_str(40)
    assert len(s.contributors) >= 2
    assert s.in_warmup is False
    assert s.latest_date == day_str(69)


def test_summary_on_nothing():
    s = summarize(assess([]))
    assert s.tier == "learning"
    assert s.eligible_days == 0


def test_weights_and_config_are_honest_defaults():
    # Equal weights, stated rather than tuned.
    assert set(DEFAULT_CONFIG.weights) == set(FEATURE_NAMES)
    assert len(set(DEFAULT_CONFIG.weights.values())) == 1
    assert DEFAULT_CONFIG.warmup_days == 7


# ---- found by the persona fixture ------------------------------------------


def test_a_feature_that_was_exactly_zero_in_warmup_does_not_alarm_on_its_first_nonzero_day():
    """The stable persona never said "um" for its first week, so its filler
    variance was zero, a relative floor on a zero mean was no floor at all,
    and the first "um" became an infinite z-score and an acute alarm. A real
    person who happened not to say "um" for seven days would have tripped
    the same thing. Absolute floors state a belief: nobody's day-to-day
    variability is ever smaller than this."""
    days = make_days(30, seed=8)
    for d in days:
        d["filler_rate"] = 0.0
        d["disfluency_rate"] = 0.0
    days[12]["filler_rate"] = 1.2      # a couple of ums: an ordinary day
    days[12]["disfluency_rate"] = 0.6  # one restart
    a = assess(days)
    assert a[12].tier == "stable", a[12].explanation
    filler = next(x for x in a[12].features if x.name == "filler_rate")
    assert filler.baseline_sd >= DEFAULT_CONFIG.sd_floor_abs["filler_rate"]
    assert abs(filler.z) < 5
