"""Where memories, trials and instincts live: one SQLite file (~/.probate-memory/memory.db).

Every call to remember() is a trial and leaves a row, whatever the verdict. Only approved rows are
ever returned by recall(). A conviction also becomes an instinct, so a lookalike is convicted on
sight.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from probate_memory.court import APPROVED, CONTESTED, CONVICTED, Instinct, Judgement, shingles

FORGOTTEN, REJECTED = "forgotten", "rejected"
SCHEMA = """
create table if not exists memories (
  id integer primary key,
  text text not null,
  source text not null,
  about text not null default '',
  status text not null,          -- approved | convicted | contested | rejected | forgotten
  reason text not null,
  flags text not null default '[]',
  jev text,
  instinct integer,
  created text not null,
  decided text
);
create table if not exists instincts (
  id integer primary key,
  from_memory integer not null,
  shingles text not null,
  summary text not null,
  created text not null
);
"""


def default_path() -> Path:
    return Path(os.environ.get("PROBATE_MEMORY_DB", Path.home() / ".probate-memory" / "memory.db"))


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Memory:
    id: int
    text: str
    source: str
    about: str
    status: str
    reason: str
    flags: list[str]
    created: str

    def public(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "about": self.about,
            "status": self.status,
            "reason": self.reason,
            "flags": self.flags,
            "created": self.created,
        }


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class Store:
    def __init__(self, path: Path | str | None = None, vectors=None):
        # Optional recall by meaning (pinecone.py). Holds approved memories only.
        self.vectors = vectors
        self.path = Path(path) if path else default_path()
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # trials

    def record(self, text: str, source: str, about: str, j: Judgement) -> Memory:
        jev = json.dumps({k: [a.value, a.confidence] for k, a in j.jev.items()}) if j.jev else None
        cur = self.db.execute(
            "insert into memories (text, source, about, status, reason, flags, jev, instinct,"
            " created) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                text,
                source,
                about,
                j.verdict,
                j.reason,
                json.dumps(j.flags),
                jev,
                j.instinct,
                _now(),
            ),
        )
        mid = cur.lastrowid
        if j.verdict == CONVICTED and j.instinct is None:
            summary = (j.flags[0].replace("_", " ") if j.flags else j.reason.split(":")[0]).strip()
            self.db.execute(
                "insert into instincts (from_memory, shingles, summary, created)"
                " values (?, ?, ?, ?)",
                (mid, json.dumps(sorted(shingles(text))), summary, _now()),
            )
        self.db.commit()
        if j.verdict == APPROVED:
            self._index(mid, text, about, source)
        return self.get(mid)  # type: ignore[return-value]

    def _index(self, mid: int, text: str, about: str, source: str) -> None:
        if self.vectors is None:
            return
        from probate_memory.pinecone import VectorsUnavailable

        try:
            self.vectors.upsert(mid, text, about, source)
        except VectorsUnavailable:
            pass  # word search still finds it; the court's record is in SQLite either way

    def get(self, mid: int) -> Memory | None:
        r = self.db.execute("select * from memories where id = ?", (mid,)).fetchone()
        return self._mem(r) if r else None

    def trials(self, limit: int = 20, status: str | None = None) -> list[Memory]:
        q, args = "select * from memories", []
        if status:
            q, args = q + " where status = ?", [status]
        rows = self.db.execute(q + " order by id desc limit ?", [*args, limit]).fetchall()
        return [self._mem(r) for r in rows]

    def instincts(self) -> list[Instinct]:
        rows = self.db.execute("select * from instincts order by id").fetchall()
        return [Instinct(r["id"], frozenset(json.loads(r["shingles"])), r["summary"]) for r in rows]

    def counts(self) -> dict[str, int]:
        out = {s: 0 for s in (APPROVED, CONVICTED, CONTESTED, REJECTED, FORGOTTEN)}
        for r in self.db.execute("select status, count(*) n from memories group by status"):
            out[r["status"]] = r["n"]
        out["instincts"] = self.db.execute("select count(*) from instincts").fetchone()[0]
        return out

    # the owner's decisions (CLI only, never an agent tool)

    def decide(self, mid: int, approve: bool) -> Memory:
        m = self.get(mid)
        if not m:
            raise KeyError(f"No memory {mid}")
        if m.status != CONTESTED:
            raise ValueError(f"Memory {mid} is {m.status}, not waiting for a decision")
        status = APPROVED if approve else REJECTED
        reason = m.reason + (" Approved by the owner." if approve else " Rejected by the owner.")
        self.db.execute(
            "update memories set status = ?, reason = ?, decided = ? where id = ?",
            (status, reason, _now(), mid),
        )
        self.db.commit()
        if approve:
            self._index(mid, m.text, m.about, m.source)
        return self.get(mid)  # type: ignore[return-value]

    # what agents can do with approved memories

    def forget(self, mid: int) -> bool:
        cur = self.db.execute(
            "update memories set status = ?, decided = ? where id = ? and status = ?",
            (FORGOTTEN, _now(), mid, APPROVED),
        )
        self.db.commit()
        if cur.rowcount == 1 and self.vectors is not None:
            from probate_memory.pinecone import VectorsUnavailable

            try:
                self.vectors.delete(mid)
            except VectorsUnavailable:
                pass  # recall re-checks the status in SQLite, so a forgotten memory never returns
        return cur.rowcount == 1

    def recall(self, query: str, limit: int = 5) -> list[tuple[Memory, float]]:
        """Approved memories for a query: by meaning through Pinecone when it is set up, otherwise
        (or if it fails) ranked by BM25. Every hit is re-checked against SQLite, so only memories
        that are approved right now come back."""
        if self.vectors is not None and _words(query):
            from probate_memory.pinecone import VectorsUnavailable

            try:
                hits = self.vectors.search(query, limit * 2)
            except VectorsUnavailable:
                hits = None
            if hits is not None:
                out = []
                for mid, score in hits:
                    m = self.get(mid)
                    if m and m.status == APPROVED:
                        out.append((m, score))
                if out:
                    return out[:limit]
        return self._recall_words(query, limit)

    def _recall_words(self, query: str, limit: int) -> list[tuple[Memory, float]]:
        rows = [
            self._mem(r)
            for r in self.db.execute(
                "select * from memories where status = ? order by id desc", (APPROVED,)
            )
        ]
        q = _words(query)
        if not q:
            return [(m, 0.0) for m in rows[:limit]]
        docs = [_words(m.text + " " + m.about) for m in rows]
        n = len(docs) or 1
        avg = sum(map(len, docs)) / n or 1
        df = Counter(w for d in docs for w in set(d))
        scored = []
        for m, d in zip(rows, docs, strict=True):
            tf = Counter(d)
            s = 0.0
            for w in set(q):
                if w not in tf:
                    continue
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * len(d) / avg))
            if s > 0:
                scored.append((m, round(s, 3)))
        scored.sort(key=lambda x: -x[1])
        return scored[:limit]

    @staticmethod
    def _mem(r: sqlite3.Row) -> Memory:
        return Memory(
            r["id"],
            r["text"],
            r["source"],
            r["about"],
            r["status"],
            r["reason"],
            json.loads(r["flags"]),
            r["created"],
        )
