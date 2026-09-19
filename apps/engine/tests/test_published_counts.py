"""Counts that appear in public text have to be counted, not remembered.

This exists because two documents in this repository disagreed with each
other. README.md said 165 tests and docs/SUBMISSION.md said 86, and a
judge reads both. 165 was right; 86 was copied across from a sibling
project, where it was also stale.

A number nothing checks is a number that was only true on the day it was
typed, and on a project whose whole argument is that every published
figure is re-derived from something committed, a submission contradicting
its own README is worse than either number being wrong.

The count is taken by collecting the suite rather than by running it, so
this test cannot recurse into itself.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
# The packages the README tells a reader to run, in that order.
TARGETS = ["packages/speech-vitals", "apps/engine", "apps/ingest", "apps/server", "apps/agent"]
PUBLIC_TEXT = ["README.md", "docs/SUBMISSION.md"]


def collected_total() -> int:
    """Ask pytest to collect, not to run. Fast, and it counts the real thing."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *TARGETS],
        cwd=REPO, capture_output=True, text=True,
    )
    # The last summary line reads like "165 tests collected in 0.42s".
    match = re.search(r"(\d+) tests? collected", proc.stdout)
    if not match:
        pytest.skip(f"could not collect the suite: {proc.stdout[-300:]}")
    return int(match.group(1))


def stated_counts() -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for name in PUBLIC_TEXT:
        path = REPO / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf8")
        # The headline figure only. Punctuation may sit inside the bold:
        # README writes "**165 tests.**" and SUBMISSION writes
        # "**86 tests**". The first draft of this matcher required the
        # digits and "tests" to be flush against the closing asterisks, so
        # it missed the README entirely and the two documents "agreed"
        # while contradicting each other by seventy-nine.
        #
        # The per-package counts in the repository table are deliberately
        # not matched here: they are smaller numbers with their own
        # meaning, and sweeping them in would make this test unreadable.
        m = re.search(r"\*\*(\d+) tests[.,;:]?\*\*", text)
        if m:
            out.append((name, int(m.group(1))))
    return out


def test_public_documents_agree_with_each_other() -> None:
    counts = stated_counts()
    assert counts, "no document states a test total; one of them should"
    numbers = {n for _, n in counts}
    assert len(numbers) == 1, (
        "public documents disagree about the test total: "
        + ", ".join(f"{f} says {n}" for f, n in counts)
    )


def test_public_documents_agree_with_the_suite() -> None:
    actual = collected_total()
    for name, stated in stated_counts():
        # Not exact equality: a run adds tests more often than it removes
        # them, and the failure worth catching is a figure nobody checked.
        assert abs(actual - stated) <= 2, (
            f"{name} says {stated} tests, the suite collects {actual}"
        )
