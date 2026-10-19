"""The hosted check-in tools: tonight's script, the record that it started,
and a coaching note that is built only from the engine's numbers."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from bellwether_server import MemoryStore, build_app
from speech_vitals import FEATURE_NAMES
from speech_vitals.elicitation import host_lines_for

FORBIDDEN = re.compile(r"\b(dementia|alzheimer|diagnos\w*|parkinson|aphasia|will (get|develop)|predict\w*)\b", re.I)


@pytest.fixture()
def client():
    app = build_app(store=MemoryStore(), default_profile="test", seed=False)
    return TestClient(app)


def rpc(c, method, params=None, sid=None, id_=1):
    headers = {"mcp-session-id": sid} if sid else {}
    return c.post("/mcp", json={"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}, headers=headers)


def session(c):
    return rpc(c, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}).headers["mcp-session-id"]


def tool(c, sid, name, args=None):
    res = rpc(c, "tools/call", {"name": name, "arguments": args or {}}, sid=sid).json()
    assert "error" not in res, res
    return json.loads(res["result"]["content"][0]["text"])


def day_row(d: date, words: int, seed: int = 1):
    import random

    rng = random.Random(seed + d.toordinal())
    row = {"date": d.isoformat(), "token_count_day": words}
    for f in FEATURE_NAMES:
        row[f] = round(rng.uniform(0.3, 0.7), 4)
    return row


def test_start_check_in_returns_the_days_exact_script_and_records_the_start(client):
    sid = session(client)
    today = date.today().isoformat()
    out = tool(client, sid, "start_check_in", {"profile_id": "me-voice", "host": "alexa", "date": today})
    assert out["date"] == today
    assert out["host_lines"] == host_lines_for(today)
    assert out["opener"].startswith("Bellwether check-in")
    assert [p["kind"] for p in out["prompts"]] == ["narrative", "description", "procedure"]
    assert out["eligible_days"] == 0 and out["today_counted"] is False
    assert out["already_started_today"] is None
    # A second start the same evening is told about the first.
    again = tool(client, sid, "start_check_in", {"profile_id": "me-voice", "host": "alexa", "date": today})
    assert again["already_started_today"]["host"] == "alexa"


def test_without_a_date_the_service_uses_its_own_utc_day(client):
    from datetime import datetime, timezone

    sid = session(client)
    out = tool(client, sid, "start_check_in", {"profile_id": "me-voice"})
    assert out["date"] == datetime.now(timezone.utc).date().isoformat()
    bad = tool(client, sid, "start_check_in", {"profile_id": "x", "date": "2026-13-40"})
    assert bad["date"] == datetime.now(timezone.utc).date().isoformat()


def test_the_page_can_peek_without_starting(client):
    peek = client.get("/v1/profiles/me-voice/check-in?peek=1").json()
    assert peek["already_started_today"] is None
    again = client.get("/v1/profiles/me-voice/check-in?peek=1").json()
    assert again["already_started_today"] is None
    started = client.get("/v1/profiles/me-voice/check-in?host=test").json()
    assert started["already_started_today"] is None
    assert client.get("/v1/profiles/me-voice/check-in?peek=1").json()["already_started_today"]["host"] == "test"


def test_coaching_counts_the_first_week_and_names_a_short_day(client):
    today = date.today()
    rows = [day_row(today - timedelta(days=k), 260) for k in (3, 2)] + [day_row(today - timedelta(days=1), 90)]
    assert client.post("/v1/profiles/me-voice/days", json=rows).status_code == 200
    sid = session(client)
    note = tool(client, sid, "coaching_note", {"profile_id": "me-voice"})
    assert note["facts"]["eligible_days"] == 2
    assert "Day two of seven counted." in note["text"]
    assert "Five more days" in note["text"]
    assert f"{(today - timedelta(days=1)).isoformat()} came to 90 words" in note["text"]
    assert any("full sentences" in a for a in note["actions"])
    assert not FORBIDDEN.search(note["text"] + " ".join(note["actions"]))


def test_coaching_after_the_week_is_about_what_to_do_not_what_it_means(client):
    today = date.today()
    rows = [day_row(today - timedelta(days=k), 300) for k in range(20, 0, -1)]
    assert client.post("/v1/profiles/me-voice/days", json=rows).status_code == 200
    note = client.get("/v1/profiles/me-voice/coaching").json()
    assert note["facts"]["tier"] in ("stable", "watch", "discuss")
    assert note["actions"], note
    assert "disclaimer" in note
    assert not FORBIDDEN.search(note["text"] + " ".join(note["actions"]))


def test_simulated_profiles_say_so_first():
    store = MemoryStore()
    store.put_meta("alex", "label", "SIMULATED")
    c = TestClient(build_app(store=store, default_profile="test", seed=False))
    note = c.get("/v1/profiles/alex/coaching").json()
    assert note["simulated"] is True
    assert note["text"].startswith("This person is simulated.")


def test_a_drift_note_names_at_most_three_measures_in_plain_words():
    from bellwether_server.checkin import _spoken_list

    names = ["filler_rate", "disfluency_rate", "pronoun_noun_ratio", "low_freq_word_rate", "mattr"]
    assert _spoken_list(names) == "ums and uhs, restarts, pronoun use and two other measures"
    assert _spoken_list(["mattr"]) == "vocabulary variety"
    assert _spoken_list(["mattr", "filler_rate"]) == "vocabulary variety and ums and uhs"
    assert _spoken_list([]) == "several measures"
    assert "_" not in _spoken_list(names)


def test_a_guessed_date_is_ignored_and_does_not_mark_that_day(client):
    """On 2026-10-18 the Strands agent, asked to host, sent 2025-01-17."""
    from datetime import datetime, timezone

    sid = session(client)
    utc = datetime.now(timezone.utc).date()
    out = tool(client, sid, "start_check_in", {"profile_id": "me-voice", "date": "2025-01-17"})
    assert out["date"] == utc.isoformat()
    for k in (-1, 1):
        near = (utc + timedelta(days=k)).isoformat()
        assert tool(client, sid, "start_check_in", {"profile_id": f"p{k}", "date": near})["date"] == near
    far = (utc + timedelta(days=2)).isoformat()
    assert tool(client, sid, "start_check_in", {"profile_id": "p2", "date": far})["date"] == utc.isoformat()


def test_coaching_speaks_about_the_latest_check_in_not_an_old_short_day(client):
    today = date.today()
    rows = [day_row(today - timedelta(days=3), 93), day_row(today - timedelta(days=2), 299), day_row(today, 297)]
    assert client.post("/v1/profiles/me-voice/days", json=rows).status_code == 200
    note = client.get("/v1/profiles/me-voice/coaching").json()
    assert f"The latest check-in, on {today.isoformat()}, counted with 297 words." in note["text"]
    assert "93 words" not in note["text"]
    assert not any("full sentences" in a for a in note["actions"])


def test_the_simulated_first_week_replays_one_evening_at_a_time():
    """Seeded beside the demo, labelled simulated, and viewed as of each
    evening: the short third day does not count, the seventh counted day is
    the eighth evening, and the first comparison is the ninth."""
    c = TestClient(build_app(store=MemoryStore()))
    days = [d["date"] for d in c.get("/v1/profiles/sam-first-week/days").json()["days"]]
    assert len(days) == 10
    seen = []
    for d in days:
        s = c.get(f"/v1/profiles/sam-first-week/summary?as_of={d}").json()
        n = c.get(f"/v1/profiles/sam-first-week/coaching?as_of={d}").json()
        assert s["simulated"] is True and n["text"].startswith("This person is simulated.")
        assert n["date"] == d
        seen.append((s["tier"], s["eligible_days"]))
    assert [e for _, e in seen] == [1, 2, 2, 3, 4, 5, 6, 7, 8, 9]
    assert [t for t, _ in seen][:8] == ["learning"] * 8
    assert seen[8][0] in ("stable", "watch", "discuss")
    third = c.get(f"/v1/profiles/sam-first-week/coaching?as_of={days[2]}").json()
    assert "came to 118 words, under the floor of 150" in third["text"]


def test_as_of_is_validated_and_never_leaks_later_days():
    c = TestClient(build_app(store=MemoryStore()))
    assert c.get("/v1/profiles/sam-first-week/summary?as_of=10/12/2026").status_code == 400
    days = [d["date"] for d in c.get("/v1/profiles/sam-first-week/days").json()["days"]]
    a = c.get(f"/v1/profiles/sam-first-week/assessments?as_of={days[3]}").json()["days"]
    assert max(x["date"] for x in a) == days[3]


def test_the_report_carries_a_section_for_the_annual_wellness_visit():
    """Offered as observation over time, never as a screening result, and
    sourced, so the page has somewhere to go that already exists."""
    c = TestClient(build_app(store=MemoryStore()))
    rep = c.get("/v1/profiles/alex-drift/report").json()
    awv = rep["awv"]
    assert awv["title"] == "For the Annual Wellness Visit"
    assert "not a screening result" in awv["text"]
    assert len(awv["questions"]) == 3
    assert "10.1016/j.jalz.2012.09.011" in awv["source"]
    assert any("10.1186/s13195-023-01272-z" in x["source"] for x in rep["citations"])
    assert not FORBIDDEN.search(awv["text"] + " ".join(awv["questions"]))
