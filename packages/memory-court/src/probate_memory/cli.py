"""probate-memory: run the MCP server, and decide contested memories as the owner.

probate-memory serve                 run the MCP server over stdio (what an MCP client starts)
probate-memory check "text" --source web    a dry-run trial: nothing is saved
probate-memory waiting               memories waiting for your decision
probate-memory approve ID | reject ID
probate-memory list                  approved memories
probate-memory trials                recent trials, every verdict
probate-memory instincts             tricks the court has learned to recognise
"""

from __future__ import annotations

import argparse
import json
import sys

from probate_memory import __version__
from probate_memory.config import owner_from_env
from probate_memory.court import CONTESTED, SOURCES, judge
from probate_memory.ollama import second_judge_from_env
from probate_memory.pinecone import PineconeRecall
from probate_memory.store import APPROVED, Store


def _line(m) -> str:
    text = m.text if len(m.text) <= 100 else m.text[:97] + "..."
    return f"{m.id:>5}  {m.status:<10} {m.source:<15} {text}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="probate-memory", description="Memory with a court, for any AI agent."
    )
    p.add_argument(
        "--db", help="SQLite file (default: $PROBATE_MEMORY_DB or ~/.probate-memory/memory.db)"
    )
    p.add_argument("--version", action="version", version=f"probate-memory {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve", help="run the MCP server over stdio")
    c = sub.add_parser("check", help="a dry-run trial; nothing is saved")
    c.add_argument("text")
    c.add_argument("--source", choices=SOURCES, default="unknown_sender")
    sub.add_parser("waiting", help="memories waiting for your decision")
    for name in ("approve", "reject"):
        d = sub.add_parser(name, help=f"{name} a waiting memory")
        d.add_argument("id", type=int)
    sub.add_parser("list", help="approved memories")
    t = sub.add_parser("trials", help="recent trials")
    t.add_argument("--limit", type=int, default=20)
    sub.add_parser("instincts", help="tricks the court recognises")
    a = p.parse_args(argv)

    if a.cmd == "serve":
        from probate_memory.server import build_server

        build_server(Store(a.db, PineconeRecall.from_env())).run("stdio")
        return 0

    if a.cmd == "check":
        store = Store(a.db, PineconeRecall.from_env())
        j = judge(a.text, a.source, owner_from_env(), store.instincts(), second_judge_from_env())
        print(json.dumps({"verdict": j.verdict, "reason": j.reason, "flags": j.flags}, indent=2))
        return 0 if j.verdict == APPROVED else 1

    store = Store(a.db, PineconeRecall.from_env())
    if a.cmd in ("approve", "reject"):
        try:
            m = store.decide(a.id, a.cmd == "approve")
        except (KeyError, ValueError) as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"Memory {m.id} {m.status}: {m.text}")
        return 0
    if a.cmd == "waiting":
        rows = store.trials(500, CONTESTED)
        if not rows:
            print("Nothing is waiting for you.")
        for m in rows:
            print(_line(m))
            print(f"       {m.reason}")
        return 0
    if a.cmd == "list":
        for m in store.trials(500, APPROVED):
            print(_line(m))
        return 0
    if a.cmd == "trials":
        for m in store.trials(a.limit):
            print(_line(m))
        c = store.counts()
        print(
            f"\n{c['approved']} approved, {c['convicted']} convicted, {c['contested']} waiting, "
            f"{c['instincts']} instincts"
        )
        return 0
    if a.cmd == "instincts":
        for i in store.instincts():
            print(f"{i.id:>5}  {i.summary}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
