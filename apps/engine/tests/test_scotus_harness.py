"""The external harness, tested as code and pinned as claims.

The harness in `harness/scotus/` runs Bellwether's engine over real
spontaneous speech from real people that nobody here wrote. Its numbers are
the only ones in this repository that are not measured on personas we
authored, which makes them the ones most worth protecting from drift.

The first half tests the harness's own logic on inputs small enough to check
by hand. The injection in particular has to be right or the sensitivity
sweep is fiction: a shift applied in the wrong direction would measure the
engine ignoring an improvement.

The second half pins the committed result. Those tests skip when the result
file is absent, because the corpus is a separate download and a fresh clone
should not fail its test suite over a 1.3 GB file it was never asked to
fetch. Everything else in this repository runs without it.

Regenerate: pip install convokit, then
    python harness/scotus/run.py --out harness/scotus/results.json
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "harness" / "scotus"))

from speech_vitals import FEATURE_NAMES, DayFeatures  # noqa: E402

from bellwether_engine.baseline import DIRECTION  # noqa: E402

RESULTS = REPO / "harness" / "scotus" / "results.json"
needs_corpus = pytest.mark.skipif(
    not RESULTS.exists(), reason="run harness/scotus/run.py; needs the ConvoKit corpus"
)


def row(date: str, **over) -> DayFeatures:
    base = dict(
        date=date,
        utterances=10,
        token_count_day=500,
        vocab_size_day=200.0,
        mattr=0.75,
        mean_utt_len=16.0,
        dep_depth_mean=4.5,
        pronoun_noun_ratio=0.3,
        filler_rate=2.0,
        disfluency_rate=1.0,
        low_freq_word_rate=6.0,
        idea_density=5.0,
    )
    base.update(over)
    return DayFeatures(**base)


# --------------------------------------------------------------------------
# The harness logic
# --------------------------------------------------------------------------


def test_injection_leaves_the_baseline_half_untouched():
    from run import inject

    rows = [row(f"2000-01-{d:02d}") for d in range(1, 21)]
    out = inject(rows, cut=10, magnitude=2.0)
    assert out[:10] == rows[:10]


def test_injection_moves_every_feature_the_concerning_way():
    """The direction is the whole correctness of the sweep.

    Shift a feature the reassuring way and the sensitivity table would be
    measuring how well the engine ignores someone getting better, which
    would look like a result and be worthless.
    """
    from run import inject

    # Enough spread in the baseline half for a per-feature sd to exist.
    rows = [row(f"2000-01-{d:02d}", mattr=0.70 + 0.01 * d, mean_utt_len=14.0 + d) for d in range(1, 21)]
    out = inject(rows, cut=10, magnitude=3.0)

    last_original, last_shifted = rows[-1], out[-1]
    for name in ("mattr", "mean_utt_len"):
        moved = getattr(last_shifted, name) - getattr(last_original, name)
        if DIRECTION[name] == "lower_is_concerning":
            assert moved < 0, name
        else:
            assert moved > 0, name


def test_injection_ramps_rather_than_stepping():
    from run import RAMP_SESSIONS, inject

    rows = [row(f"2000-02-{d:02d}", mattr=0.70 + 0.005 * d) for d in range(1, 29)]
    out = inject(rows, cut=7, magnitude=2.0)
    first = abs(out[7].mattr - rows[7].mattr)
    later = abs(out[7 + RAMP_SESSIONS - 1].mattr - rows[7 + RAMP_SESSIONS - 1].mattr)
    assert first < later


def test_a_zero_magnitude_injection_changes_nothing():
    """The control that makes the rest of the sweep interpretable."""
    from run import inject

    rows = [row(f"2000-03-{d:02d}", mattr=0.70 + 0.004 * d) for d in range(1, 21)]
    assert inject(rows, cut=10, magnitude=0.0) == rows


def test_a_feature_with_no_variation_cannot_be_shifted():
    # The shift is expressed in the person's own standard deviations, so a
    # feature that never moved has no scale to shift along. It stays put
    # rather than producing a nonsense jump.
    from run import inject

    rows = [row(f"2000-04-{d:02d}") for d in range(1, 21)]
    out = inject(rows, cut=10, magnitude=5.0)
    assert out[-1].mattr == rows[-1].mattr


def test_separation_compares_speakers_against_their_own_spread():
    from run import separation_table

    tight = [row(f"2000-05-{d:02d}", mattr=0.70 + 0.001 * d) for d in range(1, 11)]
    other = [row(f"2000-06-{d:02d}", mattr=0.90 + 0.001 * d) for d in range(1, 11)]
    table = {r["feature"]: r for r in separation_table({"a": tight, "b": other})}
    # Two speakers 0.2 apart, each varying by a thousandth: hugely separable.
    assert table["mattr"]["betweenOverWithin"] > 1.0


def test_separation_needs_two_speakers_to_mean_anything():
    from run import separation_table

    only = [row(f"2000-07-{d:02d}", mattr=0.70 + 0.001 * d) for d in range(1, 11)]
    assert separation_table({"a": only}) == []


# --------------------------------------------------------------------------
# What the committed run found
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def results():
    return json.loads(RESULTS.read_text(encoding="utf8"))


@needs_corpus
def test_the_corpus_is_not_ours(results):
    assert results["corpus"]["authoredByUs"] is False
    assert "Oyez" in results["corpus"]["name"]


@needs_corpus
def test_the_engine_is_quiet_on_real_unchanged_speakers(results):
    """The negative control, on speech nobody here wrote."""
    r = results["restraint"]
    assert r["sessionsAssessed"] > 300
    assert r["sessionsFlagged"] == 0
    assert r["seriesWithNoFlagAtAll"] == r["series"]


@needs_corpus
def test_the_zero_shift_row_detects_nobody(results):
    """Without this the sensitivity table is measuring the engine's own tail.

    The same real series, with nothing done to it, must detect nobody. If it
    ever does, every other row of the sweep is reporting a coincidence.
    """
    sweep = {r["shiftInWithinPersonSd"]: r for r in results["sensitivity"]["sweep"]}
    assert 0.0 in sweep, "the sweep must include the do-nothing control"
    assert sweep[0.0]["subjectsDetected"] == 0


@needs_corpus
def test_a_sustained_shift_of_one_and_a_half_sd_is_caught_in_everyone(results):
    sweep = {r["shiftInWithinPersonSd"]: r for r in results["sensitivity"]["sweep"]}
    row_ = sweep[1.5]
    assert row_["subjectsDetected"] == row_["ofSubjects"]


@needs_corpus
def test_bigger_changes_are_not_harder_to_find(results):
    # Monotonic in the direction that has to hold for the sweep to be
    # believable at all. A detector that found 2 SD less often than 1 SD
    # would be reporting an artefact.
    sweep = sorted(results["sensitivity"]["sweep"], key=lambda r: r["shiftInWithinPersonSd"])
    found = [r["subjectsDetected"] for r in sweep]
    assert found == sorted(found)


@needs_corpus
def test_two_different_people_sit_closer_than_one_persons_own_range(results):
    """The measured case for comparing someone with themselves.

    Bellwether's central design choice is n-of-1. This is the evidence for
    it, and it comes from real speech: on every one of the nine features,
    the spread between different justices is smaller than the spread within
    a single justice's own sessions. Comparing a person against a population
    would be asking a detector to resolve a difference smaller than the
    noise it has to tolerate anyway.
    """
    why = results["whyOwnBaseline"]
    assert why["allBelowOne"] is True
    assert len(why["perFeature"]) == len(FEATURE_NAMES)
    for feature in why["perFeature"]:
        assert 0 < feature["betweenOverWithin"] < 1.0, feature["feature"]


@needs_corpus
def test_the_failed_first_control_is_on_the_record(results):
    # The splice control did not fire and nearly became the published
    # result. Deleting it would have been the easy move.
    assert "mostly did not fire" in results["sensitivity"]["whyNotASpliceOfTwoSpeakers"]


@needs_corpus
def test_it_refuses_to_be_read_as_evidence_about_dementia(results):
    limits = " ".join(results["limits"])
    assert "no labelled cognitive change" in limits
    assert "Nothing here is evidence about dementia" in limits
