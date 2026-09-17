"""Measure Bellwether's decision rule against the ones it replaced.

    python fixtures/compare_detectors.py

Writes fixtures/detector-comparison.json: the full threshold sweep for two
simpler detectors, Bellwether's own result, and whether any setting of a
simpler rule beats it on both axes at once.

Reads the committed persona assessments rather than re-running the engine,
which means every detector is scored on an identical composite series and
the comparison is about the decision rule and nothing else.
"""

from __future__ import annotations

import json
from pathlib import Path

from bellwether_engine.compare import (
    dominates,
    engine_flags,
    evaluate,
    shewhart_composite,
    shewhart_feature,
)

REPO = Path(__file__).resolve().parents[1]
PERSONAS = REPO / "fixtures" / "personas"

COMPOSITE_THRESHOLDS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
FEATURE_Z = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]


def load(persona: str, name: str):
    return json.loads((PERSONAS / persona / f"{name}.json").read_text(encoding="utf8"))


def main() -> int:
    stable = load("alex-stable", "assessments")
    drift = load("alex-drift", "assessments")
    ramp_start = load("alex-drift", "meta")["drift_start_date"]

    ours = evaluate(stable, drift, ramp_start, engine_flags)

    composite_sweep = [
        {
            "threshold": t,
            **evaluate(stable, drift, ramp_start, lambda a, t=t: shewhart_composite(a, t)),
        }
        for t in COMPOSITE_THRESHOLDS
    ]
    feature_sweep = [
        {
            "z": z,
            **evaluate(stable, drift, ramp_start, lambda a, z=z: shewhart_feature(a, z)),
        }
        for z in FEATURE_Z
    ]

    alternatives = composite_sweep + feature_sweep
    beaten_by = [alt for alt in alternatives if dominates(alt, ours)]

    # The fairest single comparison a reader can hold in their head: among
    # the simpler settings that raise no false alarm at all, how late is the
    # best of them?
    quiet = [a for a in alternatives if a["falseAlarmsOnStable"] == 0 and a["daysIntoChangeBeforeFirstFlag"]]
    best_quiet = min(quiet, key=lambda a: a["daysIntoChangeBeforeFirstFlag"]) if quiet else None

    # And the mirror: among settings fast enough to match us, what do they cost?
    fast = [
        a
        for a in alternatives
        if a["daysIntoChangeBeforeFirstFlag"]
        and a["daysIntoChangeBeforeFirstFlag"] <= (ours["daysIntoChangeBeforeFirstFlag"] or 10**6)
    ]
    cheapest_fast = min(fast, key=lambda a: a["falseAlarmsOnStable"]) if fast else None

    out = {
        "what": "Bellwether's accumulating decision rule against the two a reasonable engineer builds first",
        "method": (
            "Every detector is scored on the same committed persona assessments, so all of them "
            "see identical features, an identical per-person EWMA baseline, identical concern "
            "signing and identical low-exposure exclusions. Only the decision rule differs."
        ),
        "personas": {
            "stable": "no injected change; every flag is a false alarm",
            "drift": f"identical until {ramp_start}, then a gradual two-week change",
            "rampStart": ramp_start,
        },
        "bellwether": {"rule": "one-sided CUSUM on the concern-signed composite, k 0.5, h 5.0", **ours},
        "alternatives": {
            "shewhartComposite": {
                "rule": "flag the day the composite exceeds a fixed threshold",
                "sweep": composite_sweep,
            },
            "shewhartFeature": {
                "rule": "flag the day any single feature's concern-signed z exceeds a threshold",
                "sweep": feature_sweep,
            },
        },
        "result": {
            "settingsBeatingBellwetherOnBothAxes": len(beaten_by),
            "bestAlternativeWithZeroFalseAlarms": best_quiet,
            "cheapestAlternativeMatchingOurDetectionSpeed": cheapest_fast,
        },
        "limit": (
            "Both personas are synthetic and authored by this project. This measures that the "
            "decision rule matters and by how much on a change of known shape and timing. It is "
            "not evidence that the detector works on a real person, and it is not offered as any."
        ),
    }

    dest = REPO / "fixtures" / "detector-comparison.json"
    dest.write_text(json.dumps(out, indent=1), encoding="utf8")

    print(f"Bellwether: {ours['falseAlarmsOnStable']} false alarms, "
          f"first flag on day {ours['daysIntoChangeBeforeFirstFlag']} of the change.")
    print(f"Simpler settings that beat it on both axes: {len(beaten_by)}")
    if best_quiet:
        label = best_quiet.get("threshold", best_quiet.get("z"))
        print(f"Best simpler setting with no false alarms: {label} -> day "
              f"{best_quiet['daysIntoChangeBeforeFirstFlag']}")
    if cheapest_fast:
        label = cheapest_fast.get("threshold", cheapest_fast.get("z"))
        print(f"Cheapest simpler setting that keeps up: {label} -> "
              f"{cheapest_fast['falseAlarmsOnStable']} false alarms")
    print(f"\nWrote {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
