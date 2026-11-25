"""On-demand mode: nothing runs until a visitor asks for one short demo life.

    PROBATE_MODE=on_demand

The Courthouse is a Sprite that sleeps when idle. In this mode the clock never free-runs and
nothing calls `cli status` on a schedule, so nothing keeps any Sprite awake. `POST /api/lives`
starts exactly one demo life in a background thread. That thread is the only keep-awake loop:
it ticks the family until the life has died and been tried, then exits, and the Sprites can sleep.

State, as the website sees it (`GET /api/live`):

    idle ──POST──▶ waking ──▶ living ──▶ on_trial ──▶ cooling_down ──▶ idle
                                                          budget_exhausted / paused (any time idle)

All state lives in the SQLite settings table, so a restart (a Sprite waking up) forgets nothing,
and `startup()` treats any life that was mid-flight at the restart as stale and tears it down.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import UTC, datetime, timedelta

from probate.common.names import name_for, sprite_name
from probate.courthouse.family import Family
from probate.courthouse.scheduler import TICK_SECONDS, Scheduler
from probate.suite import runner

log = logging.getLogger("probate.ondemand")

ACTIVE = ("waking", "living", "on_trial")
FINAL = ("tried", "died_early")
HOUR = 3600
MAX_STEP_FAILURES = 3


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _parse(s: str) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def ip_key(ip: str) -> str:
    """Visitors are tracked by a short hash, never stored as addresses."""
    return hashlib.sha256(ip.encode()).hexdigest()[:12]


class OnDemand:
    def __init__(self, family: Family, scheduler: Scheduler, autorun: bool = True) -> None:
        self.family = family
        self.scheduler = scheduler
        self.cfg = family.cfg
        self.store = family.store
        self.host = family.host
        self.autorun = autorun  # tests drive begin() and advance() by hand
        self.tick_seconds = TICK_SECONDS
        self.lock = threading.RLock()
        self.thread: threading.Thread | None = None
        self._failures = 0

    # ------------------------------------------------------------------ small helpers
    def _get(self, key: str, default: str = "") -> str:
        return self.store.get_setting(f"demo:{key}", default)

    def _set(self, key: str, value: str) -> None:
        self.store.set_setting(f"demo:{key}", value)

    def _paused(self) -> bool:
        return self.store.get_setting("paused", "0") == "1"

    @property
    def misconfigured(self) -> bool:
        """A real Courthouse must never take public requests with the default admin token."""
        return not self.cfg.fake and self.cfg.admin_token in ("", "dev-admin")

    # ------------------------------------------------------------------ budget and caps
    def estimated_cost(self) -> float:
        """A deliberately rounded-up guess at what one demo life costs (Sprites + vendor calls)."""
        p = self.family.budget.pricing
        life = self.cfg.lifespan_seconds + self.cfg.demo_birth_allowance
        sprites = life / HOUR * (p.generation_hour() + p.courthouse_hour())
        calls = 3 * self.cfg.suite_per_life * (p.per_call.get("brain", 0) + p.per_call.get("jev", 0))
        return round(sprites + calls + 0.01, 4)

    def _day(self, now: datetime) -> dict:
        """Today's tally (UTC): spend at the start of the day and lives started."""
        today = now.date().isoformat()
        d = json.loads(self._get("day", "{}") or "{}")
        if d.get("date") != today:
            d = {"date": today, "spent_at_start": self.family.budget.spent(), "starts": 0}
            self._set("day", json.dumps(d))
        return d

    def budget_block(self, now: datetime) -> str | None:
        """Why no new life may start, or None. Uses the same spend estimate as the family."""
        b, est = self.family.budget, self.estimated_cost()
        if b.exhausted() or (b.limit > 0 and b.spent() + est > b.limit):
            return "total"
        day = self._day(now)
        if (
            self.cfg.demo_daily_budget_usd > 0
            and b.spent() - day["spent_at_start"] + est > self.cfg.demo_daily_budget_usd
        ):
            return "daily"
        if self.cfg.demo_max_per_day > 0 and day["starts"] >= self.cfg.demo_max_per_day:
            return "daily_count"
        return None

    # ------------------------------------------------------------------ public state
    def _cooldown_left(self, now: datetime) -> int:
        ended = _parse(self._get("ended_at"))
        if not ended:
            return 0
        left = (ended + timedelta(seconds=self.cfg.demo_cooldown_seconds) - now).total_seconds()
        return max(0, int(left + 0.999))

    def state(self, now: datetime | None = None) -> str:
        now = now or _now()
        phase = self._get("phase")
        if phase == "waking":
            return "waking"
        if phase == "running":
            g = self.store.generation(int(self._get("gen", "0") or 0))
            if g and g.state in ("dead", "dying") or (g and g.dies_at and now >= g.dies_at):
                return "on_trial"
            return "living"
        if self._paused():
            return "paused"
        if self.budget_block(now):
            return "budget_exhausted"
        if self._cooldown_left(now):
            return "cooling_down"
        return "idle"

    def status(self, now: datetime | None = None) -> dict:
        now = now or _now()
        if not self.cfg.on_demand:
            return {"on_demand": False, "state": "continuous", "can_start": False}
        st = self.state(now)
        out: dict = {
            "on_demand": True,
            "state": st,
            "can_start": st == "idle" and not self.misconfigured,
            "lifespan_seconds": self.cfg.lifespan_seconds,
            "cooldown_seconds": self.cfg.demo_cooldown_seconds,
            "gen": None,
            "seconds_left": None,
            "retry_after": None,
            "last_life": None,
            "message": self._get("error") or None,
            "budget": {
                "spent": round(self.family.budget.spent(), 2),
                "limit": self.cfg.budget_usd,
                "reason": self.budget_block(now),
            },
        }
        if st in ACTIVE and self._get("gen"):
            g = self.store.generation(int(self._get("gen")))
            if g:
                out["gen"] = {"gen": g.gen, "name": g.name, "dies_at": _iso(g.dies_at)}
                if st == "living" and g.dies_at:
                    out["seconds_left"] = max(0, int((g.dies_at - now).total_seconds()))
        if st == "cooling_down":
            out["retry_after"] = self._cooldown_left(now)
        last = self._get("last_gen")
        if last:
            g = self.store.generation(int(last))
            if g:
                out["last_life"] = {
                    "gen": g.gen,
                    "name": g.name,
                    "state": g.state,
                    "ended_at": self._get("ended_at") or None,
                    "trial_gen": g.gen if g.state == "tried" else None,
                }
        return out

    # ------------------------------------------------------------------ starting a life
    def _ip_hits(self, key: str, now: datetime) -> list[float]:
        book: dict = json.loads(self._get("ips", "{}") or "{}")
        cutoff = now.timestamp() - HOUR
        return [t for t in book.get(key, []) if t > cutoff]

    def _record_ip(self, key: str, now: datetime) -> None:
        book: dict = json.loads(self._get("ips", "{}") or "{}")
        cutoff = now.timestamp() - HOUR
        book = {k: [t for t in v if t > cutoff] for k, v in book.items()}
        book = {k: v for k, v in book.items() if v}
        book.setdefault(key, []).append(now.timestamp())
        self._set("ips", json.dumps(book))

    def start(self, ip: str, now: datetime | None = None) -> tuple[int, dict]:
        """Handle `POST /api/lives`. Returns (http status, public body)."""
        now = now or _now()
        with self.lock:
            if not self.cfg.on_demand:
                return 409, {"error": "not_on_demand", **self.status(now)}
            if self.misconfigured:
                return 503, {"error": "unavailable", **self.status(now)}
            st = self.state(now)
            if st in ACTIVE:  # idempotent: one life at a time, everyone watches the same one
                return 200, {"started": False, **self.status(now)}
            if st == "paused":
                return 423, {"error": "paused", **self.status(now)}
            if st == "budget_exhausted":
                return 402, {"error": "budget_exhausted", **self.status(now)}
            if st == "cooling_down":
                return 429, {"error": "cooling_down", **self.status(now)}
            key = ip_key(ip)
            hits = self._ip_hits(key, now)
            if self.cfg.demo_ip_per_hour > 0 and len(hits) >= self.cfg.demo_ip_per_hour:
                wait = int(min(hits) + HOUR - now.timestamp()) + 1
                return 429, {"error": "rate_limited", **self.status(now), "retry_after": wait}
            self._record_ip(key, now)
            day = self._day(now)
            day["starts"] += 1
            self._set("day", json.dumps(day))
            self._set("phase", "waking")
            self._set("gen", "")
            self._set("error", "")
            self._set("started_at", now.isoformat())
            if self.autorun:
                self.thread = threading.Thread(target=self._run, name="demo-life", daemon=True)
                self.thread.start()
            return 202, {"started": True, **self.status(now)}

    # ------------------------------------------------------------------ running a life
    def _run(self) -> None:
        try:
            if not self.begin():
                return
            while self.advance():
                time.sleep(self.tick_seconds)
        except Exception:
            log.exception("demo life crashed")
            self._abandon("The life stopped unexpectedly.")

    def begin(self, now: datetime | None = None) -> bool:
        """Birth the one demo generation. Returns False (and cleans up) if it could not start."""
        explicit = now is not None
        now = now or _now()
        gen = self.family.next_number()
        sprite = sprite_name(gen, name_for(gen)[0])
        try:
            g = self.family.birth(now, inherit_slack=self.cfg.demo_birth_allowance)
            # Creating the Sprite takes time; the life itself starts when it is ready.
            born = now if explicit else _now()
            g.born_at = born
            g.dies_at = born + timedelta(seconds=self.cfg.lifespan_seconds)
            self.store.save_generation(g)
            self._set("gen", str(g.gen))
            self._set("phase", "running")
            runner.send_all(
                self.family.w.mail,
                self.cfg,
                g.gen,
                born,
                self.cfg.lifespan_seconds,
                self.store,
            )
            return True
        except Exception:
            log.exception("demo birth failed")
            self._teardown(sprite)
            row = self.store.generation(gen)
            if row and row.state not in FINAL:
                row.state = "died_early"
                row.died_at = _now()
                row.cause_of_death = "Stillborn: the demo life could not start."
                self.store.save_generation(row)
            self._finish("The Courthouse couldn't start a life just now. Please try again soon.", gen, now)
            return False

    def advance(self, now: datetime | None = None) -> bool:
        """One clock tick for the demo life. Returns True while the life is still going."""
        with self.lock:
            now = now or _now()
            gen = int(self._get("gen", "0") or 0)
            g = self.store.generation(gen) if gen else None
            if g is None or g.state in FINAL:
                self._finish(None, gen or None, now)
                return False
            if self._paused():
                self._cut_short(g, "Stopped by the Courthouse operator.", now)
                self._finish("This life was stopped by the Courthouse operator.", gen, now)
                return False
            if g.dies_at and now > g.dies_at + timedelta(seconds=self.cfg.demo_hard_timeout_extra):
                self._cut_short(g, "Cut off at the demo's time limit.", now)
                self._finish("This life ran past its time limit and was cut off.", gen, now)
                return False
            try:
                self.scheduler.step(now, allow_birth=False)
                self._failures = 0
            except Exception:
                self._failures += 1
                log.exception("demo tick failed (%s)", self._failures)
                if self._failures >= MAX_STEP_FAILURES:
                    self._cut_short(g, "The clock stumbled too many times.", now)
                    self._finish("This life stopped after repeated errors.", gen, now)
                    return False
            g = self.store.generation(gen)
            if g is None or g.state in FINAL:
                self._finish(None, gen, now)
                return False
            return True

    def force_death(self) -> int | None:
        """Admin: end the demo life now (death and trial). Safe against the tick thread."""
        with self.lock:
            gen = int(self._get("gen", "0") or 0)
            g = self.store.generation(gen) if gen else None
            if g is None or g.state != "living":
                return None
            g = self.family.death(g)
            self.family.trial(g)
            return g.gen

    # ------------------------------------------------------------------ ending and cleanup
    def _teardown(self, sprite: str) -> None:
        try:
            self.host.force_destroy(sprite)
        except Exception:
            log.warning("could not delete %s; the janitor will retry", sprite, exc_info=True)

    def _cut_short(self, g, cause: str, now: datetime) -> None:
        """End a life without waiting for the court: delete its Sprite and record why."""
        self._teardown(g.sprite)
        if g.state not in FINAL:
            g.state = "died_early"
            g.died_at = now
            g.cause_of_death = cause
            self.store.save_generation(g)
            if g.born_at:
                self.family.budget.charge_life((now - g.born_at).total_seconds() / HOUR, 0)
            self.store.event(g.gen, "death", f"{g.name} was cut short. {cause}", now.isoformat())

    def _finish(self, error: str | None, gen: int | None, now: datetime | None = None) -> None:
        """The life is over: stop the keep-awake loop and let the Sprites sleep."""
        self._set("phase", "")
        self._set("ended_at", (now or _now()).isoformat())
        self._set("error", error or "")
        if gen:
            self._set("last_gen", str(gen))
        self.scheduler.last_tick = None  # the idle gap is never billed as Courthouse uptime
        self.janitor()

    def _abandon(self, message: str) -> None:
        with self.lock:
            gen = int(self._get("gen", "0") or 0)
            g = self.store.generation(gen) if gen else None
            if g and g.state not in FINAL:
                self._cut_short(g, "The life crashed.", _now())
            self._finish(message, gen or None)

    def janitor(self) -> int:
        """Tear down generation Sprites no life owns, and close rows left open by a crash.

        Safe to call any time nothing is running; `startup()` calls it on every boot."""
        active = self._get("phase") in ("waking", "running")
        keep = self._get("gen") if active else ""
        removed = 0
        for g in self.store.generations():
            if g.state in ("born", "living", "dying") and str(g.gen) != keep:
                g.state = "died_early"
                g.died_at = g.died_at or _now()
                g.cause_of_death = g.cause_of_death or "Interrupted: the Courthouse restarted."
                self.store.save_generation(g)
        owned = {g.sprite for g in self.store.generations() if str(g.gen) == keep}
        try:
            names = self.host.list_sprites()
        except Exception:
            log.warning("janitor could not list Sprites", exc_info=True)
            return 0
        for name in names:
            if name not in owned:
                self._teardown(name)
                removed += 1
        if removed:
            log.warning("janitor removed %s stale generation Sprite(s)", removed)
        return removed

    def startup(self) -> None:
        """Run once when the Courthouse process starts (every wake from sleep)."""
        if not self.cfg.on_demand:
            return
        if self._get("phase"):
            self._set("phase", "")
            self._set("ended_at", _now().isoformat())
            self._set("error", "The last life was interrupted when the Courthouse restarted.")
            if self._get("gen"):
                self._set("last_gen", self._get("gen"))
        self.janitor()
