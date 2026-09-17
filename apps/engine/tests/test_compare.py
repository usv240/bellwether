"""The baseline comparison, as unit tests and as pinned claims.

Two jobs in one file. The first half tests the detector rules on tiny
hand-built inputs, because a comparison is only evidence if the thing it
compares against is implemented correctly: a baseline accidentally
crippled is worse than no baseline, and it is the easiest mistake to make
without noticing.

The second half pins what the committed comparison actually found, so the
claim in the README cannot drift from the file that produced it.

Regenerate: python fixtures/compare_detectors.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bellwether_engine.compare import (
    days_into_ramp,
    dominates,
    engine_flags,
    scored_days,
    shewhart_composite,
    shewhart_feature,
)

REPO = Path(__file__).resolve().parents[3]


def day(date: str, composite=None, tier="stable", **features):
    return {
        "date": date,
        "composite": composite,
        "tier": tier,
        "features": [
            {"name": name, "concern_z": z} for name, z in features.items()
        ],
    }


# --------------------------------------------------------------------------
# The rules themselves
# --------------------------------------------------------------------------


def test_a_day_with_no_score_is_invisible_to_every_detector():
    """Warmup and low-exposure days carry no composite.

    No detector may be credited or blamed for a day it never saw, so all
    of them start from the same filtered set.
    """
    days = [day("2026-01-01"), day("2026-01-02", composite=9.0, mattr=9.0)]
    assert [d["date"] for d in scored_days(days)] == ["2026-01-02"]
    assert shewhart_composite(days, 1.0) == ["2026-01-02"]
    assert shewhart_feature(days, 1.0) == ["2026-01-02"]


def test_the_composite_rule_has_no_memory():
    """The point of the comparison: it fires on the day, not on the trend."""
    days = [
        day("2026-01-01", composite=4.9),
        day("2026-01-02", composite=4.9),
        day("2026-01-03", composite=5.1),
    ]
    assert shewhart_composite(days, 5.0) == ["2026-01-03"]


def test_the_feature_rule_fires_on_any_single_feature():
    days = [day("2026-01-01", composite=0.0, mattr=1.0, filler_rate=3.0)]
    assert shewhart_feature(days, 2.0) == ["2026-01-01"]
    assert shewhart_feature(days, 4.0) == []


def test_the_feature_rule_reports_each_day_once():
    """Nine features over threshold is one flagged day, not nine."""
    days = [day("2026-01-01", composite=0.0, a=5.0, b=5.0, c=5.0)]
    assert shewhart_feature(days, 2.0) == ["2026-01-01"]


def test_the_feature_rule_only_looks_at_the_concerning_direction():
    # concern_z is already signed so that positive means worrying. A day
    # that moved sharply the reassuring way must not flag.
    days = [day("2026-01-01", composite=0.0, mattr=-6.0)]
    assert shewhart_feature(days, 2.0) == []


def test_engine_flags_counts_watch_as_well_as_discuss():
    days = [
        day("2026-01-01", composite=1.0, tier="stable"),
        day("2026-01-02", composite=1.0, tier="watch"),
        day("2026-01-03", composite=1.0, tier="discuss"),
        day("2026-01-04", composite=None, tier="excluded"),
    ]
    assert engine_flags(days) == ["2026-01-02", "2026-01-03"]


def test_day_one_of_the_ramp_is_the_start_date_itself():
    assert days_into_ramp(["2026-08-31"], "2026-08-31") == 1
    assert days_into_ramp(["2026-09-01"], "2026-08-31") == 2


def test_flags_before_the_change_are_not_detections():
    """They are false alarms, and are counted as such on the other persona."""
    assert days_into_ramp(["2026-08-01"], "2026-08-31") is None
    assert days_into_ramp(["2026-08-01", "2026-09-02"], "2026-08-31") == 3


def test_never_detecting_is_worse_than_detecting_late():
    late = {"falseAlarmsOnStable": 0, "daysIntoChangeBeforeFirstFlag": 14}
    never = {"falseAlarmsOnStable": 0, "daysIntoChangeBeforeFirstFlag": None}
    assert dominates(late, never)
    assert not dominates(never, late)


def test_dominance_needs_both_axes():
    ours = {"falseAlarmsOnStable": 0, "daysIntoChangeBeforeFirstFlag": 2}
    faster_but_noisy = {"falseAlarmsOnStable": 3, "daysIntoChangeBeforeFirstFlag": 1}
    quieter_but_slower = {"falseAlarmsOnStable": 0, "daysIntoChangeBeforeFirstFlag": 5}
    assert not dominates(faster_but_noisy, ours)
    assert not dominates(quieter_but_slower, ours)
    assert dominates(ours, quieter_but_slower)


# --------------------------------------------------------------------------
# What the committed comparison found
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def comparison():
    path = REPO / "fixtures" / "detector-comparison.json"
    assert path.exists(), "run python fixtures/compare_detectors.py"
    return json.loads(path.read_text(encoding="utf8"))


def test_bellwether_is_quiet_and_early(comparison):
    ours = comparison["bellwether"]
    assert ours["falseAlarmsOnStable"] == 0
    assert ours["daysIntoChangeBeforeFirstFlag"] == 2


def test_no_simpler_setting_beats_it_on_both_axes(comparison):
    """The claim, stated as the thing that would falsify it.

    Eighteen settings of two simpler rules were swept. If any one of them
    were at least as quiet and at least as early, the accumulating rule
    would not be worth its complexity and the README would have to say so.
    """
    assert comparison["result"]["settingsBeatingBellwetherOnBothAxes"] == 0


def test_the_quiet_alternative_is_two_days_later(comparison):
    best = comparison["result"]["bestAlternativeWithZeroFalseAlarms"]
    assert best["falseAlarmsOnStable"] == 0
    assert best["daysIntoChangeBeforeFirstFlag"] == 4
    assert best["threshold"] == 4


def test_matching_our_speed_costs_a_false_alarm(comparison):
    fast = comparison["result"]["cheapestAlternativeMatchingOurDetectionSpeed"]
    assert fast["daysIntoChangeBeforeFirstFlag"] <= 2
    assert fast["falseAlarmsOnStable"] >= 1


def test_the_sweep_is_wide_enough_to_be_a_real_search(comparison):
    # A comparison against one arbitrary threshold proves nothing. The
    # sweep has to cover settings that are obviously too twitchy and
    # obviously too sluggish, so the reader can see the whole tradeoff.
    composite = comparison["alternatives"]["shewhartComposite"]["sweep"]
    feature = comparison["alternatives"]["shewhartFeature"]["sweep"]
    assert len(composite) + len(feature) == 18
    assert max(r["falseAlarmsOnStable"] for r in composite + feature) >= 8
    assert any(r["daysIntoChangeBeforeFirstFlag"] is None or r["daysIntoChangeBeforeFirstFlag"] >= 14
               for r in composite + feature)


def test_every_detector_saw_the_same_inputs(comparison):
    # Stated in the file, because a comparison where the baseline got worse
    # features is a statement about feature engineering, not about the rule.
    assert "Only the decision rule differs." in comparison["method"]


def test_the_limit_of_synthetic_data_is_stated(comparison):
    assert "synthetic" in comparison["limit"]
    assert "not evidence that the detector works on a real person" in comparison["limit"]


def test_the_result_is_stated_in_the_readme(comparison):
    readme = (REPO / "README.md").read_text(encoding="utf8")
    assert "detector-comparison.json" in readme or "no false alarms" in readme
