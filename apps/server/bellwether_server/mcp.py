"""MCP server for Bellwether: Model Context Protocol spec revision
2025-11-25 over the Streamable HTTP transport. The Alexa+ surface.

A faithful port of the transport that already runs in Nightlight and
EveryWord, including the lesson both of them paid for: a real client
terminates a session with DELETE carrying a JSON content-type and an empty
body, which a naive body parser answers with a 500. Here DELETE never reads
a body.

Why an agent surface belongs on this product: the question a person or a
family actually asks is spoken and casual ("how have I been sounding
lately?", "is it worth mentioning to the doctor?"), and the answer needs
several dependent reads (status, then trend, then the days behind it) and
a judgement about whether to say anything. That is an agent's job. The
agent gets exactly the seven tools below and nothing else: no transcripts,
because none exist to give.

Transport behaviour, per the spec:
  POST /mcp    JSON-RPC 2.0 requests and notifications, answered as JSON
  GET  /mcp    405 with an Allow header (no server-initiated stream)
  DELETE /mcp  terminates the session (204), unknown session 404
  MCP-Session-Id issued on initialize and required after: missing 400,
  unknown or terminated 404. MCP-Protocol-Version validated when present.
  Origin, when present, must be loopback or an allowed site origin
  (DNS-rebinding guidance).
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from bellwether_engine import assess, summarize
from speech_vitals import FEATURE_NAMES, FEATURES

from .store import Store

SITE_ORIGIN = "https://d1xfuyog8wiuvf.cloudfront.net"

_LOOPBACK = re.compile(r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$")


def is_allowed_origin(origin: str) -> bool:
    """Loopback, this product's own site, or anything named in the env.

    The spec's DNS-rebinding guidance says to validate Origin, and the
    first reading of that produced a loopback-only check. That is correct
    for a server nothing but a local client talks to, and wrong the moment
    the product's own website holds a session: the deployed server
    answered its own front page with 403.

    Both sibling projects hit this and fixed it. This one did not, because
    until the Alexa+ panel existed nothing here had ever called the server
    from a browser, so every test and every curl agreed it was fine. A
    rule that only wrong callers could trip looks identical to a correct
    rule until a right caller turns up.

    BELLWETHER_ALLOWED_ORIGINS is a comma-separated list, for a fork
    deployed somewhere else.
    """
    if _LOOPBACK.match(origin):
        return True
    named = {
        o.strip().rstrip("/")
        for o in [SITE_ORIGIN, *os.environ.get("BELLWETHER_ALLOWED_ORIGINS", "").split(",")]
        if o.strip()
    }
    return origin.rstrip("/") in named


MCP_PROTOCOL_VERSION = "2025-11-25"
FALLBACK_PROTOCOL_VERSION = "2025-03-26"
SERVER_INFO = {"name": "bellwether-mcp", "version": "0.1.0"}

DISCLAIMER = (
    "This is not a diagnosis; it is a record of change over time in one person "
    "against their own baseline. Changes in speech have many everyday causes, "
    "including sleep, stress, medication and mood. Share it with a clinician you trust."
)

INSTRUCTIONS = (
    "Bellwether keeps a personal baseline of how one person normally speaks, from "
    "language features only (never words), and reports when that changes. Ask for "
    "the current status, a trend over recent weeks, the days behind it, or a one-page "
    "report for a doctor's visit. You may run the spoken check with a person and log "
    "the result. Report only numbers these tools return. Never diagnose, never predict, "
    "never give medical advice; suggest only what the person can act on themselves, "
    "such as adding a note about sleep or travel, or raising the report with their clinician."
)

# The spoken check: an active layer usable when the passive one flags drift.
# Every prompt is a short spoken line so an agent can administer it.
CHECK_SCRIPT = {
    "animal_fluency": {
        "plain": "Name as many different animals as you can in sixty seconds.",
        "steps": [
            "Say: In a moment I will start a sixty second timer. When I say go, name as many different animals as you can. Any animal counts. Ready?",
            "Say: Go. Start the timer.",
            "Count each distinct animal named once. Do not count repeats or non-animals.",
            "At sixty seconds say: Stop. Thank you.",
            "Log the count with log_check_result, kind animal_fluency.",
        ],
        "basis": "Category (semantic) fluency, the animal naming task. A widely used brief screen; in the literature a cutoff below 15 in sixty seconds has shown high sensitivity and specificity for dementia in older adults (Canning et al. 2004, Neurology 62(4)). Bellwether displays the score and never a judgement beyond the tier language.",
        "duration_seconds": 60,
    },
    "sentence_repetition": {
        "plain": "Repeat three sentences exactly as you hear them.",
        "sentences": [
            "The quiet river ran behind the old stone mill.",
            "She bought fresh bread and two green apples on Tuesday.",
            "If it rains tomorrow, we will visit the museum instead.",
        ],
        "steps": [
            "Say: I will read a sentence. Please say it back to me exactly.",
            "Read one sentence, wait, and note what is said back.",
            "Repeat for all three sentences.",
            "Score each from 0 to 2: 2 exact, 1 close with one change, 0 otherwise. Sum to a score out of 6.",
            "Log the total with log_check_result, kind sentence_repetition.",
        ],
        "basis": "Sentence repetition draws on working memory and syntax and is part of several brief cognitive batteries. Scored here for change over time, not against a population cutoff.",
    },
}

TOOLS = [
    {
        "name": "get_speech_vitals",
        "description": "Current status for a person: the tier (learning, stable, watch, discuss), since when, how many days of baseline, and which features are driving any change. The right first call. Data is labelled simulated where it is.",
        "inputSchema": {
            "type": "object",
            "properties": {"profile_id": {"type": "string", "description": "Which person; omit for the default profile"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_trend",
        "description": "Day by day over recent weeks: the tier, the composite change score, and the features most out of range each day. Low-exposure days are marked excluded rather than misread.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string"},
                "weeks": {"type": "integer", "minimum": 1, "maximum": 12, "description": "How many weeks back (default 4)"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "list_days",
        "description": "The raw day feature rows behind everything: nine language features and the word count, per day. There are no transcripts; these numbers are all that is stored.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 90, "description": "Most recent days to return (default 14)"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "add_annotation",
        "description": "Attach a note to a day, such as travel, illness, poor sleep or a new medication. Annotations appear beside the day in every view so a change can be read in context, and they never alter the numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string"},
                "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                "note": {"type": "string", "minLength": 1, "maxLength": 200},
            },
            "required": ["date", "note"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_check_instructions",
        "description": "The spoken check, as short lines an agent can read aloud: sixty seconds of animal naming, then three sentences to repeat. Use it when the tier is watch or discuss, or when the person asks. Returns the script and how to score it; log the result with log_check_result.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "log_check_result",
        "description": "Record a spoken check result on the timeline. The score is displayed alongside the passive trend and never turned into a judgement beyond the tier language.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string"},
                "kind": {"type": "string", "enum": ["animal_fluency", "sentence_repetition"]},
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
                "detail": {"type": "string", "maxLength": 300},
            },
            "required": ["kind", "score"],
            "additionalProperties": False,
        },
    },
    {
        "name": "generate_doctor_report",
        "description": "A one-page report for a clinical appointment: the date range, the tier history, notable changes with dates and the features behind them, spoken check results, annotations, the non-diagnostic statement, and the citations. Designed for a twelve-minute appointment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string"},
                "weeks": {"type": "integer", "minimum": 1, "maximum": 12, "description": "Weeks to cover (default 8)"},
            },
            "additionalProperties": False,
        },
    },
]

_DIRECTION_WORD = {"lower_is_concerning": "lower", "higher_is_concerning": "higher"}
_SPEC_BY_NAME = {f.name: f for f in FEATURES}


def _text(payload) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=1)}]}


def _result(id_, result) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


class ToolError(Exception):
    def __init__(self, message: str, code: int = -32602) -> None:
        super().__init__(message)
        self.code = code


def profile_view(store: Store, profile_id: str) -> dict:
    """Everything derived for one profile, computed from the stored day
    rows on every call. Nothing here is cached or stored."""
    days = store.list_days(profile_id)
    annotations = store.list_annotations(profile_id)
    assessments = assess(days, annotations=annotations)
    summary = summarize(assessments)
    return {
        "profile_id": profile_id,
        "simulated": (store.get_meta(profile_id, "label") or "").upper() == "SIMULATED",
        "days": days,
        "assessments": assessments,
        "summary": summary,
        "annotations": annotations,
        "checks": store.list_checks(profile_id),
    }


def build_report(view: dict, weeks: int = 8) -> dict:
    """The doctor report as data. The web app renders it to a page and a
    PDF; the agent can read it aloud. Same content either way."""
    cutoff_n = weeks * 7
    assessments = view["assessments"][-cutoff_n:]
    eligible = [a for a in assessments if a.eligible]
    if not assessments:
        return {"available": False, "message": "No days recorded yet.", "disclaimer": DISCLAIMER}

    tier_runs: list[dict] = []
    for a in assessments:
        if tier_runs and tier_runs[-1]["tier"] == a.tier:
            tier_runs[-1]["to"] = a.date
            tier_runs[-1]["days"] += 1
        else:
            tier_runs.append({"tier": a.tier, "from": a.date, "to": a.date, "days": 1})

    # Notable changes: the first day of each watch or discuss run, with the
    # features behind it and their direction.
    notable = []
    for run in tier_runs:
        if run["tier"] in ("watch", "discuss"):
            first = next(a for a in assessments if a.date == run["from"])
            notable.append(
                {
                    "date": run["from"],
                    "tier": run["tier"],
                    "days": run["days"],
                    "features": [
                        {
                            "feature": name,
                            "plain": _SPEC_BY_NAME[name].plain,
                            "direction": _DIRECTION_WORD[_SPEC_BY_NAME[name].direction],
                        }
                        for name in first.contributors
                    ],
                    "explanation": list(first.explanation),
                }
            )

    # The two features that moved most over the window, by mean concern z.
    movement: dict[str, list[float]] = {n: [] for n in FEATURE_NAMES}
    for a in eligible:
        for f in a.features:
            if f.concern_z is not None:
                movement[f.name].append(f.concern_z)
    moved = sorted(
        ((sum(v) / len(v), n) for n, v in movement.items() if v), reverse=True
    )[:2]

    return {
        "available": True,
        "simulated": view["simulated"],
        "profile_id": view["profile_id"],
        "range": {"from": assessments[0].date, "to": assessments[-1].date, "weeks": weeks},
        "current": view["summary"].to_dict(),
        "tier_history": tier_runs,
        "notable_changes": notable,
        "most_moved_features": [
            {"feature": n, "plain": _SPEC_BY_NAME[n].plain, "mean_concern_z": round(z, 2)}
            for z, n in moved
        ],
        "spoken_checks": [c for c in view["checks"] if c.get("at", "") >= assessments[0].date],
        "annotations": {d: n for d, n in view["annotations"].items() if assessments[0].date <= d <= assessments[-1].date},
        "eligible_days": len(eligible),
        "excluded_days": len(assessments) - len(eligible),
        "disclaimer": DISCLAIMER,
        "method": "Nine language features per day from everyday speech, compared with this person's own baseline. No transcript is stored. Full method and citations: docs/METHODS.md in the repository.",
        "citations": [
            {"claim": "Time from symptom onset to dementia diagnosis averages 3.5 years", "source": "Orgeta et al., Int J Geriatr Psychiatry, 2025, doi:10.1002/gps.70129"},
            {"claim": "40 to 80 percent of medical information is forgotten immediately", "source": "Kessels, J R Soc Med, 2003, 96:219-222"},
            {"claim": "Language features from spontaneous speech separate Alzheimer's from control speech at 85 to 89.6 percent on the ADReSS benchmark", "source": "Luz et al., Interspeech 2020, doi:10.21437/Interspeech.2020-2571"},
        ],
    }


def register_mcp(app: FastAPI, store: Store, default_profile: str) -> None:
    sessions: set[str] = set()

    def resolve_profile(args: dict) -> str:
        pid = args.get("profile_id")
        return str(pid) if isinstance(pid, str) and pid.strip() else default_profile

    def call_tool(name: str, args: dict) -> dict:
        if name == "get_speech_vitals":
            view = profile_view(store, resolve_profile(args))
            s = view["summary"].to_dict()
            return _text(
                {
                    "profile_id": view["profile_id"],
                    "simulated": view["simulated"],
                    **s,
                    "note": "Tiers describe change against this person's own baseline. Not a diagnosis.",
                }
            )

        if name == "get_trend":
            view = profile_view(store, resolve_profile(args))
            weeks = args.get("weeks") if isinstance(args.get("weeks"), int) else 4
            weeks = max(1, min(12, weeks))
            rows = []
            for a in view["assessments"][-weeks * 7 :]:
                top = sorted(
                    (f for f in a.features if f.concern_z is not None),
                    key=lambda f: -f.concern_z,
                )[:2]
                rows.append(
                    {
                        "date": a.date,
                        "tier": a.tier,
                        "composite": a.composite,
                        "top": [{"feature": f.name, "concern_z": f.concern_z} for f in top],
                        "annotation": a.annotation,
                    }
                )
            return _text({"profile_id": view["profile_id"], "simulated": view["simulated"], "weeks": weeks, "days": rows})

        if name == "list_days":
            view = profile_view(store, resolve_profile(args))
            limit = args.get("limit") if isinstance(args.get("limit"), int) else 14
            limit = max(1, min(90, limit))
            return _text(
                {
                    "profile_id": view["profile_id"],
                    "simulated": view["simulated"],
                    "days": view["days"][-limit:],
                    "note": "These numbers are everything that is stored. No transcript exists.",
                }
            )

        if name == "add_annotation":
            pid = resolve_profile(args)
            date = args.get("date")
            note = args.get("note")
            if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                raise ToolError("date must be YYYY-MM-DD")
            if not isinstance(note, str) or not note.strip() or len(note) > 200:
                raise ToolError("note is required, at most 200 characters")
            store.put_annotation(pid, date, note.strip())
            return _text({"recorded": True, "profile_id": pid, "date": date, "note": note.strip()})

        if name == "run_check_instructions":
            return _text({"checks": CHECK_SCRIPT, "then": "Log each result with log_check_result."})

        if name == "log_check_result":
            pid = resolve_profile(args)
            kind = args.get("kind")
            score = args.get("score")
            if kind not in CHECK_SCRIPT:
                raise ToolError("kind must be animal_fluency or sentence_repetition")
            if not isinstance(score, int) or score < 0 or score > 100:
                raise ToolError("score must be an integer from 0 to 100")
            check = {
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "kind": kind,
                "score": score,
                "detail": (args.get("detail") or "")[:300],
            }
            store.put_check(pid, check)
            return _text({"recorded": True, "profile_id": pid, **check})

        if name == "generate_doctor_report":
            view = profile_view(store, resolve_profile(args))
            weeks = args.get("weeks") if isinstance(args.get("weeks"), int) else 8
            return _text(build_report(view, max(1, min(12, weeks))))

        raise ToolError(f"Unknown tool: {name}")

    @app.post("/mcp")
    async def mcp_post(request: Request):
        origin = request.headers.get("origin")
        if origin and not is_allowed_origin(origin):
            return JSONResponse(_error(None, -32600, "Origin not allowed"), status_code=403)

        raw = await request.body()
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return JSONResponse(_error(None, -32700, "Parse error"), status_code=400)
        if isinstance(body, list):
            return JSONResponse(_error(None, -32600, "Batching is not part of this protocol revision"), status_code=400)
        if not isinstance(body, dict) or body.get("jsonrpc") != "2.0" or not isinstance(body.get("method"), str):
            return JSONResponse(_error(None, -32600, "Invalid JSON-RPC request"), status_code=400)

        msg_id = body.get("id")
        method = body["method"]
        session_id = request.headers.get("mcp-session-id")
        version = request.headers.get("mcp-protocol-version")
        if version is not None and version not in (MCP_PROTOCOL_VERSION, FALLBACK_PROTOCOL_VERSION):
            return JSONResponse(_error(msg_id, -32600, f"Unsupported protocol version: {version}"), status_code=400)

        if method == "initialize":
            new_session = str(uuid.uuid4())
            sessions.add(new_session)
            return JSONResponse(
                _result(
                    msg_id,
                    {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": SERVER_INFO,
                        "instructions": INSTRUCTIONS,
                    },
                ),
                headers={"MCP-Session-Id": new_session},
            )

        if not session_id:
            return JSONResponse(_error(msg_id, -32600, "Missing MCP-Session-Id header"), status_code=400)
        if session_id not in sessions:
            return JSONResponse(_error(msg_id, -32001, "Unknown or terminated session"), status_code=404)

        if msg_id is None:
            return Response(status_code=202)

        if method == "ping":
            return JSONResponse(_result(msg_id, {}))
        if method == "tools/list":
            return JSONResponse(_result(msg_id, {"tools": TOOLS}))
        if method == "tools/call":
            params = body.get("params") or {}
            name = params.get("name") if isinstance(params.get("name"), str) else ""
            args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            try:
                return JSONResponse(_result(msg_id, call_tool(name, args)))
            except ToolError as err:
                return JSONResponse(_error(msg_id, err.code, str(err)))
            except Exception as err:  # noqa: BLE001
                return JSONResponse(_error(msg_id, -32603, str(err)))
        return JSONResponse(_error(msg_id, -32601, f"Method not found: {method}"))

    @app.get("/mcp")
    async def mcp_get():
        return Response(status_code=405, headers={"Allow": "POST, DELETE"})

    @app.delete("/mcp")
    async def mcp_delete(request: Request):
        # Never reads a body: a real client sends one, empty, with a JSON
        # content-type, and parsing it is how both sibling projects got a 500.
        session_id = request.headers.get("mcp-session-id")
        if session_id and session_id in sessions:
            sessions.discard(session_id)
            return Response(status_code=204)
        return Response(status_code=404)
