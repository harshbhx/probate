"""Run a whole family quickly in the fake world, for local development and the UI.

    python -m probate.courthouse.simulate --generations 12

Every number this produces is from a simulation and is labelled that way in the UI
(settings key `mode=simulation`). Never present it as a live run.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime, timedelta

from probate.adapters import world
from probate.common.config import Settings
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost
from probate.courthouse.store import Store


def run(
    generations: int,
    start: datetime,
    lifespan_s: int = 86400,
    reset: bool = True,
    leave_last_alive: bool = True,
) -> Store:
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = lifespan_s
    if reset and cfg.data_dir.exists():
        shutil.rmtree(cfg.data_dir)
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    store.set_setting("mode", "simulation")
    fam = Family(cfg, store, w, LocalHost(cfg, w))
    for i in range(generations):
        born = start + timedelta(seconds=lifespan_s * i)
        if leave_last_alive and i == generations - 1:
            g = fam.birth(born)
            from probate.suite import runner

            runner.send_all(w.mail, cfg, g.gen, born, lifespan_s, store)
            fam.host.tick(g.sprite)
            break
        g = fam.live_fast(born)
        print(
            f"Gen {g.gen:>2} {g.name:<8} resisted {g.attacks_resisted}/{g.attacks_met}  "
            f"will {g.items_willed:>2}: {g.items_approved} ok, {g.items_convicted} convicted, "
            f"{g.items_contested} contested  | {g.cause_of_death}"
        )
    print(f"Genome: {[i.name for i in store.genome()]}")
    return store


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=12)
    ap.add_argument("--start", default=None, help="ISO date of Gen 1's birth (default: N days ago)")
    args = ap.parse_args()
    start = (
        datetime.fromisoformat(args.start)
        if args.start
        else datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        - timedelta(days=args.generations - 1)
    )
    run(args.generations, start)


if __name__ == "__main__":
    main()
