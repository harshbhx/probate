"""SQLite index on the Courthouse. Box holds the archive; this drives the UI and the scheduler."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from probate.common.models import Generation, Instinct, Judgement, MemoryItem

SCHEMA = Path(__file__).with_name("schema.sql")


def now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        # One connection is shared by request threads, the life thread and the webhook worker.
        # Interleaving statements on it fails with "another row available", so serialise.
        self.lock = threading.RLock()
        self.db.executescript(SCHEMA.read_text(encoding="utf-8"))

    def q(self, sql: str, *args) -> list[sqlite3.Row]:
        with self.lock:
            return list(self.db.execute(sql, args))

    def one(self, sql: str, *args) -> sqlite3.Row | None:
        rows = self.q(sql, *args)
        return rows[0] if rows else None

    def x(self, sql: str, *args) -> None:
        with self.lock:
            self.db.execute(sql, args)
            self.db.commit()

    # settings
    def get_setting(self, key: str, default: str = "") -> str:
        row = self.one("SELECT value FROM settings WHERE key=?", key)
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.x(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            key,
            value,
        )

    # generations
    def save_generation(self, g: Generation) -> None:
        d = g.model_dump(mode="json")
        d["new_instinct_at_birth"] = int(g.new_instinct_at_birth)
        cols = ",".join(d)
        marks = ",".join("?" for _ in d)
        updates = ",".join(f"{k}=excluded.{k}" for k in d if k != "gen")
        # Column names come from the Generation model, never from input; values are bound.
        self.x(
            f"INSERT INTO generations({cols}) VALUES({marks}) ON CONFLICT(gen) DO UPDATE SET {updates}",  # nosec B608
            *d.values(),
        )

    def generation(self, gen: int) -> Generation | None:
        row = self.one("SELECT * FROM generations WHERE gen=?", gen)
        return self._gen(row) if row else None

    def generations(self) -> list[Generation]:
        return [self._gen(r) for r in self.q("SELECT * FROM generations ORDER BY gen")]

    def living(self) -> Generation | None:
        row = self.one(
            "SELECT * FROM generations WHERE state IN ('born','living','dying') ORDER BY gen DESC LIMIT 1"
        )
        return self._gen(row) if row else None

    def _gen(self, row: sqlite3.Row) -> Generation:
        fields = set(Generation.model_fields)
        d = {k: row[k] for k in row.keys() if k in fields}  # noqa: SIM118 - sqlite3.Row
        d["new_instinct_at_birth"] = bool(d.get("new_instinct_at_birth"))
        return Generation(**d)

    def set_gen_json(self, gen: int, column: str, value: dict) -> None:
        if column not in ("evidence_json", "baseline_json"):
            raise ValueError(f"not a JSON column: {column}")
        self.x(f"UPDATE generations SET {column}=? WHERE gen=?", json.dumps(value), gen)  # nosec B608

    def gen_json(self, gen: int, column: str) -> dict | None:
        if column not in ("evidence_json", "baseline_json"):
            raise ValueError(f"not a JSON column: {column}")
        row = self.one(f"SELECT {column} FROM generations WHERE gen=?", gen)  # nosec B608
        return json.loads(row[column]) if row and row[column] else None

    # will items and judgements
    def save_item(
        self, it: MemoryItem, fixture_id: str | None = None, gloss: str | None = None
    ) -> None:
        self.x(
            "INSERT OR REPLACE INTO will_items(item_id,gen,created_at,category,text,language,gloss_en,source,"
            "source_ref,evidence,fixture_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            it.id,
            it.gen,
            it.created_at.isoformat(),
            it.category.value,
            it.text,
            it.language,
            gloss,
            it.source.value,
            it.source_ref,
            it.evidence,
            fixture_id,
        )

    def save_judgement(self, j: Judgement) -> None:
        self.x(
            "INSERT OR REPLACE INTO judgements(item_id,gen,layer1_flags,jev_answers,verdict,reason,new_instinct)"
            " VALUES(?,?,?,?,?,?,?)",
            j.item_id,
            j.gen,
            json.dumps(j.layer1_flags),
            json.dumps({k: v.model_dump() for k, v in j.jev_answers.items()}),
            j.verdict.value,
            j.reason,
            j.new_instinct,
        )

    def judged(self, item_id: str) -> bool:
        return self.one("SELECT 1 FROM judgements WHERE item_id=?", item_id) is not None

    # instincts
    def genome(self) -> list[Instinct]:
        return [
            Instinct(
                name=r["name"],
                question=r["question"],
                threshold=r["threshold"],
                born_from=r["born_from"],
                added_in_gen=r["added_in_gen"],
                lore=r["lore"],
            )
            for r in self.q("SELECT * FROM instincts WHERE active=1 ORDER BY added_in_gen, rowid")
        ]

    def add_instinct(self, i: Instinct) -> None:
        self.x(
            "INSERT OR IGNORE INTO instincts(name,question,threshold,born_from,added_in_gen,lore) VALUES(?,?,?,?,?,?)",
            i.name,
            i.question,
            i.threshold,
            i.born_from,
            i.added_in_gen,
            i.lore,
        )

    # events
    def event(self, gen: int | None, kind: str, text: str, ts: str | None = None) -> None:
        self.x("INSERT INTO events(ts,gen,kind,text) VALUES(?,?,?,?)", ts or now(), gen, kind, text)
