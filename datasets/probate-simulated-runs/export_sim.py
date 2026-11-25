"""Export a SIMULATED Probate run (PROBATE_FAKE=1 stand-in models) to JSONL.

    PROBATE_FAKE=1 PROBATE_DATA_DIR=/tmp/sim python -m probate.courthouse.simulate --generations 12
    python datasets/probate-simulated-runs/export_sim.py /tmp/sim/probate.db

Every row carries simulated=true. Refuses to export a database not marked mode=simulation.
Absolute timestamps, sprite names and voice ids are dropped. Standard library only.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "data"
GEN_COLS = [
    "gen", "name", "state", "cause_of_death", "epitaph", "obituary", "genome_size_at_birth",
    "new_instinct_at_birth", "emails_handled", "attacks_met", "attacks_resisted",
    "items_willed", "items_approved", "items_convicted", "items_contested",
]  # fmt: skip


def write(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps({"simulated": True, **r}, ensure_ascii=False) + "\n")
    print(f"wrote {name}: {len(rows)} rows")


def main(db_path: str) -> int:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    mode = con.execute("select value from settings where key='mode'").fetchone()
    if not mode or mode["value"] != "simulation":
        print("refusing: database is not marked mode=simulation")
        return 1
    gens = [
        {c: r[c] for c in GEN_COLS} for r in con.execute("select * from generations order by gen")
    ]
    for g in gens:
        g["state"] = {"tried": "completed"}.get(g["state"], g["state"])
    runs = [
        {
            "gen": r["gen"],
            "fixture_id": r["fixture_id"],
            "is_attack": bool(r["is_attack"]),
            "outcome": r["outcome"],
            "instinct": r["instinct"],
        }
        for r in con.execute("select * from suite_runs order by gen, fixture_id")
    ]
    write("generations.jsonl", gens)
    write("fixture_outcomes.jsonl", runs)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
