"""Run Bellwether's engine over real human speech that nobody here authored.

    pip install convokit
    python harness/scotus/run.py

That is the exact command that produced the committed `results.json`. It
downloads the 2019 term (7 MB) if no corpus path is given. One term is the
right unit rather than a limitation: a justice does not undergo a systematic
language change inside a single nine-month term, which is what makes a flag
inside a series a false alarm. Spanning decades would confound restraint
with ordinary ageing. Point `--corpus` at the full 1.3 GB archive to run
wider.

Why this corpus
---------------
Everything else in this repository is measured on two synthetic personas we
wrote. That is enough to show the decision rule earns its complexity
(`fixtures/detector-comparison.json`) and not enough to show anything about
a real person, because a person we invented cannot surprise us.

The Supreme Court oral argument corpus is the closest freely available thing
to what Bellwether needs: the same named individuals speaking spontaneously,
unscripted, across dozens of separate sessions inside a single term,
transcribed by professional court reporters and published by the Court.
ConvoKit distributes it (Cornell Conversational Analysis Toolkit), derived
from the Oyez Project.

    Corpus:  supreme-corpus, ConvoKit
    Source:  Oyez Project transcripts of US Supreme Court oral arguments
    Licence: check the ConvoKit corpus page before republishing any text.
             This harness publishes counts and feature statistics only and
             no transcript text, which is also what Bellwether itself does.

What it measures
----------------
Three things, in the order they have to be established.

1. **Why an own baseline at all.** How far apart are two different people,
   in units of one person's own session-to-session variability? Bellwether's
   central design claim is that a person must be compared with their own
   past rather than with a population, and this corpus can test that claim
   instead of asserting it.

2. **Restraint on real speech.** How often does the engine flag a change in
   someone whose speech has no reason to have changed? Each justice within
   each term is one series. A justice does not undergo a systematic language
   change over a single nine-month term, so a flag inside a series is, to a
   first approximation, a false alarm. Every one is counted and none is
   explained away.

3. **Sensitivity on real speech, with a known effect size.** A specificity
   result of zero is worthless on its own, because a detector that never
   fires scores a perfect zero and is useless. So a real justice's real
   sessions are shifted in the concerning direction by a known multiple of
   that justice's own standard deviation, ramped over fourteen sessions
   exactly as the synthetic persona ramps, and the magnitude is swept.

What it does not measure
------------------------
Anything about dementia. There is no labelled cognitive change anywhere in
this corpus and this harness does not pretend otherwise. It measures how the
detector behaves on real spontaneous speech from real people, which is the
half that synthetic personas cannot establish, and nothing beyond that.

Three limits that shape every number here and are reported with them:

1. **A session is not a day.** Bellwether normally sees everything a person
   says in a day. Here it sees one argument, a few hundred to a few thousand
   words in a formal register. Sessions are given sequential dates because
   the engine's EWMA and CUSUM advance per observation rather than per
   elapsed day, so calendar gaps change nothing, but "day" in the output
   means "one oral argument".

2. **Professional transcription removes two of the nine features.** Court
   reporters strip "um" and "uh": across a full term they survive at about
   0.02 per thousand words. Filler rate and disfluency rate are therefore
   near-constant here, and the absolute standard-deviation floors in
   `EngineConfig.sd_floor_abs` are what stop that from producing nonsense.
   This corpus exercises seven of the nine features honestly and the other
   two only as a test that those floors hold.

3. **Appellate argument is a register, not everyday speech.** Vocabulary is
   legal, sentences are long, and the person is performing. The baseline is
   per-person so the register is absorbed into their normal, but nothing
   here says how the detector behaves on kitchen-table conversation.
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from bellwether_engine.baseline import DEFAULT_CONFIG, DIRECTION, assess
from speech_vitals import FEATURE_NAMES, Utterance, aggregate_day

REPO = Path(__file__).resolve().parents[2]

# A series needs enough sessions after warmup to be worth scoring at all.
MIN_ASSESSED = 14
# The injected change ramps over this many sessions, matching the persona.
RAMP_SESSIONS = 14


def load_sessions(corpus_path: str, terms: set[str] | None = None):
    """Group every justice's words into one text per (term, case).

    Justices are interrupted constantly, so a single utterance is a
    fragment. The unit that corresponds to "everything this person said in
    one sitting" is the whole case.
    """
    from convokit import Corpus

    corpus = Corpus(filename=corpus_path)
    grouped: dict[tuple[str, str, str], list[str]] = collections.defaultdict(list)
    for utterance in corpus.iter_utterances():
        if utterance.meta.get("speaker_type") != "J":
            continue
        text = (utterance.text or "").strip()
        if not text:
            continue
        case_id = str(utterance.meta.get("case_id", ""))
        term = case_id.split("_")[0] if "_" in case_id else case_id
        if not term.isdigit():
            continue
        if terms and term not in terms:
            continue
        grouped[(utterance.speaker.id, term, case_id)].append(text)
    return grouped


def series_for(grouped) -> dict[tuple[str, str], list[tuple[str, str]]]:
    """One series per justice per term, as an ordered list of (case, text)."""
    series: dict[tuple[str, str], list[tuple[str, str]]] = collections.defaultdict(list)
    for (speaker, term, case_id), parts in grouped.items():
        series[(speaker, term)].append((case_id, " ".join(parts)))
    for key in series:
        # Case ids are not reliably chronological, so this is a stable order
        # rather than a true one. Nothing in the engine depends on the
        # calendar, only on the sequence being fixed and seen exactly once.
        series[key].sort()
    return series


def features_for(session_texts: list[tuple[str, str]]):
    """Feature rows, one per session, with sequential dates.

    The dates are a device and are labelled as one above. What matters is
    that each session is seen exactly once, in a fixed order.
    """
    start = date(2000, 1, 1)
    rows = []
    for index, (_case, text) in enumerate(session_texts):
        stamp = (start + timedelta(days=index)).isoformat()
        pieces = [line for line in text.split("\n") if line.strip()] or [text]
        utterances = [
            Utterance(ts=f"{stamp}T12:00:00Z", text=piece, speaker="justice")
            for piece in pieces
        ]
        rows.append(aggregate_day(utterances, date=stamp))
    return rows


def separation_table(per_speaker: dict[str, list]) -> list[dict]:
    """Between-speaker spread against within-speaker spread, per feature."""
    table = []
    for name in FEATURE_NAMES:
        values = {sp: [getattr(d, name) for d in rows] for sp, rows in per_speaker.items()}
        usable = [v for v in values.values() if len(v) > 1]
        if len(usable) < 2:
            continue
        within = statistics.mean(statistics.pstdev(v) for v in usable)
        between = statistics.pstdev([statistics.mean(v) for v in usable])
        table.append(
            {
                "feature": name,
                "withinSpeakerSd": round(within, 4),
                "betweenSpeakerSd": round(between, 4),
                "betweenOverWithin": round(between / within, 2) if within else None,
            }
        )
    return table


def inject(rows: list, cut: int, magnitude: float) -> list:
    """A real series with a known shift applied from ``cut`` onward.

    Every feature moves in its own concerning direction by ``magnitude``
    times that person's own standard deviation, ramping in over
    ``RAMP_SESSIONS``. Expressing the size in within-person standard
    deviations is the only framing that means anything for a detector whose
    whole premise is comparing someone with themselves.
    """
    sds = {
        name: statistics.pstdev([getattr(d, name) for d in rows[:cut]]) or 0.0
        for name in FEATURE_NAMES
    }
    out = []
    for index, row in enumerate(rows):
        if index < cut:
            out.append(row)
            continue
        ramp = min(1.0, (index - cut + 1) / RAMP_SESSIONS)
        patch = {}
        for name in FEATURE_NAMES:
            sign = -1.0 if DIRECTION[name] == "lower_is_concerning" else 1.0
            patch[name] = getattr(row, name) + sign * magnitude * sds[name] * ramp
        out.append(replace(row, **patch))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Bellwether on real speech")
    parser.add_argument(
        "--corpus",
        default="",
        help="path to a downloaded ConvoKit supreme corpus; blank downloads supreme-2019",
    )
    parser.add_argument("--out", default=str(REPO / "harness" / "scotus" / "results.json"))
    parser.add_argument("--min-assessed", type=int, default=MIN_ASSESSED)
    parser.add_argument("--terms", default="", help="comma separated terms, blank for all")
    args = parser.parse_args()

    wanted = {t.strip() for t in args.terms.split(",") if t.strip()} or None
    corpus_path = args.corpus
    if not corpus_path:
        # supreme-2019 is 7 MB against 1.3 GB for the whole archive, and one
        # term is the right unit anyway: a justice does not undergo a
        # systematic language change inside a single term, which is what
        # makes a flag inside a series a false alarm. Spanning decades would
        # confound the restraint measurement with ordinary ageing.
        from convokit import download

        corpus_path = download("supreme-2019")
    grouped = load_sessions(corpus_path, wanted)
    series = series_for(grouped)
    print(f"{len(series)} justice-term series from {len(grouped)} justice-case sessions")

    rows = []
    per_speaker: dict[str, list] = {}
    for (speaker, term), sessions in sorted(series.items()):
        assessments = assess(features_for(sessions), DEFAULT_CONFIG)
        scored = [a for a in assessments if a.composite is not None]
        if len(scored) < args.min_assessed:
            continue

        flagged = [a for a in scored if a.tier in ("watch", "discuss")]
        rows.append(
            {
                "speaker": speaker,
                "term": term,
                "sessions": len(sessions),
                "assessed": len(scored),
                "excludedLowExposure": sum(1 for a in assessments if not a.eligible),
                "flagged": len(flagged),
                "maxComposite": round(max(a.composite for a in scored), 3),
                "medianComposite": round(statistics.median(a.composite for a in scored), 3),
            }
        )
        eligible = [
            d for d in features_for(sessions) if d.token_count_day >= DEFAULT_CONFIG.min_tokens
        ]
        per_speaker.setdefault(speaker, []).extend(eligible)

    separation = separation_table(per_speaker)

    # Sensitivity, swept over the size of a real change.
    sensitivity = []
    subjects = sorted(per_speaker, key=lambda sp: -len(per_speaker[sp]))[:5]
    # Zero is in the sweep on purpose. It is the same real series with
    # nothing done to it, so it must detect nobody. If it ever detects
    # someone, every other row of this table is measuring the engine
    # tripping over its own tail rather than over the injected change.
    for magnitude in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
        detected, delays = 0, []
        for speaker in subjects:
            base = per_speaker[speaker]
            cut = len(base) // 2
            assessments = assess(inject(base, cut, magnitude), DEFAULT_CONFIG)
            scored = [a for a in assessments if a.composite is not None]
            after = [
                i
                for i, a in enumerate(scored)
                if i >= cut and a.tier in ("watch", "discuss")
            ]
            if after:
                detected += 1
                delays.append(after[0] - cut + 1)
        sensitivity.append(
            {
                "shiftInWithinPersonSd": magnitude,
                "subjectsDetected": detected,
                "ofSubjects": len(subjects),
                "medianSessionsToDetect": statistics.median(delays) if delays else None,
            }
        )

    total_assessed = sum(r["assessed"] for r in rows)
    total_flagged = sum(r["flagged"] for r in rows)
    clean_series = sum(1 for r in rows if r["flagged"] == 0)

    out = {
        "corpus": {
            "name": "Supreme Court oral arguments (ConvoKit supreme-corpus, from the Oyez Project)",
            "authoredByUs": False,
            "unit": "one oral argument by one justice, treated as one day",
            "termsCovered": sorted({r["term"] for r in rows}),
        },
        "whyOwnBaseline": {
            "question": (
                "How far apart are two different people, in units of one person's own "
                "session-to-session variability? If the answer is below one, comparing a "
                "person against a population asks a detector to resolve a difference "
                "smaller than the noise it has to tolerate anyway."
            ),
            "perFeature": separation,
            "allBelowOne": all(
                r["betweenOverWithin"] is not None and r["betweenOverWithin"] < 1.0
                for r in separation
            ),
        },
        "restraint": {
            "question": (
                "How often does the engine flag a change in someone whose speech has no "
                "reason to have changed? One series is one justice in one term."
            ),
            "series": len(rows),
            "distinctSpeakers": len({r["speaker"] for r in rows}),
            "sessionsAssessed": total_assessed,
            "sessionsFlagged": total_flagged,
            "flaggedPercent": round(100 * total_flagged / total_assessed, 2) if total_assessed else None,
            "seriesWithNoFlagAtAll": clean_series,
        },
        "sensitivity": {
            "what": (
                "A real justice's real sessions, with every feature shifted in its "
                "concerning direction by a known multiple of that justice's own standard "
                "deviation, ramped over fourteen sessions exactly as the synthetic persona "
                "ramps."
            ),
            "whyNotASpliceOfTwoSpeakers": (
                "That was the first attempt and it mostly did not fire. The separation "
                "table is why: two different justices sit closer together than one "
                "justice's own range on every feature, so the splice asked the engine to "
                "resolve a change smaller than the noise it is built to ignore. Its "
                "failure said nothing about the engine. It is recorded because the wrong "
                "control nearly became the published result."
            ),
            "sweep": sensitivity,
        },
        "limits": [
            "A session is one oral argument, not a day of a person's life.",
            "Professional transcription strips um and uh, so filler rate and disfluency "
            "rate are near-constant here and this corpus exercises seven of the nine "
            "features honestly.",
            "Appellate argument is a formal register, not kitchen-table conversation.",
            "There is no labelled cognitive change in this corpus. Nothing here is "
            "evidence about dementia, and none of it is offered as any.",
            "The injected change is applied to feature rows rather than to speech, so it "
            "tests the baseline and the decision rule, not the extractor.",
        ],
        "seriesDetail": rows,
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf8")

    print(f"\nseries scored:       {len(rows)}")
    print(f"sessions assessed:   {total_assessed}")
    print(f"sessions flagged:    {total_flagged} ({out['restraint']['flaggedPercent']} percent)")
    print(f"series with no flag: {clean_series} of {len(rows)}")
    print("\nbetween-speaker over within-speaker SD:")
    for r in separation:
        print(f"  {r['feature']:22} {r['betweenOverWithin']}")
    print("\nsensitivity, shift in within-person SD:")
    for r in sensitivity:
        print(
            f"  {r['shiftInWithinPersonSd']:>4} SD -> detected in "
            f"{r['subjectsDetected']} of {r['ofSubjects']}, median "
            f"{r['medianSessionsToDetect']} sessions"
        )
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
