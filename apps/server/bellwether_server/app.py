"""The Bellwether service.

Routes:
  GET  /healthz                              liveness
  GET  /api/resilience                       every degradation path, reported
  GET  /v1/schema                            the feature registry with its literature basis
  GET  /v1/profiles/{id}/summary             current tier, since when, why
  GET  /v1/profiles/{id}/assessments?weeks=  day by day, derived on read
  GET  /v1/profiles/{id}/days                the stored feature rows (all that is stored)
  POST /v1/profiles/{id}/days                feature rows in (the public API and the ingest target)
  POST /v1/profiles/{id}/annotations         {date, note}
  POST /v1/profiles/{id}/checks              {kind, score, detail?}
  GET  /v1/profiles/{id}/report?weeks=       the doctor report as data
  GET  /v1/profiles/{id}/weekly-note         Bedrock-phrased, with provenance
  POST /v1/profiles/{id}/reset               re-seed the demo profile only
  /mcp                                       Model Context Protocol 2025-11-25

The public API accepts feature rows, not text. Anyone can run the
open-source speech-vitals package on their own machine and post the
numbers; the transcript never leaves it. That is a stance, not a limit.

The demo profile is the simulated drift persona from fixtures/personas,
labelled SIMULATED in every response that touches it.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from speech_vitals import FEATURE_NAMES, features_schema

from .bedrock import MODEL_LADDER, phrase_weekly_note
from .mcp import DISCLAIMER, build_report, profile_view, register_mcp
from .store import MemoryStore, Store

DEMO_PROFILE = "alex-drift"
REQUIRED_DAY_FIELDS = ("date", "token_count_day", *FEATURE_NAMES)


def _fixtures_dir() -> Path | None:
    env = os.environ.get("BELLWETHER_FIXTURES")
    candidates = [Path(env)] if env else []
    candidates.append(Path(__file__).resolve().parents[3] / "fixtures" / "personas")
    candidates.append(Path(__file__).resolve().parent / "demo")
    for c in candidates:
        if (c / DEMO_PROFILE / "days.json").exists():
            return c
    return None


def seed_demo(store: Store, profile: str = DEMO_PROFILE) -> int:
    """Load the simulated persona if the store has nothing for it. Returns
    the number of days seeded (0 if already present or fixtures missing)."""
    if store.list_days(profile):
        return 0
    base = _fixtures_dir()
    if base is None:
        return 0
    pdir = base / profile
    # The directory check above is for the demo persona; this profile may
    # have no fixture at all, and resetting it must not crash.
    if not (pdir / "days.json").exists():
        return 0
    days = json.loads((pdir / "days.json").read_text(encoding="utf-8"))
    for d in days:
        store.put_day(profile, d)
    meta_path = pdir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for date, note in (meta.get("annotations") or {}).items():
            store.put_annotation(profile, date, note)
    store.put_meta(profile, "label", "SIMULATED")
    return len(days)


def validate_day(row) -> dict:
    if not isinstance(row, dict):
        raise HTTPException(400, "each day must be an object")
    missing = [k for k in REQUIRED_DAY_FIELDS if k not in row]
    if missing:
        raise HTTPException(400, f"day is missing fields: {', '.join(missing)}")
    if not isinstance(row["date"], str) or len(row["date"]) != 10:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    for k in ("token_count_day", *FEATURE_NAMES):
        if not isinstance(row[k], (int, float)):
            raise HTTPException(400, f"{k} must be a number")
    # Store only what the schema knows. Anything else, including any field
    # that could carry text, is dropped at the door.
    return {k: row[k] for k in ("date", "utterances", "token_count_day", *FEATURE_NAMES) if k in row}


def build_app(
    store: Store | None = None,
    default_profile: str = DEMO_PROFILE,
    seed: bool = True,
    note_deps: dict | None = None,
) -> FastAPI:
    store = store or MemoryStore()
    if seed:
        seed_demo(store, default_profile)

    app = FastAPI(title="Bellwether", version="0.1.0", docs_url="/v1/docs", openapi_url="/v1/openapi.json")
    # CORS is handled by exactly one layer. On Lambda the function URL's CORS
    # configuration reflects the origin and exposes MCP-Session-Id; if the app
    # also emitted Access-Control-Allow-Origin, the browser would see two
    # different values ("*" and the origin) and refuse the response. curl
    # never notices; only a real browser does. Found by Lighthouse's console
    # audit on the deployed site, not by any test. Locally there is no
    # function URL, so the middleware runs.
    if "AWS_LAMBDA_FUNCTION_NAME" not in os.environ:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["MCP-Session-Id"],
        )
    app.state.store = store
    app.state.default_profile = default_profile

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "protocol": "2025-11-25", "default_profile": default_profile}

    @app.get("/api/resilience")
    def resilience():
        return {
            "detection": {
                "usesModels": False,
                "rationale": "Feature extraction is a tagger and parser, and the baseline engine is pure arithmetic. Nothing that decides a tier calls a model, so there is nothing to fall back from, and a reviewer can reproduce any number from the day's features.",
            },
            "weeklyNote": {
                "modelLadder": MODEL_LADDER,
                "onTotalFailure": "the deterministic template, which is the engine's own summary",
                "rationale": "Degrades in warmth, never in accuracy. Every note reports which rung wrote it and what was tried.",
                "enabled": os.environ.get("BELLWETHER_BEDROCK") == "1",
            },
            "store": {
                "kind": type(store).__name__,
                "design": "raw day feature rows only; tiers, trends and reports derived on every read, never stored",
                "rationale": "A summary cannot drift from the days that produced it, and a config change re-derives the whole history.",
            },
            "privacy": {
                "textStored": False,
                "rationale": "The API accepts feature rows, not text. Extraction runs where the transcript is, and only nine numbers a day cross the line. A stored row holds no string but the date.",
            },
            "ingestion": {
                "paths": ["bee conversations / now / changed (cursor, exactly-once)", "bee stream --json", "bee sync markdown", "bee stream --webhook-endpoint into POST /v1/profiles/{id}/days"],
                "rationale": "Four ways in, one schema out; the cursor is saved only after features persist.",
            },
        }

    @app.get("/v1/schema")
    def schema():
        return {"features": features_schema(), "exposure": "token_count_day", "disclaimer": DISCLAIMER}

    @app.get("/v1/profiles/{profile_id}/summary")
    def summary(profile_id: str):
        view = profile_view(store, profile_id)
        return {"profile_id": profile_id, "simulated": view["simulated"], **view["summary"].to_dict(), "disclaimer": DISCLAIMER}

    @app.get("/v1/profiles/{profile_id}/assessments")
    def assessments(profile_id: str, weeks: int = 8):
        view = profile_view(store, profile_id)
        weeks = max(1, min(12, weeks))
        return {
            "profile_id": profile_id,
            "simulated": view["simulated"],
            "days": [a.to_dict() for a in view["assessments"][-weeks * 7 :]],
        }

    @app.get("/v1/profiles/{profile_id}/days")
    def days(profile_id: str):
        view = profile_view(store, profile_id)
        return {"profile_id": profile_id, "simulated": view["simulated"], "days": view["days"]}

    @app.post("/v1/profiles/{profile_id}/days")
    async def post_days(profile_id: str, request: Request):
        body = await request.json()
        rows = body if isinstance(body, list) else body.get("days") if isinstance(body, dict) else None
        if not isinstance(rows, list) or not rows:
            raise HTTPException(400, "send a list of day feature rows, or {\"days\": [...]}")
        clean = [validate_day(r) for r in rows]
        for r in clean:
            store.put_day(profile_id, r)
        view = profile_view(store, profile_id)
        return {"stored": len(clean), "profile_id": profile_id, "tier": view["summary"].tier, "eligible_days": view["summary"].eligible_days}

    @app.post("/v1/profiles/{profile_id}/annotations")
    async def post_annotation(profile_id: str, request: Request):
        body = await request.json()
        date, note = (body or {}).get("date"), (body or {}).get("note")
        if not isinstance(date, str) or len(date) != 10 or not isinstance(note, str) or not note.strip():
            raise HTTPException(400, "date (YYYY-MM-DD) and note are required")
        store.put_annotation(profile_id, date, note.strip()[:200])
        return {"recorded": True, "date": date, "note": note.strip()[:200]}

    @app.post("/v1/profiles/{profile_id}/checks")
    async def post_check(profile_id: str, request: Request):
        body = await request.json() or {}
        kind, score = body.get("kind"), body.get("score")
        if kind not in ("animal_fluency", "sentence_repetition") or not isinstance(score, int) or not 0 <= score <= 100:
            raise HTTPException(400, "kind must be animal_fluency or sentence_repetition; score an integer 0 to 100")
        check = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "kind": kind,
            "score": score,
            "detail": str(body.get("detail") or "")[:300],
        }
        store.put_check(profile_id, check)
        return {"recorded": True, **check}

    @app.get("/v1/profiles/{profile_id}/report")
    def report(profile_id: str, weeks: int = 8):
        return build_report(profile_view(store, profile_id), max(1, min(12, weeks)))

    @app.get("/v1/profiles/{profile_id}/weekly-note")
    def weekly_note(profile_id: str):
        view = profile_view(store, profile_id)
        trend = [
            {"date": a.date, "tier": a.tier, "annotation": a.annotation}
            for a in view["assessments"][-7:]
        ]
        note = phrase_weekly_note(view["summary"].to_dict(), trend, note_deps)
        return {"profile_id": profile_id, "simulated": view["simulated"], **note, "disclaimer": DISCLAIMER}

    @app.post("/v1/profiles/{profile_id}/reset")
    def reset(profile_id: str):
        if profile_id != default_profile:
            raise HTTPException(403, "only the demo profile can be reset")
        store.reset(profile_id)
        seeded = seed_demo(store, profile_id)
        return {"reset": True, "seeded_days": seeded}

    @app.exception_handler(HTTPException)
    async def http_error(_req, exc: HTTPException):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    register_mcp(app, store, default_profile)
    return app
