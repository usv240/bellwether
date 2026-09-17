"""The two detectors a reasonable engineer would build instead, measured.

Bellwether's engine accumulates. A one-sided CUSUM on a concern-signed
composite adds up small deviations and fires when they persist, rather than
when any single day looks bad. That is a design choice, and a design choice
is only worth anything if the obvious alternative was measured and lost.

The alternatives here are not strawmen. They are what most people build
first, and for good reason: they are simpler, they need no state beyond the
baseline, and they are trivially explainable.

    shewhart_composite   flag the day the composite exceeds a threshold
    shewhart_feature     flag the day any single feature's concern-signed
                         z-score exceeds a threshold

Both see exactly the same inputs as the CUSUM: the same nine features, the
same per-person EWMA baseline, the same concern signing, the same excluded
low-exposure days. Only the decision rule differs. That is what makes the
comparison mean something. If the alternatives were fed different features
the result would be a statement about feature engineering rather than about
the rule.

Two axes matter and they trade against each other, which is the whole point
of the exercise:

    false alarms   days a detector fires on someone whose speech has not
                   changed. Every one costs a family a frightened week.
    time to detect how many days into a real change it fires. Every day of
                   delay is a day of a signal nobody acted on.

A detector that wins one axis by giving up the other has not won anything.
The question is whether any setting of a simpler rule matches the CUSUM on
both at once, and the answer is written down in
``fixtures/detector-comparison.json`` alongside the sweep that produced it.

These functions are pure and take assessment dictionaries, so they can be
run against the committed persona output without re-running the engine.
"""

from __future__ import annotations

from datetime import date


def _parse(day: str) -> date:
    year, month, dom = (int(part) for part in day.split("-"))
    return date(year, month, dom)


def scored_days(assessments: list[dict]) -> list[dict]:
    """Days that produced a score at all.

    Warmup days and low-exposure exclusions carry no composite, and a
    detector cannot be credited or blamed for a day it never saw. Every
    rule here starts from the same filtered set.
    """
    return [day for day in assessments if day.get("composite") is not None]


def shewhart_composite(assessments: list[dict], threshold: float) -> list[str]:
    """Flag any day whose composite exceeds ``threshold``. No memory."""
    return [
        day["date"] for day in scored_days(assessments) if day["composite"] > threshold
    ]


def shewhart_feature(assessments: list[dict], z: float) -> list[str]:
    """Flag any day where a single feature's concern-signed z exceeds ``z``.

    Concern-signed means the sign already points the worrying way for that
    feature, so one threshold serves all nine regardless of whether higher
    or lower is the concerning direction.
    """
    flagged = []
    for day in scored_days(assessments):
        for feature in day["features"]:
            value = feature.get("concern_z")
            if value is not None and value > z:
                flagged.append(day["date"])
                break
    return flagged


def engine_flags(assessments: list[dict]) -> list[str]:
    """What Bellwether itself flagged: any day at watch or discuss."""
    return [
        day["date"]
        for day in assessments
        if day.get("tier") in ("watch", "discuss")
    ]


def days_into_ramp(flagged: list[str], ramp_start: str) -> int | None:
    """How many days into the injected change the first flag landed.

    Day one is the first day of the ramp itself, so a flag on the start
    date returns 1. Flags before the ramp are ignored here because they
    are false alarms rather than detections, and are counted as such
    against the stable persona.
    """
    after = sorted(day for day in flagged if day >= ramp_start)
    if not after:
        return None
    return (_parse(after[0]) - _parse(ramp_start)).days + 1


def evaluate(
    stable: list[dict],
    drift: list[dict],
    ramp_start: str,
    flag: object,
) -> dict:
    """Score one detector on both axes at once.

    ``flag`` is a callable taking an assessment list and returning flagged
    dates. Splitting the two personas is what keeps the axes honest: false
    alarms are only ever counted on the person who did not change, and
    detection is only ever counted on the person who did.
    """
    call = flag  # type: ignore[assignment]
    return {
        "falseAlarmsOnStable": len(call(stable)),  # type: ignore[operator]
        "daysIntoChangeBeforeFirstFlag": days_into_ramp(call(drift), ramp_start),  # type: ignore[operator]
    }


def dominates(a: dict, b: dict) -> bool:
    """True when ``a`` is at least as good as ``b`` on both axes and better on one.

    Used to answer the only question that matters here: is there any setting
    of a simpler rule that the CUSUM does not beat outright? A detector that
    never fires is given no credit, which is why a missing detection day is
    treated as worse than any real one.
    """
    big = 10**6
    a_days = a["daysIntoChangeBeforeFirstFlag"] or big
    b_days = b["daysIntoChangeBeforeFirstFlag"] or big
    no_worse = a["falseAlarmsOnStable"] <= b["falseAlarmsOnStable"] and a_days <= b_days
    better = a["falseAlarmsOnStable"] < b["falseAlarmsOnStable"] or a_days < b_days
    return no_worse and better
