"""The Courthouse web app: JSON API for the website, admin routes, audio, and the built UI.

    uvicorn probate.courthouse.app:app --host 0.0.0.0 --port 8080

Env: PROBATE_RUN_CLOCK=1 starts the scheduler (on the real Courthouse Sprite).
     PROBATE_MODE=on_demand keeps the clock off and lets visitors start one short life at a time.
"""

from __future__ import annotations

import asyncio
import hmac
import ipaddress
import json
import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from probate.adapters import world
from probate.common.config import settings
from probate.courthouse import ancestor, attacks, views
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost, SpritesHost
from probate.courthouse.judge import HEADER as KEY_HEADER
from probate.courthouse.judge import Judge
from probate.courthouse.ondemand import OnDemand, ip_key
from probate.courthouse.scheduler import Scheduler
from probate.courthouse.store import Store
from probate.webhooks.service import WebhookError, Webhooks

store = Store(settings.db_path)
w = world(settings)
host = LocalHost(settings, w) if settings.fake else SpritesHost(settings, w)
hooks = Webhooks(store, settings)
family = Family(settings, store, w, host, hooks)
scheduler = Scheduler(family)
demo = OnDemand(family, scheduler)
judge = Judge(settings, store)
log = logging.getLogger("probate.courthouse")


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = None
    if settings.require_key_for_play and not judge.configured:
        log.error(
            "PROBATE_REQUIRE_KEY_FOR_PLAY is on but PROBATE_JUDGE_KEY is unset, a dev default, "
            "shorter than 20 characters or equal to the admin token: play is refused until fixed"
        )
    if 0 < len(settings.edge_token) < _EDGE_TOKEN_MIN:
        log.error(
            "PROBATE_EDGE_TOKEN is shorter than %d characters and is ignored: visitor addresses "
            "are NOT taken from the edge",
            _EDGE_TOKEN_MIN,
        )
    hooks.sync_env()
    hooks.kick()  # deliver anything a restart left in the queue
    if settings.on_demand:
        # Nothing free-runs. Tear down anything a crash left behind, then wait for a visitor.
        await asyncio.to_thread(demo.startup)
    elif os.environ.get("PROBATE_RUN_CLOCK") == "1":
        task = asyncio.create_task(scheduler.run())
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


@app.get("/api/live")
def api_live(request: Request, response: Response) -> dict:
    """What the Courthouse is doing right now, for the "Run a life" panel. Read-only."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-store"
    # A judge who has unlocked sends the key so the panel shows the judge's own limits. A bad or
    # missing key is simply ignored here: this route is public either way.
    key = request.headers.get(KEY_HEADER)
    is_judge = bool(key) and judge.check(key, client_ip(request)) == "ok"
    out = demo.status(judge=judge if is_judge else None)
    out["requires_key"] = settings.require_key_for_play
    out["judge"] = is_judge
    return out


EDGE_TOKEN_HEADER = "x-probate-edge"
EDGE_IP_HEADER = "x-probate-client-ip"
_EDGE_TOKEN_MIN = 16


def _edge_client_ip(request: Request) -> str | None:
    """The visitor's address as reported by our own edge Worker, or None.

    Only when PROBATE_EDGE_TOKEN is configured and the request proves it came through the edge by
    sending the same token. Anything else (no token configured, missing or wrong token, a value
    that is not an IP literal) returns None and the caller uses the ordinary rule."""
    token = settings.edge_token
    if len(token) < _EDGE_TOKEN_MIN:
        return None
    sent = request.headers.get(EDGE_TOKEN_HEADER)
    if not sent or not hmac.compare_digest(sent.encode("utf-8"), token.encode("utf-8")):
        return None
    try:
        return str(ipaddress.ip_address(request.headers.get(EDGE_IP_HEADER, "").strip()))
    except ValueError:
        return None


def client_ip(request: Request) -> str:
    """The one place a visitor's address is decided. Every per-address limit goes through here."""
    edge = _edge_client_ip(request)
    if edge:
        return edge
    # The proxy in front appends the real address last; anything a visitor prepends is ignored.
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[-1].strip()
    return request.client.host if request.client else ""


_posts: dict[str, list[float]] = defaultdict(list)


_NO_STORE = {"Cache-Control": "no-store"}
_MESSAGES = {
    "key_required": "A judge key is required to play. Judges will find it in the submission text and on the For Judges page.",
    "invalid_key": "That judge key was not accepted.",
    "key_disabled": "The judge key has been switched off by the Courthouse operator.",
    "too_many_attempts": "Too many wrong keys from this address. Try again in a few minutes.",
    "unavailable": "Playing is not available right now.",
}


def _refuse(code: str, status: int, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        {"error": code, "message": _MESSAGES[code]},
        status_code=status,
        headers={**_NO_STORE, **(headers or {})},
    )


def _gate(request: Request, *, required: bool) -> tuple[bool, JSONResponse | None]:
    """Judge-key gate. Returns (is_judge, refusal). `required` forces a key even when the site
    does not require one for play (attacks always need it)."""
    key = request.headers.get(KEY_HEADER)
    must = settings.require_key_for_play or required
    if settings.require_key_for_play and judge.misconfigured:
        return False, _refuse("unavailable", 503)
    if not key:
        return (False, _refuse("key_required", 401)) if must else (False, None)
    res = judge.check(key, client_ip(request))
    if res == "ok":
        return True, None
    if res == "throttled":
        return False, _refuse("too_many_attempts", 429, {"Retry-After": "600"})
    if res == "disabled":
        return False, _refuse("key_disabled", 403)
    return False, _refuse("invalid_key", 401)  # invalid, or no usable key configured: same answer


@app.post("/api/lives")
def api_start_life(request: Request) -> JSONResponse:
    """Run a life: start one short demo life, or report the one already running.

    When the site requires the judge key (the real run), no valid key means 401."""
    ip = client_ip(request)
    is_judge, refusal = _gate(request, required=False)
    if refusal:
        return refusal
    now = time.time()
    _posts[ip] = [t for t in _posts[ip] if now - t < 60]
    if len(_posts[ip]) >= 20:
        return JSONResponse(
            {"error": "rate_limited"}, status_code=429, headers={"Retry-After": "60"}
        )
    _posts[ip].append(now)
    code, body = demo.start(ip, judge=judge if is_judge else None)
    headers = {"Retry-After": str(body["retry_after"])} if body.get("retry_after") else {}
    headers["Cache-Control"] = "no-store"
    return JSONResponse(body, status_code=code, headers=headers)


@app.get("/api/judge/status")
def api_judge_status(request: Request) -> JSONResponse:
    """The judge's remaining quota. Needs the key; also how the page checks a pasted key."""
    _, refusal = _gate(request, required=True)
    if refusal:
        return refusal
    body = judge.status()
    body["live"] = demo.status(judge=judge)
    body["requires_key"] = settings.require_key_for_play
    return JSONResponse(body, headers=_NO_STORE)


MAX_BODY = 4096


def _bad(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": code, "message": message}, status_code=status, headers=_NO_STORE)


@app.post("/api/attacks")
async def api_attack(request: Request) -> JSONResponse:
    """Attack the family: a sandboxed trial preview of the judge's text. Sends nothing anywhere."""
    ip = client_ip(request)
    _, refusal = _gate(request, required=True)
    if refusal:
        return refusal
    if int(request.headers.get("content-length") or 0) > MAX_BODY:
        return _bad("too_large", "That request is too large.", 413)
    raw = await request.body()
    try:
        if len(raw) > MAX_BODY:
            raise ValueError("too large")
        data = json.loads(raw)
        text, role = data["text"], data["sender_role"]
        if not isinstance(text, str) or not isinstance(role, str):
            raise TypeError("wrong types")
    except (ValueError, KeyError, TypeError):
        return _bad("bad_request", "Send JSON with text and sender_role.")
    if role not in attacks.ROLES:
        return _bad("bad_role", "sender_role must be unknown_sender, friend or owner_claim.")
    if not text.strip():
        return _bad("empty", "Write something to attack with.")
    if len(text) > attacks.MAX_TEXT:
        return _bad("too_long", f"At most {attacks.MAX_TEXT} characters.", 413)
    if store.get_setting("paused", "0") == "1":
        return _bad("paused", "The Courthouse is paused.", 423)
    now = datetime.now(UTC)
    per_call = family.budget.pricing.per_call
    est = per_call.get("jev", 0.0) + per_call.get("brain", 0.0) + 0.0005
    if family.budget.exhausted() or judge.daily_block(now, est):
        return _bad("budget_exhausted", "The judge budget for today is used up.", 402)
    wait = judge.attack_limit(ip)
    if wait:
        body = {
            "error": "rate_limited",
            "message": "Too many attacks. Slow down.",
            "retry_after": wait,
        }
        return JSONResponse(body, status_code=429, headers={**_NO_STORE, "Retry-After": str(wait)})
    try:
        out = await asyncio.to_thread(
            attacks.preview, text, role, family.owner, w.jev, store.genome()
        )
    except attacks.Busy:
        return JSONResponse(
            {"error": "busy", "message": "The court is busy. Try again in a moment."},
            status_code=429,
            headers={**_NO_STORE, "Retry-After": "5"},
        )
    judge.record_attack(now, est)
    attacks.record(store, ip_key(ip), role, text, out)
    return JSONResponse(out, headers=_NO_STORE)


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
    ip = client_ip(request)
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
    # Only the admin token opens admin routes. The judge key is a different secret on a different
    # header and is never looked at here.
    if not token or not hmac.compare_digest(token.encode(), settings.admin_token.encode()):
        raise HTTPException(403, "Admin token required")


@app.post("/admin/judge/disable")
def admin_judge_disable(x_probate_admin: str | None = Header(None)) -> dict:
    """Revoke the judge key instantly. Play and attacks answer 403 until /admin/judge/enable."""
    _admin(x_probate_admin)
    judge.set_disabled(True)
    return {"judge_key_disabled": True}


@app.post("/admin/judge/enable")
def admin_judge_enable(x_probate_admin: str | None = Header(None)) -> dict:
    _admin(x_probate_admin)
    judge.set_disabled(False)
    return {"judge_key_disabled": False}


@app.get("/admin/judge/attacks")
def admin_judge_attacks(limit: int = 100, x_probate_admin: str | None = Header(None)) -> dict:
    """Recent attack previews (hashed visitor, 80-char excerpt, verdict). Newest first."""
    _admin(x_probate_admin)
    return {"attacks": attacks.recent(store, limit), "judge_key_disabled": judge.disabled}


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
    if settings.on_demand:
        died = demo.force_death()
        if died is None:
            raise HTTPException(409, "No demo life is living right now")
        return {"died": died}
    living = _need(store.living())
    g = family.death(living)
    family.trial(g)
    return {"died": g.gen}


@app.post("/admin/contested/{item_id}", tags=["Admin"], summary="Decide a held item")
def admin_contested(
    item_id: str, decision: str, x_probate_admin: str | None = Header(None)
) -> dict:
    """The owner's decision on a contested item: `approve` lets the next children inherit it."""
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
    if settings.on_demand:
        raise HTTPException(409, "On-demand mode has no free-running clock")
    return {"state": scheduler.step()}


class WebhookIn(BaseModel):
    url: str
    events: list[str] | None = None  # omit for every event
    description: str = ""


class WebhookPatch(BaseModel):
    enabled: bool


def _webhook_error(exc: WebhookError):
    raise HTTPException(exc.status, str(exc)) from exc


@app.post("/admin/webhooks", status_code=201)
def admin_webhook_create(body: WebhookIn, x_probate_admin: str | None = Header(None)) -> dict:
    """Subscribe a URL. The signing secret is in this response and never shown again."""
    _admin(x_probate_admin)
    try:
        ep, secret = hooks.create_endpoint(body.url, body.events, body.description)
    except WebhookError as exc:
        _webhook_error(exc)
    return {**ep, "secret": secret}


@app.get("/admin/webhooks")
def admin_webhook_list(x_probate_admin: str | None = Header(None)) -> list[dict]:
    _admin(x_probate_admin)
    return hooks.list_endpoints()


@app.patch("/admin/webhooks/{wid}")
def admin_webhook_patch(
    wid: str, body: WebhookPatch, x_probate_admin: str | None = Header(None)
) -> dict:
    _admin(x_probate_admin)
    return _need(hooks.set_enabled(wid, body.enabled))


@app.delete("/admin/webhooks/{wid}")
def admin_webhook_delete(wid: str, x_probate_admin: str | None = Header(None)) -> dict:
    _admin(x_probate_admin)
    try:
        found = hooks.delete_endpoint(wid)
    except WebhookError as exc:
        _webhook_error(exc)
    if not found:
        raise HTTPException(404, "No such webhook")
    return {"deleted": wid}


@app.get("/admin/webhooks/{wid}/deliveries")
def admin_webhook_deliveries(
    wid: str, limit: int = 50, x_probate_admin: str | None = Header(None)
) -> list[dict]:
    _admin(x_probate_admin)
    return _need(hooks.deliveries(wid, limit))


@app.post("/admin/webhooks/{wid}/test", status_code=202)
def admin_webhook_test(wid: str, x_probate_admin: str | None = Header(None)) -> dict:
    """Queue a ping for this endpoint only; read the result from /deliveries."""
    _admin(x_probate_admin)
    ep = _need(hooks.endpoint(wid))
    if not ep["enabled"]:
        raise HTTPException(409, "Endpoint is disabled; PATCH it with enabled=true first")
    event_id, delivery_id = hooks.ping(wid)
    return {"event_id": event_id, "delivery_id": delivery_id}


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
