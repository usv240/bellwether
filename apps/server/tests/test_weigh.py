"""Both sides of a change: computed, cited by id, never a verdict."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from bellwether_server import MemoryStore, build_app

FORBIDDEN = re.compile(r"\b(dementia|alzheimer|diagnos\w*|parkinson|aphasia|predict\w*|disease)\b", re.I)


def client():
    return TestClient(build_app(store=MemoryStore()))


def test_a_flagged_change_has_evidence_on_both_sides_with_ids():
    w = client().get("/v1/profiles/alex-drift/weigh").json()
    assert w["tier"] in ("watch", "discuss") and w["simulated"] is True
    assert [e["id"] for e in w["change"]][:2] == ["C1", "C2"]
    assert [e["id"] for e in w["ordinary"]][0] == "O1"
    text = " ".join(e["claim"] for e in w["change"] + w["ordinary"])
    assert not FORBIDDEN.search(text)
    assert "does not say which is right" in w["note"]


def test_the_persons_own_note_is_weighed_by_its_distance_from_the_change():
    w = client().get("/v1/profiles/alex-drift/weigh").json()
    o1 = w["ordinary"][0]["claim"]
    assert "2026-08-16" in o1 and "days before it began" in o1


def test_a_stable_profile_has_nothing_to_weigh():
    w = client().get("/v1/profiles/sam-first-week/weigh").json()
    assert w["change"] == [] and w["ordinary"] == []
    assert "Nothing to weigh" in w["note"]


def test_as_of_weighs_the_change_as_it_stood_then():
    c = client()
    early = c.get("/v1/profiles/alex-drift/weigh?as_of=2026-09-05").json()
    late = c.get("/v1/profiles/alex-drift/weigh").json()
    assert early["change"][0]["claim"] != late["change"][0]["claim"]
