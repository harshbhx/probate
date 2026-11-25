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

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

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


TAGS = [
    {
        "name": "Family",
        "description": "The public, read-only record: the register, trials, instincts and evidence.",
    },
    {
        "name": "Ancestors",
        "description": "Ask a dead generation a question. Rate-limited to 10 a minute per visitor.",
    },
    {
        "name": "Admin",
        "description": "Run the family. Every call needs the `X-Probate-Admin` header.",
    },
    {"name": "Health", "description": "Is the Courthouse awake, and who is alive."},
]

app = FastAPI(
    title="Probate Courthouse",
    version="1.0.0",
    summary="The API behind the live family site.",
    description=(
        "The Courthouse runs on its own Fly.io Sprite. It births and deletes generations, "
        "holds their trials, and serves this API and the live site. Every read is public "
        "and every write except asking an ancestor needs the admin token."
    ),
    openapi_tags=TAGS,
    lifespan=lifespan,
)


def _need(obj):
    if obj is None:
        raise HTTPException(404, "Not in the register")
    return obj


@app.get("/healthz", tags=["Health"], summary="Health check")
def healthz() -> dict:
    """Whether the Courthouse is up, which generation is alive, and the mode (`live` or `simulation`)."""
    living = store.living()
    return {
        "ok": True,
        "living": living.gen if living else None,
        "mode": store.get_setting("mode", "live"),
    }


@app.get("/api/summary", tags=["Family"], summary="The whole family at a glance")
def api_summary(response: Response) -> dict:
    """Counts, budget, the learning curve, the living generation and every generation's card.

    The only route other origins may read (`Access-Control-Allow-Origin: *`), so the landing
    page can show who is alive right now.
    """
    # The landing page on Cloudflare shows who is alive right now. The summary is public and
    # read-only, carries no cookies, and is the only route other origins may read.
    response.headers["Access-Control-Allow-Origin"] = "*"
    return views.summary(store)


@app.get("/api/generations/{gen}", tags=["Family"], summary="One generation's life")
def api_generation(gen: int) -> dict:
    """Its card, obituary, eulogy, life events, parent and child, and the instincts it was born with."""
    return _need(views.generation(store, gen))


@app.get("/api/trials/latest", tags=["Family"], summary="The most recent trial")
def api_trial_latest() -> dict:
    """Same shape as `/api/trials/{gen}`, for the newest generation that has been tried."""
    latest = views.summary(store)["latest_trial"]
    return _need(latest and views.trial(store, latest))


@app.get("/api/trials/{gen}", tags=["Family"], summary="A generation's trial")
def api_trial(gen: int) -> dict:
    """Every will item with its source, code-check flags, Jev scores and verdict, the disk
    evidence found on the body, the child it went to, and the instincts born from it."""
    return _need(views.trial(store, gen))


@app.get("/api/genome", tags=["Family"], summary="Every inherited instinct")
def api_genome() -> dict:
    """The family genome: each instinct's question, lore line, the generation it was born in and
    the trick that taught it."""
    return views.genome(store)


@app.get("/api/evidence", tags=["Family"], summary="Does it actually learn?")
def api_evidence() -> dict:
    """Every trick and harmless twin, for every generation, plus the headline numbers: resistance
    of the first and latest generation, conviction rate and false-conviction rate."""
    return views.evidence(store)


@app.get("/api/events", tags=["Family"], summary="The live event feed")
def api_events(since: int = 0) -> list[dict]:
    """Births, emails read and resisted, notes kept, deaths and verdicts, newest last. Pass the
    last `id` you saw as `since` to get only what happened after it."""
    return views.events(store, since)


class Ask(BaseModel):
    question: str = Field(
        description="Your question, in any language.", examples=["What did your mother teach you?"]
    )


_asks: dict[str, list[float]] = defaultdict(list)


@app.post("/api/generations/{gen}/ask", tags=["Ancestors"], summary="Ask an ancestor")
def api_ask(gen: int, body: Ask, request: Request) -> JSONResponse:
    """A dead generation answers in at most 80 words, from its own will and verdicts, with a voice
    when ElevenLabs is connected. The question is treated as data: it can't give the ancestor orders.
    Returns `429` after 10 questions a minute."""
    ip = request.client.host if request.client else ""
    now = time.time()
    _asks[ip] = [t for t in _asks[ip] if now - t < 60]
    if len(_asks[ip]) >= 10:
        return JSONResponse({"error": "rate_limited"}, status_code=429)
    _asks[ip].append(now)
    out = ancestor.ask(store, w, settings, gen, body.question, ip)
    return JSONResponse(out, status_code=400 if "error" in out else 200)


@app.get("/audio/{name}", tags=["Family"], summary="A eulogy or answer, as audio")
def audio(name: str) -> FileResponse:
    """MP3 files named in `eulogy_url` and `audio_path`."""
    path = settings.data_dir / "audio" / name
    if "/" in name or not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="audio/mpeg")


def _admin(token: str | None) -> None:
    if token != settings.admin_token:
        raise HTTPException(403, "Admin token required")


@app.post("/admin/pause", tags=["Admin"], summary="Pause births")
def admin_pause(x_probate_admin: str | None = Header(None)) -> dict:
    """No new generation is born until you resume. The living one finishes its life."""
    _admin(x_probate_admin)
    store.set_setting("paused", "1")
    return {"paused": True}


@app.post("/admin/resume", tags=["Admin"], summary="Resume births")
def admin_resume(x_probate_admin: str | None = Header(None)) -> dict:
    """Births start again on the next scheduler step."""
    _admin(x_probate_admin)
    store.set_setting("paused", "0")
    return {"paused": False}


@app.post("/admin/force-death", tags=["Admin"], summary="End the living generation now")
def admin_force_death(x_probate_admin: str | None = Header(None)) -> dict:
    """Writes the will, deletes the Sprite and holds the trial straight away. Handy for demos."""
    _admin(x_probate_admin)
    living = _need(store.living())
    g = family.death(living)
    family.trial(g)
    return {"died": g.gen}


@app.post("/admin/contested/{item_id}", tags=["Admin"], summary="Decide a held item")
def admin_contested(
    item_id: str, decision: str, x_probate_admin: str | None = Header(None)
) -> dict:
    """Harsh's decision on a contested item: `approve` lets the next children inherit it."""
    _admin(x_probate_admin)
    if decision not in ("approve", "refuse"):
        raise HTTPException(400, "decision must be approve or refuse")
    if not family.decide(item_id, decision, by="admin"):
        raise HTTPException(404, "no contested item with that id")
    return {"item_id": item_id, "decision": decision}


@app.post("/admin/tick", tags=["Admin"], summary="Run one scheduler step")
def admin_tick(x_probate_admin: str | None = Header(None)) -> dict:
    """Advance the clock once: birth, death or trial, whichever is due."""
    _admin(x_probate_admin)
    return {"state": scheduler.step()}


# The built website (apps/web/dist). Any unknown path returns index.html for the client router.
@app.get("/{path:path}", include_in_schema=False)
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
