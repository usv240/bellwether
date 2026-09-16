"""Service tests: MCP transport conformance (spec 2025-11-25), the seven
tools, the public API, the Bedrock ladder, and the privacy guarantee at
the door.

Self-contained: a synthetic profile is posted through the public API rather
than read from fixture files, so the suite proves the API stores what the
engine reads, and runs anywhere.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from bellwether_server import MCP_PROTOCOL_VERSION, MemoryStore, build_app
from speech_vitals import FEATURE_NAMES

PROFILE = {
    "mattr": (0.72, 0.02), "mean_utt_len": (9.0, 0.8), "dep_depth_mean": (3.2, 0.25),
    "pronoun_noun_ratio": (0.35, 0.03), "filler_rate": (2.0, 0.4), "disfluency_rate": (1.0, 0.3),
    "low_freq_word_rate": (6.0, 0.8), "idea_density": (4.5, 0.3), "vocab_size_day": (320.0, 25.0),
}
DRIFT = {"mattr": -1, "mean_utt_len": -1, "pronoun_noun_ratio": +1, "idea_density": -1, "low_freq_word_rate": -1}
START = date(2026, 3, 1)


def synthetic_days(n=40, seed=3, drift_from=25):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        row = {"date": (START + timedelta(days=i)).isoformat(), "utterances": 40, "token_count_day": 1800}
        for name in FEATURE_NAMES:
            mean, sd = PROFILE[name]
            v = rng.gauss(mean, sd)
            if drift_from is not None and i >= drift_from and name in DRIFT:
                v += DRIFT[name] * 2.5 * sd
            row[name] = v
        out.append(row)
    return out


@pytest.fixture()
def client():
    app = build_app(store=MemoryStore(), default_profile="test", seed=False)
    c = TestClient(app)
    r = c.post("/v1/profiles/test/days", json=synthetic_days())
    assert r.status_code == 200, r.text
    return c


def rpc(c, method, params=None, sid=None, id_=1, headers=None):
    body = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        body["params"] = params
    h = {"content-type": "application/json"}
    if sid:
        h["mcp-session-id"] = sid
    if headers:
        h.update(headers)
    return c.post("/mcp", json=body, headers=h)


def session(c) -> str:
    r = rpc(c, "initialize", {"protocolVersion": MCP_PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    assert r.status_code == 200
    return r.headers["mcp-session-id"]


def call(c, sid, name, args=None):
    r = rpc(c, "tools/call", {"name": name, "arguments": args or {}}, sid, id_=9)
    body = r.json()
    if "error" in body:
        return {"error": body["error"]}
    import json as _json
    return _json.loads(body["result"]["content"][0]["text"])


# ---- transport -------------------------------------------------------------


def test_initialize_issues_session_and_protocol(client):
    r = rpc(client, "initialize", {"protocolVersion": MCP_PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    assert r.status_code == 200
    assert r.json()["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION
    assert r.json()["result"]["serverInfo"]["name"] == "bellwether-mcp"
    assert len(r.headers["mcp-session-id"]) == 36


def test_missing_unknown_and_bad_version(client):
    assert rpc(client, "tools/list").status_code == 400
    assert rpc(client, "tools/list", sid="00000000-0000-0000-0000-000000000000").status_code == 404
    sid = session(client)
    assert rpc(client, "tools/list", sid=sid, headers={"mcp-protocol-version": "1999-01-01"}).status_code == 400
    assert rpc(client, "tools/list", sid=sid, headers={"mcp-protocol-version": MCP_PROTOCOL_VERSION}).status_code == 200


def test_origin_notifications_and_batches(client):
    sid = session(client)
    assert rpc(client, "tools/list", sid=sid, headers={"origin": "https://evil.example.com"}).status_code == 403
    assert rpc(client, "tools/list", sid=sid, headers={"origin": "http://localhost:3000"}).status_code == 200
    r = client.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers={"mcp-session-id": sid})
    assert r.status_code == 202 and r.content == b""
    r = client.post("/mcp", json=[{"jsonrpc": "2.0", "id": 1, "method": "ping"}], headers={"mcp-session-id": sid})
    assert r.status_code == 400


def test_get_405_and_delete_lifecycle(client):
    r = client.get("/mcp")
    assert r.status_code == 405 and "POST" in r.headers["allow"]
    sid = session(client)
    # A real client sends DELETE with a JSON content-type and an empty body.
    r = client.delete("/mcp", headers={"mcp-session-id": sid, "content-type": "application/json"})
    assert r.status_code == 204
    assert rpc(client, "tools/list", sid=sid).status_code == 404
    assert client.delete("/mcp", headers={"mcp-session-id": sid}).status_code == 404


def test_unknown_tool_and_method(client):
    sid = session(client)
    assert call(client, sid, "does_not_exist")["error"]["code"] == -32602
    assert rpc(client, "resources/list", sid=sid).json()["error"]["code"] == -32601


# ---- tools -----------------------------------------------------------------


def test_lists_seven_tools(client):
    sid = session(client)
    names = sorted(t["name"] for t in rpc(client, "tools/list", sid=sid).json()["result"]["tools"])
    assert names == sorted(["get_speech_vitals", "get_trend", "list_days", "add_annotation", "run_check_instructions", "log_check_result", "generate_doctor_report"])


def test_speech_vitals_reports_the_drift_with_contributors(client):
    sid = session(client)
    out = call(client, sid, "get_speech_vitals")
    assert out["profile_id"] == "test" and out["simulated"] is False
    assert out["tier"] in ("watch", "discuss")
    assert len(out["contributors"]) >= 2
    assert "Not a diagnosis" in out["note"]


def test_trend_and_days(client):
    sid = session(client)
    trend = call(client, sid, "get_trend", {"weeks": 2})
    assert len(trend["days"]) == 14 and all("tier" in d for d in trend["days"])
    days = call(client, sid, "list_days", {"limit": 5})
    assert len(days["days"]) == 5
    assert set(FEATURE_NAMES) <= set(days["days"][0])


def test_annotation_appears_in_trend(client):
    sid = session(client)
    d = (START + timedelta(days=30)).isoformat()
    assert call(client, sid, "add_annotation", {"date": d, "note": "travel, slept badly"})["recorded"] is True
    trend = call(client, sid, "get_trend", {"weeks": 4})
    assert next(x for x in trend["days"] if x["date"] == d)["annotation"] == "travel, slept badly"
    assert call(client, sid, "add_annotation", {"date": "bad", "note": "x"})["error"]["code"] == -32602


def test_spoken_check_script_and_logging(client):
    sid = session(client)
    script = call(client, sid, "run_check_instructions")["checks"]
    assert set(script) == {"animal_fluency", "sentence_repetition"}
    assert script["animal_fluency"]["duration_seconds"] == 60
    assert len(script["sentence_repetition"]["sentences"]) == 3
    assert call(client, sid, "log_check_result", {"kind": "animal_fluency", "score": 18})["recorded"] is True
    assert call(client, sid, "log_check_result", {"kind": "nope", "score": 1})["error"]["code"] == -32602


def test_doctor_report_structure(client):
    sid = session(client)
    call(client, sid, "log_check_result", {"kind": "animal_fluency", "score": 17})
    rep = call(client, sid, "generate_doctor_report", {"weeks": 6})
    assert rep["available"] is True
    assert rep["range"]["weeks"] == 6
    assert rep["tier_history"][0]["tier"] == "learning"
    assert any(n["tier"] in ("watch", "discuss") for n in rep["notable_changes"])
    assert len(rep["citations"]) == 3
    assert "not a diagnosis" in rep["disclaimer"].lower()
    assert rep["spoken_checks"][0]["score"] == 17


# ---- public API ------------------------------------------------------------


def test_post_days_validates_and_drops_text_at_the_door():
    c = TestClient(build_app(store=MemoryStore(), default_profile="p", seed=False))
    assert c.post("/v1/profiles/p/days", json=[{"date": "2026-01-01"}]).status_code == 400
    row = synthetic_days(1)[0]
    row["transcript"] = "a secret sentence"
    r = c.post("/v1/profiles/p/days", json=[row])
    assert r.status_code == 200 and r.json()["stored"] == 1
    stored = c.get("/v1/profiles/p/days").json()["days"][0]
    assert "transcript" not in stored
    assert "secret" not in str(stored)


def test_summary_assessments_report_and_schema(client):
    s = client.get("/v1/profiles/test/summary").json()
    assert s["tier"] in ("watch", "discuss") and "disclaimer" in s
    a = client.get("/v1/profiles/test/assessments", params={"weeks": 1}).json()
    assert len(a["days"]) == 7
    assert client.get("/v1/profiles/test/report").json()["available"] is True
    sch = client.get("/v1/schema").json()
    assert {f["name"] for f in sch["features"]} == set(FEATURE_NAMES)
    assert client.get("/healthz").json()["ok"] is True


def test_resilience_report(client):
    r = client.get("/api/resilience").json()
    assert r["detection"]["usesModels"] is False
    assert len(r["weeklyNote"]["modelLadder"]) == 3
    assert r["privacy"]["textStored"] is False
    assert r["store"]["kind"] == "MemoryStore"


def test_reset_is_demo_only(client):
    assert client.post("/v1/profiles/test/reset").status_code == 200
    assert client.post("/v1/profiles/other/reset").status_code == 403


# ---- the weekly note ladder ------------------------------------------------


def _client_with_note(create_text, models):
    app = build_app(store=MemoryStore(), default_profile="t", seed=False, note_deps={"create_text": create_text, "models": models, "enabled": True})
    c = TestClient(app)
    c.post("/v1/profiles/t/days", json=synthetic_days())
    return c


def test_weekly_note_descends_the_ladder_and_reports_provenance():
    def create(_s, _u, model):
        if model == "gated":
            raise RuntimeError("AccessDeniedException")
        return "This week your speech moved outside your usual range. A note about sleep would help read it. Bring the report to your clinician."
    c = _client_with_note(create, ["gated", "ok"])
    note = c.get("/v1/profiles/t/weekly-note").json()
    assert note["source"] == "bedrock" and note["model"] == "ok"
    assert note["attempts"][0] == {"model": "gated", "ok": False, "reason": "AccessDeniedException"}
    assert "facts_text" in note and "Current tier" in note["facts_text"]


def test_weekly_note_falls_to_template_when_every_model_fails():
    def create(*_):
        raise RuntimeError("region unavailable")
    c = _client_with_note(create, ["a", "b"])
    note = c.get("/v1/profiles/t/weekly-note").json()
    assert note["source"] == "template" and note["model"] is None
    assert len(note["attempts"]) == 2
    assert "not a diagnosis" in note["text"].lower()


def test_rambling_answer_fails_the_rung_not_the_ladder():
    def create(_s, _u, model):
        return "x" * 700 if model == "chatty" else "A quiet week, within your normal range."
    c = _client_with_note(create, ["chatty", "concise"])
    note = c.get("/v1/profiles/t/weekly-note").json()
    assert note["model"] == "concise"
    assert note["attempts"][0]["reason"] == "response too long"
