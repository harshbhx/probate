"""The Courthouse clock: every 15 seconds, move the family one step forward.

Real time, real or fake world. The simulator (`simulate.py`) skips the clock entirely.
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

from probate.courthouse.family import Family
from probate.suite import runner

log = logging.getLogger("probate.scheduler")
TICK_SECONDS = 15
MAX_TRIAL_ATTEMPTS = 3  # then the will is left unjudged: nothing in it is inherited
TRIAL_BACKOFF_SECONDS = 60  # doubles with each failed attempt
BIRTH_BACKOFF_SECONDS = 120  # doubles with each failed birth, capped below
MAX_BIRTH_BACKOFF_SECONDS = 1800
MAX_SUITE_ATTEMPTS = 3  # a life's test emails are retried on later ticks, then given up on
LEASE_NAME = "clock"
LEASE_SECONDS = 45  # a clock process that stops renewing loses the clock after this long
LEASE_RENEW_SECONDS = 10
# A birth waits for the previous generation's trial (its instincts are inherited), but not for
# longer than this; the trial carries on and its instincts reach the lives after.
TRIAL_WAIT_MAX_SECONDS = 600
FIRST_MAIL_SECONDS = 60  # a life this old that has read no mail, though mail was sent, is restarted
RECONCILE_EVERY_TICKS = 20  # the Sprite sweep runs this often (20 ticks of 15 s = every 5 minutes)
STRAY = re.compile(
    r"gen-(\d{3,})-[a-z0-9-]+"
)  # only a Sprite named like a generation is ever swept
ADMIN_TICK_WAIT_SECONDS = 8  # POST /admin/tick answers after this long, whatever the step is doing


def brief(exc: BaseException) -> str:
    """The error's type and first line, short enough for the public event feed.

    Long runs of letters and digits (tokens, ids, encoded bodies) are cut so nothing sensitive
    reaches the feed.
    """
    first = str(exc).splitlines()[0] if str(exc) else ""
    first = re.sub(r"[A-Za-z0-9_\-]{24,}", "…", first)
    first = re.sub(r"\?\S*", "", first)  # drop query strings from URLs
    return f"{type(exc).__name__}: {first[:140]}" if first else type(exc).__name__


class Scheduler:
    def __init__(self, family: Family, background_trials: bool = False) -> None:
        self.family = family
        self.store = family.store
        self.last_tick = None
        # With background trials a trial runs on its own thread outside the lifecycle lock, so
        # ticks, births and /admin/tick are not held for minutes. Off by default: a trial then
        # runs inside the step, which is what the simulator and the tests rely on.
        self.background_trials = background_trials
        self._trials: dict[int, tuple[threading.Thread, float]] = {}
        self._trials_lock = threading.Lock()
        self.owner = uuid.uuid4().hex[:8]  # this process's name on the clock lease
        self.lease_on = False  # True once run() claims the clock: step() then needs the lease
        self.holding = False
        self.state = "idle"
        self.detail = ""
        self.state_since = datetime.now(UTC)
        self._announced: set[str] = set()
        self._tick_thread: threading.Thread | None = None
        self._ticks = 0

    # ------------------------------------------------------------------ what the clock says
    def note(self, state: str, detail: str = "") -> str:
        """Remember and log what the clock is doing, one line per tick."""
        if state != self.state:
            self.state_since = datetime.now(UTC)
        self.state, self.detail = state, detail
        log.info("tick %s%s", state, f" ({detail})" if detail else "")
        return state

    def announce(self, key: str, gen: int | None, text: str) -> None:
        """A wait worth showing in the public feed, once per reason."""
        if key not in self._announced:
            self._announced.add(key)
            self.store.event(gen, "life", text)

    def describe(self) -> dict:
        return {
            "state": self.state,
            "detail": self.detail,
            "since": self.state_since.isoformat(),
            "lease_held": self.holding if self.lease_on else None,
            "trials_running": [g for g, _age in self.trials_running()],
        }

    def step(self, now: datetime | None = None, allow_birth: bool = True) -> str:
        if self.lease_on and not self.holding:
            return self.note("standby:lease", "another Courthouse process holds the clock")
        # The clock thread and the admin routes share one lock: no double birth, death or trial.
        with self.family.lifecycle_lock:
            return self._step(now, allow_birth)

    def tick_now(self, wait: float = ADMIN_TICK_WAIT_SECONDS) -> dict:
        """One step for POST /admin/tick: answer within `wait` seconds even if the step (a death,
        a birth) takes longer; it carries on in the background and the state says so."""
        out: dict = {}
        with self._trials_lock:
            busy = self._tick_thread is not None and self._tick_thread.is_alive()
            if not busy:

                def work() -> None:
                    try:
                        out["state"] = self.step()
                    except Exception as exc:
                        out["error"] = exc
                        log.exception("admin tick failed")

                self._tick_thread = threading.Thread(target=work, daemon=True, name="admin-tick")
                self._tick_thread.start()
            thread = self._tick_thread
        if busy:
            return {"state": "running", "clock": self.describe()}
        thread.join(wait)
        if thread.is_alive():
            return {"state": "running", "clock": self.describe()}
        if "error" in out:
            raise out["error"]
        return {"state": out["state"], "clock": self.describe()}

    # ------------------------------------------------------------------ trials
    def trials_running(self) -> list[tuple[int, float]]:
        with self._trials_lock:
            return [
                (g, time.monotonic() - t0) for g, (th, t0) in self._trials.items() if th.is_alive()
            ]

    def start_trial(self, g, now: datetime | None = None) -> None:
        """Hold the trial now (default) or, with background trials, on its own thread."""
        if not self.background_trials:
            self.try_trial(g, now)
            return
        with self._trials_lock:
            old = self._trials.get(g.gen)
            if old and old[0].is_alive():
                return

            def work() -> None:
                try:
                    self.try_trial(g, now)
                except Exception:
                    log.exception("trial of gen %s crashed", g.gen)

            th = threading.Thread(target=work, daemon=True, name=f"trial-{g.gen}")
            self._trials[g.gen] = (th, time.monotonic())
            th.start()

    def try_trial(self, g, now: datetime | None = None) -> bool:
        """Hold the trial; a trial that keeps failing backs off and is finally given up on, so it
        can neither block births nor repeat its emails and model calls every tick."""
        now = now or datetime.now(UTC)
        key, retry_key = f"trial_attempts:{g.gen}", f"trial_retry_at:{g.gen}"
        retry_at = self.store.get_setting(retry_key, "")
        if retry_at and now < datetime.fromisoformat(retry_at):
            return False
        try:
            self.family.trial(g)
            return True
        except Exception as exc:
            n = int(self.store.get_setting(key, "0") or 0) + 1
            self.store.set_setting(key, str(n))
            log.exception("trial of gen %s failed (attempt %s)", g.gen, n)
            if n >= MAX_TRIAL_ATTEMPTS:
                cur = self.store.generation(g.gen)
                cur.state = "tried"
                self.store.save_generation(cur)
                self.store.event(
                    g.gen,
                    "error",
                    f"The court could not finish {g.name}'s trial after {n} tries "
                    f"({type(exc).__name__}). Nothing from that will is inherited.",
                )
                return False
            wait = TRIAL_BACKOFF_SECONDS * 2 ** (n - 1)
            self.store.set_setting(retry_key, (now + timedelta(seconds=wait)).isoformat())
            self.store.event(
                g.gen,
                "error",
                f"The court hit a problem in {g.name}'s trial (attempt {n} of "
                f"{MAX_TRIAL_ATTEMPTS}, {type(exc).__name__}); it will try again in {wait} seconds.",
            )
            return False

    def _step(self, now: datetime | None, allow_birth: bool) -> str:
        now = now or datetime.now(UTC)
        if self.last_tick is not None:
            # The Courthouse is awake while the clock runs; cap the gap so a restart isn't billed.
            gap = (now - self.last_tick).total_seconds()
            self.family.budget.charge_courthouse(min(max(gap, 0), 4 * TICK_SECONDS))
        self.last_tick = now
        if self.family.hooks is not None:
            self.family.hooks.kick()  # due retries go out while we are awake anyway
        try:
            self.family.read_court_replies()
        except Exception:
            log.warning("reading court replies failed; will retry next tick", exc_info=True)
        self._ticks += 1
        if allow_birth and self._ticks % RECONCILE_EVERY_TICKS == 1:
            self.reconcile_sprites()
        living = self.store.living()
        if living:
            # A death that failed partway (a dropped connection, a Sprite that would not answer)
            # leaves the generation "dying". It is tried again on the next tick, not left forever.
            if living.state == "dying" or (living.dies_at and now >= living.dies_at):
                g = self.family.death(living, now)
                self.start_trial(g, now)
                return self.note(f"died:{g.gen}", "the trial follows")
            self.ensure_suite(living, now)
            st = self.family.host.tick(living.sprite)
            if isinstance(st, dict) and st.get("restarted"):
                self.store.event(
                    living.gen,
                    "error",
                    f"{living.name}'s agent had stopped reading mail for {st.get('loop_age')} "
                    "seconds; the Courthouse restarted it.",
                )
            else:
                self.watch_first_mail(living, st, now)
            return self.note(f"living:{living.gen}")
        dead = [g for g in self.store.generations() if g.died_at]
        if dead and now < dead[-1].died_at + timedelta(seconds=self.family.cfg.gap_seconds):
            until = dead[-1].died_at + timedelta(seconds=self.family.cfg.gap_seconds)
            self.note(
                "waiting", f"gap after gen {dead[-1].gen}'s death, until {until:%H:%M:%S} UTC"
            )
            return "waiting"
        unfinished = [g for g in self.store.generations() if g.state == "dead"]
        for g in unfinished:  # a trial interrupted by a restart
            self.start_trial(g, now)
        if not allow_birth:
            return "idle"  # on-demand mode: only a visitor's request starts a life
        if self.store.get_setting("paused", "0") == "1":
            return self.note("paused", "no one is born until resume")
        running = self.trials_running()
        if running:
            gen_, age = max(running, key=lambda r: r[1])
            if age < TRIAL_WAIT_MAX_SECONDS:
                self.announce(
                    f"trial-wait:{gen_}",
                    gen_,
                    f"The next birth waits for gen {gen_}'s trial to finish: its instincts are "
                    "inherited.",
                )
                return self.note(
                    "waiting:trial",
                    f"birth waits for the trial of gen {gen_}, running {age:.0f}s of at most "
                    f"{TRIAL_WAIT_MAX_SECONDS}s",
                )
            self.announce(
                f"trial-gave-up:{gen_}",
                gen_,
                f"Gen {gen_}'s trial is still running after {TRIAL_WAIT_MAX_SECONDS} seconds; the "
                "next birth no longer waits for it.",
            )
            log.warning("birth no longer waits for the trial of gen %s (%.0fs)", gen_, age)
        if self.family.budget.exhausted():
            if self.store.get_setting("resting", "") != "budget":
                self.store.set_setting("resting", "budget")
                self.store.event(
                    None,
                    "resting",
                    "The family is resting to save money. No one will be born until the budget "
                    "is raised.",
                )
            return self.note("resting:budget", "the budget is used up")
        quota = self.family.quota
        need = runner.agentmail_sends(self.family.cfg, self.family.next_number(), self.store)
        if not quota.room_for(need, now):
            mark = f"mail:{now.astimezone(UTC):%Y-%m-%d}"
            if self.store.get_setting("resting", "") != mark:
                self.store.set_setting("resting", mark)
                self.store.event(
                    None,
                    "resting",
                    f"The family is waiting for tomorrow's mail: AgentMail's daily limit has "
                    f"{quota.left(now)} sends left, and a life needs {need + quota.reserve}. "
                    "The next birth is at 00:00 UTC.",
                )
            return self.note(
                "resting:mail", f"{quota.left(now)} AgentMail sends left, a life needs {need}"
            )
        self.store.set_setting("resting", "")
        retry_at = self.store.get_setting("birth_retry_at", "")
        if retry_at and now < datetime.fromisoformat(retry_at):
            return self.note("waiting:birth-backoff", f"retry at {retry_at}")
        self.set_aside_stale_mail()
        try:
            g = self.family.birth(now)
        except Exception:
            n = int(self.store.get_setting("birth_failures", "0") or 0) + 1
            self.store.set_setting("birth_failures", str(n))
            wait = min(BIRTH_BACKOFF_SECONDS * 2 ** (n - 1), MAX_BIRTH_BACKOFF_SECONDS)
            self.store.set_setting("birth_retry_at", (now + timedelta(seconds=wait)).isoformat())
            raise
        self.store.set_setting("birth_failures", "0")
        self.store.set_setting("birth_retry_at", "")
        self.ensure_suite(g, now)
        return self.note(f"born:{g.gen}")

    def watch_first_mail(self, g, st, now: datetime) -> None:
        """A life that is FIRST_MAIL_SECONDS old and has read no mail although its test emails
        went out has an agent that is not running (generation 1 of the staging test). Restart it,
        once per life, and say so."""
        key = f"mail_watch:{g.gen}"
        if self.store.get_setting(key, "") or not isinstance(st, dict) or st.get("emails"):
            return
        restart = getattr(self.family.host, "restart_agent", None)
        if not g.born_at or restart is None:
            return
        age = (now - g.born_at).total_seconds()
        row = self.store.one(
            "SELECT COUNT(*) AS n FROM suite_runs WHERE gen=? AND message_id IS NOT NULL", g.gen
        )
        sent = row["n"] if row else 0
        if age < FIRST_MAIL_SECONDS or not sent:
            return
        self.store.set_setting(key, "1")
        log.warning(
            "%s has read no mail in %.0fs with %s emails sent; restarting its agent",
            g.name,
            age,
            sent,
        )
        try:
            restart(g.sprite)
        except Exception as exc:  # noqa: BLE001 - say so in the feed; the next life is unaffected
            self.store.event(
                g.gen, "error", f"{g.name} has read no mail and the restart failed ({brief(exc)})."
            )
            return
        self.store.event(
            g.gen,
            "error",
            f"{g.name} had read no mail {age:.0f} seconds after birth, although {sent} test "
            "emails were sent; the Courthouse restarted the agent.",
        )

    def reconcile_sprites(self) -> int:
        """Delete generation Sprites that no open life owns, so none is left billing.

        A delete that failed (a Sprites outage during a death or a failed birth) used to leave its
        Sprite running for good. This lists the generation Sprites and deletes each one whose
        generation is not born, living or dying. Only names shaped like `gen-NNN-name` are ever
        touched. Returns how many it deleted.
        """
        try:
            names = self.family.host.list_sprites()
        except Exception:
            log.warning("could not list Sprites to look for strays", exc_info=True)
            return 0
        with self.family.lifecycle_lock:  # no birth can start while we decide what is a stray
            rows = self.store.generations()
            keep = {g.sprite for g in rows if g.state in ("born", "living", "dying")}
            closed = {
                g.sprite: g.gen
                for g in rows
                if g.state in ("dead", "died_early", "tried")
                # A birth refused because the name was another environment's Sprite does not own it.
                and not self.store.get_setting(f"foreign_sprite:{g.gen}", "")
            }
            removed = 0
            for name in names:
                if not STRAY.fullmatch(name) or name in keep:
                    continue
                if name not in closed:
                    # Another Courthouse in the same org names its Sprites the same way: a name no
                    # row of this database owns is never ours to delete.
                    log.warning("foreign or unknown Sprite %s, not deleted", name)
                    self.announce(
                        f"foreign:{name}", None, f"Foreign or unknown Sprite {name}, not deleted."
                    )
                    continue
                try:
                    self.family.host.force_destroy(name)
                except Exception:
                    log.warning("could not delete the stray Sprite %s", name, exc_info=True)
                    continue
                removed += 1
                log.warning("deleted the stray Sprite %s: its life had closed", name)
                self.store.event(
                    closed[name],
                    "error",
                    f"Deleted a leftover Sprite ({name}) whose generation had closed.",
                )
                self.family.emit(
                    "sprite.stray_deleted", {"sprite": name}, f"stray:{name}:{self._ticks}"
                )
        return removed

    def recover_orphans(self) -> int:
        """A generation still 'born' when this process takes the clock was being born by a
        process that stopped (a deploy restarted the service mid-birth). Its Sprite may be
        half installed, so it is deleted and the row closed; the next birth starts clean."""
        n = 0
        with self.family.lifecycle_lock:
            for g in self.store.generations():
                if g.state != "born":
                    continue
                try:
                    self.family.host.force_destroy(g.sprite)
                except Exception:
                    # Keep the row open: it is retried at the next start, and the sweep deletes the
                    # Sprite meanwhile. Closing it would hide the leak.
                    log.warning("could not delete the half-born Sprite %s", g.sprite, exc_info=True)
                    continue
                g.state = "died_early"
                self.store.set_setting(
                    "birth_skipped", str(int(self.store.get_setting("birth_skipped", "0") or 0) + 1)
                )
                self.store.save_generation(g)
                self.store.event(
                    g.gen,
                    "error",
                    f"{g.name}'s birth was cut short when the Courthouse restarted; the Sprite "
                    "was deleted and the next life starts clean.",
                )
                n += 1
        return n

    def set_aside_stale_mail(self) -> int:
        """Before a birth, set aside test emails no earlier generation read.

        Leftovers used to reach the next child: generation 12 of the real run read 12 emails
        while only 2 were sent to it. They count for no one, so they are marked read. Judge mail
        and the owner's court replies have no fixture header and are left alone.
        """
        mail = self.family.w.mail
        inbox = self.family.cfg.family_inbox

        def stale_mail() -> list:
            return [
                m
                for m in mail.list_new(inbox)
                if any(k.lower() == "x-probate-fixture" for k in (m.headers or {}))
            ]

        try:
            stale = stale_mail()
            for m in stale:
                mail.mark_read(m.inbox, m.id)
            left = stale_mail() if stale else []  # a label that did not stick shows up again
        except Exception:
            log.warning("could not set aside old test mail", exc_info=True)
            return 0
        if stale:
            self.store.event(
                None,
                "life",
                f"Set aside {len(stale) - len(left)} test emails no one read, so they count for no one.",
            )
        if left:
            log.warning("%s old test emails are still unlabeled after marking them read", len(left))
            self.store.event(
                None,
                "error",
                f"{len(left)} old test emails could not be marked read and may reach the next "
                "life; they will be tried again before the next birth.",
            )
        return len(stale) - len(left)

    def ensure_suite(self, g, now: datetime) -> None:
        """Send the living generation's test emails, once; retry what failed on later ticks.

        A birth that raised after the Sprite was up, or an email AgentMail refused, used to leave
        a life with no suite at all (generations 4 and 8 of the real run). Each call sends only
        what has not gone out yet.
        """
        if self.store.get_setting(f"suite_done:{g.gen}", "") == "1":
            return
        n = int(self.store.get_setting(f"suite_attempts:{g.gen}", "0") or 0) + 1
        self.store.set_setting(f"suite_attempts:{g.gen}", str(n))
        born = g.born_at or now
        span = (g.dies_at - born).total_seconds() if g.dies_at else None
        res = runner.send_all(
            self.family.w.mail,
            self.family.cfg,
            g.gen,
            born,
            int(span or self.family.cfg.lifespan_seconds),
            self.store,
        )
        if not res.failed:
            self.store.set_setting(f"suite_done:{g.gen}", "1")
            return
        fid, why = res.failed[0]
        last = n >= MAX_SUITE_ATTEMPTS
        if last:
            self.store.set_setting(f"suite_done:{g.gen}", "1")
        self.store.event(
            g.gen,
            "error",
            f"{len(res.failed)} test emails for {g.name} could not be sent (first: {fid}, {why}). "
            + (
                "Giving up: this life's results count only the emails that went out."
                if last
                else "They will be tried again on the next tick."
            ),
        )

    def claim(self) -> bool:
        return self.store.claim_lease(LEASE_NAME, self.owner, LEASE_SECONDS)

    async def _renew_lease(self) -> None:
        """Renew on its own task: a step can run for minutes and must not let the lease lapse."""
        while True:
            await asyncio.sleep(LEASE_RENEW_SECONDS)
            try:
                self.holding = await asyncio.to_thread(self.claim)
            except Exception:
                log.warning("could not renew the clock lease", exc_info=True)

    async def run(self) -> None:
        """Run the clock, but only while holding the lease: a second process on the same database
        (a deploy's double start) waits as a standby and takes over once the first has stopped."""
        self.lease_on = True
        renew = asyncio.create_task(self._renew_lease())
        had = False
        try:
            while True:
                try:
                    if not self.holding:
                        self.holding = await asyncio.to_thread(self.claim)
                        if not self.holding:
                            self.note("standby:lease", "another Courthouse process holds the clock")
                    if self.holding:
                        if not had:
                            had = True
                            log.info("this process now runs the clock (%s)", self.owner)
                            await asyncio.to_thread(self.recover_orphans)
                        await asyncio.to_thread(self.step)
                except Exception as exc:
                    log.exception("tick failed")
                    self.store.event(
                        None,
                        "error",
                        f"The Courthouse clock stumbled ({brief(exc)}); it will try again in 15 seconds.",
                    )
                await asyncio.sleep(TICK_SECONDS)
        finally:
            renew.cancel()
            self.lease_on = False
            self.holding = False
            try:
                self.store.release_lease(LEASE_NAME, self.owner)
            except Exception:
                log.warning("could not release the clock lease", exc_info=True)
