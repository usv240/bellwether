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
        # The per-package counts in the repository table have their own
        # test below. An earlier version of this comment said they were
        # deliberately left unchecked because sweeping them in would make
        # this test unreadable, and by the time anyone looked again the
        # table summed to 145 beside a headline of 177. "Unreadable" was
        # the wrong tradeoff against a table that contradicts itself.
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


# --------------------------------------------------------------------------
# The two judged deliverables whose size is quoted in prose.
#
# The submission said "Six entries" while FRICTION_LOG.md had nine, and the
# three it left out were entries 7, 8 and 9: two written against ourselves
# and one recording that this server was already correct on the transport
# shape that broke the other two projects. All three sibling projects had
# this same drift found on the same day, all three undercounting, and all
# three omitting the entries least flattering to themselves.
#
# The friction log is worth up to a ten percent judging bonus, so the count
# is a claim like any other and is derived here rather than remembered.
# --------------------------------------------------------------------------

WORDS = {
    3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
    9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
}


def _spelled(actual: int, label: str) -> str:
    word = WORDS.get(actual)
    assert word, f"no spelling for {actual} {label}; add it to WORDS"
    return word


def test_the_friction_log_count_is_the_number_of_entries() -> None:
    log = (REPO / "FRICTION_LOG.md").read_text(encoding="utf8")
    actual = len(re.findall(r"^## Entry \d+:", log, re.M))
    assert actual > 0, "FRICTION_LOG.md has no entries"
    word = _spelled(actual, "friction log entries")
    for name in PUBLIC_TEXT:
        text = (REPO / name).read_text(encoding="utf8")
        # Key on the filename, not on the prose around it. The first
        # version of this matched "entries with task, steps" and then the
        # sentence was reworded to link the file, so the pattern stopped
        # matching and the test passed by finding nothing. A guard that
        # goes quiet when the text it guards changes is worse than none.
        m = re.search(r"(\w+) entries in \[?FRICTION_LOG", text)
        if m:
            assert m.group(1).lower() == word, (
                f"{name} says {m.group(1)!r} friction entries, "
                f"FRICTION_LOG.md has {actual}"
            )


def test_the_feature_request_count_is_the_number_of_requests() -> None:
    """Numbered `### n.` headings, including the one numbered 5b.

    The list runs 1 to 8 but carries a 5b, which is a real request with
    its own reasoning and its own severity, so there are nine of them.
    Quoting the highest number rather than counting the headings is how
    the ninth went unmentioned.
    """
    reqs = (REPO / "docs/FEATURE_REQUESTS.md").read_text(encoding="utf8")
    actual = len(re.findall(r"^### \d+[a-z]?\. ", reqs, re.M))
    assert actual > 0, "FEATURE_REQUESTS.md has no numbered requests"
    word = _spelled(actual, "feature requests")
    for name in PUBLIC_TEXT:
        text = (REPO / name).read_text(encoding="utf8")
        m = re.search(r"(\w+), each from something we actually hit", text)
        if m:
            assert m.group(1).lower() == word, (
                f"{name} says {m.group(1)!r} feature requests, "
                f"FEATURE_REQUESTS.md has {actual}"
            )


def _collected(target: str) -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", target],
        cwd=REPO, capture_output=True, text=True,
    )
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    if not m:
        pytest.skip(f"could not collect {target}: {proc.stdout[-200:]}")
    return int(m.group(1))


def test_the_readme_table_agrees_with_each_package() -> None:
    """Every row of the repository table, against its own directory.

    These drifted furthest of anything in the project, because nothing
    read them: apps/ingest said 30 against 43 and apps/server said 18
    against 33, so the table summed to 145 under a headline claiming
    177. Each row is small and looks harmless, which is exactly why the
    total of the errors got large without anyone noticing.
    """
    readme = (REPO / "README.md").read_text(encoding="utf8")
    rows = re.findall(r"^\| \[`([^`]+)`\].*\| (\d+) \|\s*$", readme, re.M)
    assert rows, "no per-package rows found in the README table"
    stated = {pkg: int(n) for pkg, n in rows if pkg in TARGETS}
    assert set(stated) == set(TARGETS), (
        f"README table covers {sorted(stated)}, the suite runs {sorted(TARGETS)}"
    )
    for pkg, n in sorted(stated.items()):
        actual = _collected(pkg)
        assert n == actual, f"README says {pkg} has {n} tests, it collects {actual}"


def test_the_table_sums_to_the_published_total() -> None:
    """The two figures in the same README must agree with each other.

    This is the cheap check that would have caught the drift with no
    subprocess at all: 25 + 63 + 30 + 18 + 9 is 145, and the sentence
    directly beneath said 177.
    """
    readme = (REPO / "README.md").read_text(encoding="utf8")
    rows = re.findall(r"^\| \[`([^`]+)`\].*\| (\d+) \|\s*$", readme, re.M)
    table = sum(int(n) for pkg, n in rows if pkg in TARGETS)
    m = re.search(r"\*\*(\d+) tests[.,;:]?\*\*", readme)
    assert m, "README states no headline test total"
    assert table == int(m.group(1)), (
        f"the README table sums to {table} but its headline says {m.group(1)}"
    )
