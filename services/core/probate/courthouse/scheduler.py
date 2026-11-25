"""The Courthouse clock: every 15 seconds, move the family one step forward.

Real time, real or fake world. The simulator (`simulate.py`) skips the clock entirely.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from probate.courthouse.family import Family
from probate.suite import runner

log = logging.getLogger("probate.scheduler")
TICK_SECONDS = 15


class Scheduler:
    def __init__(self, family: Family) -> None:
        self.family = family
        self.store = family.store
        self.last_tick = None

    def step(self, now: datetime | None = None) -> str:
        now = now or datetime.now(UTC)
        if self.last_tick is not None:
            # The Courthouse is awake while the clock runs; cap the gap so a restart isn't billed.
            gap = (now - self.last_tick).total_seconds()
            self.family.budget.charge_courthouse(min(max(gap, 0), 4 * TICK_SECONDS))
        self.last_tick = now
        try:
            self.family.read_court_replies()
        except Exception:
            log.warning("reading court replies failed; will retry next tick", exc_info=True)
        if self.store.get_setting("paused", "0") == "1":
            return "paused"
        living = self.store.living()
        if living:
            if living.state == "dying":
                return "dying"
            if living.dies_at and now >= living.dies_at:
                g = self.family.death(living, now)
                self.family.trial(g)
                return f"died:{g.gen}"
            self.family.host.tick(living.sprite)
            return f"living:{living.gen}"
        dead = [g for g in self.store.generations() if g.died_at]
        if dead and now < dead[-1].died_at + timedelta(seconds=self.family.cfg.gap_seconds):
            return "waiting"
        unfinished = [g for g in self.store.generations() if g.state == "dead"]
        for g in unfinished:  # a trial interrupted by a restart
            self.family.trial(g)
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
        self.store.set_setting("resting", "")
        g = self.family.birth(now)
        runner.send_all(
            self.family.w.mail,
            self.family.cfg,
            g.gen,
            now,
            self.family.cfg.lifespan_seconds,
            self.store,
        )
        return f"born:{g.gen}"

    async def run(self) -> None:
        while True:
            try:
                state = await asyncio.to_thread(self.step)
                log.info("tick %s", state)
            except Exception:
                log.exception("tick failed")
                self.store.event(
                    None, "error", "The Courthouse clock stumbled; it will try again in 15 seconds."
                )
            await asyncio.sleep(TICK_SECONDS)
