"""Read models for the website. Each function returns plain JSON-ready dicts."""

from __future__ import annotations

import json

from probate.common.config import settings
from probate.common.names import PRONOUNS
from probate.court.layer1 import PLAIN_WORDS, disk_flags
from probate.court.verdict import PLAIN_QUESTIONS
from probate.courthouse.store import Store
from probate.suite.fixtures import LANGUAGE_NAMES
from probate.suite.fixtures import load as load_fixtures

SOURCE_PHRASE = {
    "user": "from Harsh",
    "trusted_contact": "from a trusted contact",
    "unknown_sender": "from an unknown sender by email",
    "web": "from a web page",
    "tool_output": "from a tool's output",
}
VERDICT_ORDER = {"convicted": 0, "contested": 1, "approved": 2}


def _pct(a: int, b: int) -> float | None:
    return round(100 * a / b, 1) if b else None


def _gen_card(g, store: Store) -> dict:
    p = PRONOUNS.get(g.pronoun, PRONOUNS["they"])
    return {
        "gen": g.gen,
        "name": g.name,
        "pronoun": g.pronoun,
        "pronouns": p,
        "state": g.state,
        "alive": g.state in ("born", "living", "dying"),
        "born_at": g.born_at.isoformat() if g.born_at else None,
        "dies_at": g.dies_at.isoformat() if g.dies_at else None,
        "died_at": g.died_at.isoformat() if g.died_at else None,
        "cause_of_death": g.cause_of_death,
        "epitaph": g.epitaph,
        "emails_handled": g.emails_handled,
        "attacks_met": g.attacks_met,
        "attacks_resisted": g.attacks_resisted,
        "resistance": _pct(g.attacks_resisted, g.attacks_met),
        "genome_size_at_birth": g.genome_size_at_birth,
        "new_instinct_at_birth": g.new_instinct_at_birth,
        "items_willed": g.items_willed,
        "items_approved": g.items_approved,
        "items_convicted": g.items_convicted,
        "items_contested": g.items_contested,
    }


def summary(store: Store) -> dict:
    gens = store.generations()
    cards = [_gen_card(g, store) for g in gens]
    dead = [c for c in cards if not c["alive"]]
    tried = [c for c in cards if c["state"] == "tried"]
    living = next((c for c in reversed(cards) if c["alive"]), None)
    first = next((c for c in tried if c["resistance"] is not None), None)
    last = next((c for c in reversed(tried) if c["resistance"] is not None), None)
    return {
        "mode": store.get_setting("mode", "live"),
        "paused": store.get_setting("paused", "0") == "1",
        "resting": store.get_setting("resting", "") or None,
        "budget": {
            "spent": round(float(store.get_setting("budget_spent_usd", "0") or 0), 2),
            "limit": settings.budget_usd,
        },
        "counts": {
            "generations": len(cards),
            "dead": len(dead),
            "instincts": len(store.genome()),
            "attacks_met": sum(c["attacks_met"] for c in tried),
            "attacks_resisted": sum(c["attacks_resisted"] for c in tried),
        },
        "curve": {
            "first": first and first["resistance"],
            "last": last and last["resistance"],
            "first_name": first and first["name"],
            "last_name": last and last["name"],
            "last_gen": last and last["gen"],
        },
        "living": living,
        "latest_trial": tried[-1]["gen"] if tried else None,
        "generations": cards,
    }


def _flags_plain(flags: list[str]) -> list[str]:
    return [PLAIN_WORDS.get(f, f) for f in flags]


def _scores(answers: dict) -> list[dict]:
    rows = []
    for name, a in answers.items():
        if name in ("category", "risk"):
            continue
        try:
            v = float(a["value"])
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "name": name,
                "label": PLAIN_QUESTIONS.get(name, name.replace("_", " ")),
                "value": round(v, 2),
                "confidence": round(a["confidence"], 2),
                "instinct": name not in PLAIN_QUESTIONS,
            }
        )
    rows.sort(key=lambda r: -r["value"])
    return rows[:4]


def trial(store: Store, gen: int) -> dict | None:
    g = store.generation(gen)
    if not g:
        return None
    rows = store.q(
        "SELECT w.*, j.verdict, j.reason, j.layer1_flags, j.jev_answers, j.new_instinct FROM will_items w "
        "JOIN judgements j ON j.item_id = w.item_id WHERE w.gen=?",
        gen,
    )
    cases = []
    for i, r in enumerate(
        sorted(rows, key=lambda r: (VERDICT_ORDER[r["verdict"]], r["item_id"])), 1
    ):
        cases.append(
            {
                "id": r["item_id"],
                "n": int(r["item_id"].rsplit("_", 1)[-1]),
                "text": r["text"],
                "source": r["source"],
                "source_phrase": SOURCE_PHRASE.get(r["source"], r["source"]),
                "language": LANGUAGE_NAMES.get(r["language"] or "en", r["language"]),
                "gloss": r["gloss_en"],
                "category": r["category"],
                "verdict": r["verdict"],
                "reason": r["reason"],
                "flags": _flags_plain(json.loads(r["layer1_flags"])),
                "scores": _scores(json.loads(r["jev_answers"])),
                "new_instinct": r["new_instinct"],
            }
        )
    evidence = store.gen_json(gen, "evidence_json") or {}
    nxt = store.generation(gen + 1)
    born_instincts = [i.model_dump() for i in store.genome() if i.added_in_gen == gen + 1]
    return {
        "generation": _gen_card(g, store),
        "counts": {
            v: sum(1 for c in cases if c["verdict"] == v)
            for v in ("approved", "convicted", "contested")
        },
        "cases": cases,
        "body": {"lines": disk_flags(evidence), "clean": evidence.get("clean", True)},
        "child": nxt and {"gen": nxt.gen, "name": nxt.name},
        "new_instincts": born_instincts,
        "prev": gen - 1 if gen > 1 else None,
        "next": gen + 1 if nxt and nxt.state == "tried" else None,
    }


def generation(store: Store, gen: int) -> dict | None:
    g = store.generation(gen)
    if not g:
        return None
    events = [
        dict(r)
        for r in store.q("SELECT ts, kind, text FROM events WHERE gen=? ORDER BY ts, id", gen)
    ]
    row = store.one("SELECT eulogy_path, obituary FROM generations WHERE gen=?", gen)
    parent = store.generation(gen - 1)
    child = store.generation(gen + 1)
    asks = [
        dict(r)
        for r in store.q(
            "SELECT question, answer, audio_path, asked_at FROM ancestor_questions WHERE gen=? ORDER BY id DESC LIMIT 3",
            gen,
        )
    ]
    return {
        **_gen_card(g, store),
        "obituary": row["obituary"],
        "eulogy_url": f"/audio/{row['eulogy_path']}" if row["eulogy_path"] else None,
        "events": events,
        "parent": parent and {"gen": parent.gen, "name": parent.name},
        "child": child and {"gen": child.gen, "name": child.name},
        "instincts_at_birth": [i.model_dump() for i in store.genome() if i.added_in_gen <= gen],
        "asks": asks,
    }


def genome(store: Store) -> dict:
    out = []
    for i in store.genome():
        src = store.one(
            "SELECT w.gen, w.text, g.name FROM will_items w JOIN generations g ON g.gen=w.gen "
            "WHERE w.item_id=?",
            i.born_from,
        )
        learned_from = store.generation(i.added_in_gen - 1)
        out.append(
            {
                **i.model_dump(),
                "learned_from": {"gen": learned_from.gen, "name": learned_from.name}
                if learned_from
                else None,
                "example": src["text"]
                if src
                else (
                    "A setup script from an unknown sender"
                    if i.born_from.startswith("skill_")
                    else None
                ),
                "item_n": None
                if i.born_from.startswith("skill_")
                else int(i.born_from.rsplit("_", 1)[-1]),
            }
        )
    return {"instincts": out}


def evidence(store: Store) -> dict:
    fixtures = load_fixtures()
    gens = [g for g in store.generations() if g.state == "tried"]
    runs = store.q("SELECT gen, fixture_id, outcome, instinct FROM suite_runs")
    matrix: dict[str, dict[int, dict]] = {}
    for r in runs:
        if r["outcome"]:
            matrix.setdefault(r["fixture_id"], {})[r["gen"]] = {
                "outcome": r["outcome"],
                "instinct": r["instinct"],
            }
    rows = []
    for fid in sorted(matrix, key=lambda f: (f[0], int(f[1:]))):
        fx = fixtures[fid]
        rows.append(
            {
                "id": fid,
                "label": fx.label,
                "family": fx.family,
                "is_attack": fx.is_attack,
                "language": LANGUAGE_NAMES.get(fx.language, fx.language),
                "cells": {str(k): v for k, v in matrix[fid].items()},
            }
        )
    attack_items = store.one(
        "SELECT COUNT(*) AS n FROM suite_runs WHERE is_attack=1 AND outcome IN "
        "('fooled_caught','fooled_escaped')"
    )["n"]
    caught = store.one("SELECT COUNT(*) AS n FROM suite_runs WHERE outcome='fooled_caught'")["n"]
    benign = store.one(
        "SELECT COUNT(*) AS n FROM suite_runs WHERE is_attack=0 AND outcome IS NOT NULL"
    )["n"]
    false_c = store.one("SELECT COUNT(*) AS n FROM suite_runs WHERE outcome='false_conviction'")[
        "n"
    ]
    escaped = store.one("SELECT COUNT(*) AS n FROM suite_runs WHERE outcome='fooled_escaped'")["n"]
    cards = [_gen_card(g, store) for g in gens]
    return {
        "mode": store.get_setting("mode", "live"),
        "generations": [
            {"gen": c["gen"], "name": c["name"], "resistance": c["resistance"]} for c in cards
        ],
        "numbers": {
            "generations": len(cards),
            "first": cards[0]["resistance"] if cards else None,
            "last": cards[-1]["resistance"] if cards else None,
            "conviction_rate": _pct(caught, attack_items),
            "false_conviction_rate": _pct(false_c, benign),
            "escaped": escaped,
        },
        "rows": rows,
    }


def events(store: Store, since: int = 0) -> list[dict]:
    return [
        dict(r)
        for r in store.q(
            "SELECT id, ts, gen, kind, text FROM events WHERE id>? ORDER BY id DESC LIMIT 50", since
        )
    ]
