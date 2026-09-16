"""Synthetic personas: real pipeline, simulated speech.

This is Bellwether's equivalent of Nightlight's simulated household. The
text is generated; everything downstream is the production code. Each
persona's utterances go through the real speech-vitals extractor and the
real baseline engine, so the demo dashboard, the tests, and the video all
show the actual product reacting to known ground truth, and the label
SIMULATED is carried in every output file.

Why generate text rather than feature numbers: feature numbers would only
test the engine. Text tests the claim that matters, that a change in how
someone talks is visible in the features at all, and it produces a fixture
that a reviewer can read and judge for plausibility.

Personas:
  alex-stable   eight weeks of ordinary variation, nothing changes
  alex-drift    the same person, with a gradual change beginning in week
                six: shorter sentences, more "it" and "they", more ums,
                fewer specific words, less subordination. Ramped over two
                weeks rather than switched on, because that is how a real
                change would arrive.

Run:  python fixtures/personas/generate.py [--out fixtures/personas] [--days 56] [--seed 7]
"""

from __future__ import annotations

import argparse
import json
import os
import random
from datetime import date, datetime, timedelta, timezone

from bellwether_engine import assess, summarize
from speech_vitals import Utterance, aggregate_day

START = date(2026, 7, 27)  # a Monday; eight weeks lands on the video week
OWNER = "speaker_1"
OTHER = "speaker_2"

NOUNS = [
    "garden", "crossword", "letter", "kettle", "allotment", "bus timetable", "recipe",
    "photograph", "hedge", "bookshelf", "radio", "greenhouse", "pension form", "thermostat",
    "bird feeder", "library book", "newspaper", "wheelbarrow", "back door", "calendar",
]
PLACES = ["the shop", "the surgery", "the park", "next door", "the church hall", "the market", "the post office"]
PEOPLE = ["Margaret", "the neighbours", "our Sarah", "the postman", "Dr Patel", "the woman from the council", "Tom"]
RARE_ADJ = ["verdant", "taciturn", "gossamer", "ineffable", "quixotic", "ephemeral", "perfunctory", "laconic", "sonorous", "diaphanous"]
RARE_NOUN = ["soliloquy", "reverie", "cadence", "penumbra", "vestibule", "susurrus", "equinox", "palimpsest", "lacuna", "sinecure"]
RARE_VERB = ["perambulate", "ruminate", "meander", "acquiesce", "extol", "ameliorate", "vacillate", "burgeon"]

# Sentence complexity tiers. Complex sentences subordinate and use a rare
# word; simple ones are short, pronoun-heavy, and vague.
COMPLEX = [
    "Although the {radj} light made the {noun} look quite different this morning, I still finished it before {person} came round, which surprised me.",
    "I was going to {rverb} down to {place} after lunch, but the rain that started around eleven put me off, so I sorted the {noun} instead.",
    "What struck me about the {noun}, once I had looked at it properly, was how much the {rnoun} of the whole thing had changed since spring.",
    "Because {person} had mentioned the {noun} on Tuesday, I dug out the old {noun2}, which turned out to be exactly where I had left it in March.",
    "If the weather holds, I think I will {rverb} along the river path that runs behind {place}, since the {radj} hedges are worth seeing before they go over.",
    "The {rnoun} of the afternoon, if that is the word, was that {person} and I finally agreed about the {noun}, after arguing about it for the best part of a year.",
]
MEDIUM = [
    "I finished the {noun} this morning and then walked to {place} for bread.",
    "{person} rang about the {noun}, so we are meeting on Thursday.",
    "The {noun} needs sorting before the weekend, I think.",
    "We went to {place} and had a look at the {noun} on the way back.",
    "I read the paper, did the {noun}, and then had a nap after lunch.",
    "It rained most of the afternoon, so I stayed in and dealt with the {noun}.",
    "I need to remember to ask {person} about the {noun2} when I see them.",
]
SIMPLE = [
    "It was fine.",
    "We did that thing.",
    "I put it over there.",
    "They came and we talked.",
    "He said it was okay.",
    "I forget what it was.",
    "It is somewhere in there.",
    "She brought the thing for it.",
    "We went to that place.",
    "I did it. Then I did the other one.",
]
REPLIES = [
    "Did you?", "That sounds nice.", "Right.", "When was that?", "Oh I see.",
    "Shall I put the kettle on?", "I think so, yes.", "Go on.",
]

FILLERS = ["um", "uh", "er"]


def fill(template: str, rng: random.Random) -> str:
    return template.format(
        noun=rng.choice(NOUNS), noun2=rng.choice(NOUNS), place=rng.choice(PLACES),
        person=rng.choice(PEOPLE), radj=rng.choice(RARE_ADJ), rnoun=rng.choice(RARE_NOUN),
        rverb=rng.choice(RARE_VERB),
    )


def degrade(text: str, level: float, rng: random.Random) -> str:
    """Apply drift to a sentence: fillers, repetitions, vagueness. ``level``
    runs 0 (none) to 1 (full)."""
    # Everyone says "um" sometimes. A baseline with no fillers at all has
    # zero variance, and the first real "um" then looks like an emergency;
    # that is how the engine's absolute floors were found. Small natural
    # rates here keep the stable persona honest.
    words = text.split()
    out: list[str] = []
    for i, w in enumerate(words):
        # Filled pause before some words.
        if rng.random() < 0.012 + 0.10 * level:
            out.append(rng.choice(FILLERS) + ",")
        # Occasional immediate repetition, the classic restart.
        if rng.random() < 0.006 + 0.05 * level and w.isalpha():
            out.append(w)
        out.append(w)
    if level <= 0:
        return " ".join(out)
    text = " ".join(out)
    # Sometimes the specific word gives way to "the thing".
    if rng.random() < 0.25 * level:
        for n in NOUNS:
            if n in text:
                text = text.replace(n, "thing", 1)
                break
    return text


def persona_day(day_index: int, drift_start: int | None, rng: random.Random, low_exposure: bool):
    """One day's utterances for the owner and a bystander."""
    level = 0.0
    if drift_start is not None and day_index >= drift_start:
        level = min(1.0, (day_index - drift_start + 1) / 14.0)  # two-week ramp

    # Mixture of complexity tiers; drift shifts mass toward simple.
    p_complex = 0.30 * (1 - 0.8 * level)
    p_simple = 0.20 + 0.55 * level
    p_medium = max(0.0, 1 - p_complex - p_simple)

    n = 3 if low_exposure else max(25, min(70, int(rng.gauss(45, 8))))
    day = START + timedelta(days=day_index)
    minute = 7 * 60 + rng.randint(0, 30)
    out: list[Utterance] = []
    for _ in range(n):
        minute += rng.randint(2, 25)
        if minute > 22 * 60:
            break
        ts = datetime(day.year, day.month, day.day, minute // 60, minute % 60, rng.randint(0, 59), tzinfo=timezone.utc)
        iso = ts.isoformat().replace("+00:00", "Z")
        r = rng.random()
        if r < p_complex:
            text = fill(rng.choice(COMPLEX), rng)
        elif r < p_complex + p_medium:
            text = fill(rng.choice(MEDIUM), rng)
        else:
            text = rng.choice(SIMPLE)
        out.append(Utterance(ts=iso, text=degrade(text, level, rng), speaker=OWNER, conversation_id=f"c-{day.isoformat()}"))
        # A bystander replies about a fifth of the time, to exercise the owner filter.
        if rng.random() < 0.2:
            minute += 1
            ts2 = ts + timedelta(seconds=rng.randint(5, 40))
            out.append(Utterance(ts=ts2.isoformat().replace("+00:00", "Z"), text=rng.choice(REPLIES), speaker=OTHER, conversation_id=f"c-{day.isoformat()}"))
    return out, level


def build(name: str, days: int, seed: int, drift_start: int | None, out_dir: str) -> dict:
    rng = random.Random(seed)
    low_days = {12, 33}
    annotations = {(START + timedelta(days=20)).isoformat(): "travel, slept badly"}
    all_utts: list[Utterance] = []
    day_feats = []
    levels = {}
    for i in range(days):
        utts, level = persona_day(i, drift_start, rng, low_exposure=(i in low_days))
        all_utts.extend(utts)
        levels[(START + timedelta(days=i)).isoformat()] = round(level, 3)
        owner_only = [u for u in utts if u.speaker == OWNER]
        day_feats.append(aggregate_day(owner_only, (START + timedelta(days=i)).isoformat()).to_dict())

    assessments = assess(day_feats, annotations=annotations)
    summary = summarize(assessments)

    pdir = os.path.join(out_dir, name)
    os.makedirs(pdir, exist_ok=True)
    with open(os.path.join(pdir, "utterances.jsonl"), "w", encoding="utf-8") as fh:
        for u in all_utts:
            fh.write(json.dumps({"ts": u.ts, "text": u.text, "speaker": u.speaker, "conversation_id": u.conversation_id}) + "\n")
    with open(os.path.join(pdir, "days.json"), "w", encoding="utf-8") as fh:
        json.dump(day_feats, fh, indent=1)
    with open(os.path.join(pdir, "assessments.json"), "w", encoding="utf-8") as fh:
        json.dump([a.to_dict() for a in assessments], fh, indent=1)
    with open(os.path.join(pdir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary.to_dict(), fh, indent=1)
    meta = {
        "label": "SIMULATED",
        "persona": name,
        "description": (
            "Synthetic everyday speech for one person. Generated text; production extractor and engine."
        ),
        "seed": seed,
        "days": days,
        "start": START.isoformat(),
        "drift_start_day": drift_start,
        "drift_start_date": (START + timedelta(days=drift_start)).isoformat() if drift_start is not None else None,
        "drift_level_by_date": levels,
        "low_exposure_days": sorted((START + timedelta(days=d)).isoformat() for d in low_days),
        "annotations": annotations,
        "owner_speaker": OWNER,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    with open(os.path.join(pdir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)

    tiers = "".join({"learning": "L", "stable": ".", "watch": "w", "discuss": "D", "excluded": "x"}[a.tier] for a in assessments)
    return {"name": name, "tiers": tiers, "summary": summary.to_dict(), "utterances": len(all_utts)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", default=os.path.join("fixtures", "personas"))
    p.add_argument("--days", type=int, default=56)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args(argv)

    results = [
        build("alex-stable", args.days, args.seed, None, args.out),
        build("alex-drift", args.days, args.seed, 35, args.out),
    ]
    for r in results:
        print(f"{r['name']:12} {r['utterances']:5} utterances")
        print(f"  tiers  {r['tiers']}")
        print(f"  now    {r['summary']['tier']} since {r['summary']['since']}  contributors={list(r['summary']['contributors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
