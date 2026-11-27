"""The Courthouse clock: every 15 seconds, move the family one step forward.

Real time, real or fake world. The simulator (`simulate.py`) skips the clock entirely.
"""

from __future__ import annotations

import asyncio
import logging
import re
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
    def __init__(self, family: Family) -> None:
        self.family = family
        self.store = family.store
        self.last_tick = None

    def step(self, now: datetime | None = None, allow_birth: bool = True) -> str:
        # The clock thread and the admin routes share one lock: no double birth, death or trial.
        with self.family.lifecycle_lock:
            return self._step(now, allow_birth)

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
        living = self.store.living()
        if living:
            # A death that failed partway (a dropped connection, a Sprite that would not answer)
            # leaves the generation "dying". It is tried again on the next tick, not left forever.
            if living.state == "dying" or (living.dies_at and now >= living.dies_at):
                g = self.family.death(living, now)
                self.try_trial(g, now)
                return f"died:{g.gen}"
            self.ensure_suite(living, now)
            self.family.host.tick(living.sprite)
            return f"living:{living.gen}"
        dead = [g for g in self.store.generations() if g.died_at]
        if dead and now < dead[-1].died_at + timedelta(seconds=self.family.cfg.gap_seconds):
            return "waiting"
        unfinished = [g for g in self.store.generations() if g.state == "dead"]
        for g in unfinished:  # a trial interrupted by a restart
            self.try_trial(g, now)
        if not allow_birth:
            return "idle"  # on-demand mode: only a visitor's request starts a life
        if self.store.get_setting("paused", "0") == "1":
            return "paused"  # the living finish their lives; no one new is born
        if self.family.budget.exhausted():
            if self.store.get_setting("resting", "") != "budget":
                self.store.set_setting("resting", "budget")
                self.store.event(
                    None,
                    "resting",
                    "The family is resting to save money. No one will be born until the budget "
                    "is raised.",
                )
            return "resting:budget"
        quota = self.family.quota
        need = runner.agentmail_sends(self.family.cfg, self.family.next_number())
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
            return "resting:mail"
        self.store.set_setting("resting", "")
        retry_at = self.store.get_setting("birth_retry_at", "")
        if retry_at and now < datetime.fromisoformat(retry_at):
            return "waiting:birth-backoff"
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
        return f"born:{g.gen}"

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

    async def run(self) -> None:
        while True:
            try:
                state = await asyncio.to_thread(self.step)
                log.info("tick %s", state)
            except Exception as exc:
                log.exception("tick failed")
                self.store.event(
                    None,
                    "error",
                    f"The Courthouse clock stumbled ({brief(exc)}); it will try again in 15 seconds.",
                )
            await asyncio.sleep(TICK_SECONDS)
