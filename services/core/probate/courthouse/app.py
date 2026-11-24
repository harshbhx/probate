"""The Courthouse web app: JSON API for the website, admin routes, audio, and the built UI.

    uvicorn probate.courthouse.app:app --host 0.0.0.0 --port 8080

Env: PROBATE_RUN_CLOCK=1 starts the scheduler (on the real Courthouse Sprite).
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from probate.adapters import world
from probate.common.config import settings
from probate.courthouse import ancestor, views
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost, SpritesHost
from probate.courthouse.scheduler import Scheduler
from probate.courthouse.store import Store

store = Store(settings.db_path)
w = world(settings)
host = LocalHost(settings, w) if settings.fake else SpritesHost(settings, w)
family = Family(settings, store, w, host)
scheduler = Scheduler(family)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = (
        asyncio.create_task(scheduler.run()) if os.environ.get("PROBATE_RUN_CLOCK") == "1" else None
    )
    yield
    if task:
        task.cancel()


app = FastAPI(title="Probate Courthouse", lifespan=lifespan)


def _need(obj):
    if obj is None:
        raise HTTPException(404, "Not in the register")
    return obj


@app.get("/healthz")
def healthz() -> dict:
    living = store.living()
    return {
        "ok": True,
        "living": living.gen if living else None,
        "mode": store.get_setting("mode", "live"),
    }


@app.get("/api/summary")
def api_summary() -> dict:
    return views.summary(store)


@app.get("/api/generations/{gen}")
def api_generation(gen: int) -> dict:
    return _need(views.generation(store, gen))


@app.get("/api/trials/latest")
def api_trial_latest() -> dict:
    latest = views.summary(store)["latest_trial"]
    return _need(latest and views.trial(store, latest))


@app.get("/api/trials/{gen}")
def api_trial(gen: int) -> dict:
    return _need(views.trial(store, gen))


@app.get("/api/genome")
def api_genome() -> dict:
    return views.genome(store)


@app.get("/api/evidence")
def api_evidence() -> dict:
    return views.evidence(store)


@app.get("/api/events")
def api_events(since: int = 0) -> list[dict]:
    return views.events(store, since)


class Ask(BaseModel):
    question: str


_asks: dict[str, list[float]] = defaultdict(list)


@app.post("/api/generations/{gen}/ask")
def api_ask(gen: int, body: Ask, request: Request) -> JSONResponse:
    ip = request.client.host if request.client else ""
    now = time.time()
    _asks[ip] = [t for t in _asks[ip] if now - t < 60]
    if len(_asks[ip]) >= 10:
        return JSONResponse({"error": "rate_limited"}, status_code=429)
    _asks[ip].append(now)
    out = ancestor.ask(store, w, settings, gen, body.question, ip)
    return JSONResponse(out, status_code=400 if "error" in out else 200)


@app.get("/audio/{name}")
def audio(name: str) -> FileResponse:
    path = settings.data_dir / "audio" / name
    if "/" in name or not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="audio/mpeg")


def _admin(token: str | None) -> None:
    if token != settings.admin_token:
        raise HTTPException(403, "Admin token required")


@app.post("/admin/pause")
def admin_pause(x_probate_admin: str | None = Header(None)) -> dict:
    _admin(x_probate_admin)
    store.set_setting("paused", "1")
    return {"paused": True}


@app.post("/admin/resume")
def admin_resume(x_probate_admin: str | None = Header(None)) -> dict:
    _admin(x_probate_admin)
    store.set_setting("paused", "0")
    return {"paused": False}


@app.post("/admin/force-death")
def admin_force_death(x_probate_admin: str | None = Header(None)) -> dict:
    _admin(x_probate_admin)
    living = _need(store.living())
    g = family.death(living)
    family.trial(g)
    return {"died": g.gen}


@app.post("/admin/contested/{item_id}")
def admin_contested(
    item_id: str, decision: str, x_probate_admin: str | None = Header(None)
) -> dict:
    _admin(x_probate_admin)
    if decision not in ("approve", "refuse"):
        raise HTTPException(400, "decision must be approve or refuse")
    store.x(
        "UPDATE judgements SET owner_decision=? WHERE item_id=? AND verdict='contested'",
        decision,
        item_id,
    )
    return {"item_id": item_id, "decision": decision}


@app.post("/admin/tick")
def admin_tick(x_probate_admin: str | None = Header(None)) -> dict:
    _admin(x_probate_admin)
    return {"state": scheduler.step()}


# The built website (apps/web/dist). Any unknown path returns index.html for the client router.
@app.get("/{path:path}")
def spa(path: str):
    dist = settings.web_dist
    target = dist / path
    if path and target.is_file() and dist in target.resolve().parents:
        return FileResponse(target)
    index = dist / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {"message": "The website isn't built yet. Run `npm run build` in apps/web."},
        status_code=503,
    )
