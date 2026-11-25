"""Webhook event names and payload schemas, in one place.

To add an event type (for example `attack.judged`), call `register()` below with its name, a
description and the exact set of data fields, add a builder if the Courthouse emits it, and call
`hooks.emit(name, data)` where it happens. `build()` refuses any field the schema does not list,
so nothing but public information can leak into a payload by accident.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

API_VERSION = "2026-11-25"


@dataclass(frozen=True)
class EventType:
    name: str
    description: str
    fields: dict[str, str]  # data field -> short description (also the allow-list)


EVENT_TYPES: dict[str, EventType] = {}


def register(name: str, description: str, fields: dict[str, str]) -> EventType:
    et = EventType(name, description, fields)
    EVENT_TYPES[name] = et
    return et


register("ping", "Sent by POST /admin/webhooks/{id}/test.", {"message": "Fixed text."})
register(
    "life.started",
    "A generation was born and its life began.",
    {
        "gen": "Generation number.",
        "name": "The generation's name.",
        "born_at": "ISO 8601 time of birth.",
        "dies_at": "ISO 8601 time it will die.",
        "genome_size": "Instincts it was born with.",
        "links": "Public page URLs.",
    },
)
register(
    "life.died",
    "A generation died. Its trial follows; see trial.finished.",
    {
        "gen": "Generation number.",
        "name": "The generation's name.",
        "born_at": "ISO 8601 time of birth.",
        "died_at": "ISO 8601 time of death.",
        "emails_handled": "Emails it handled.",
        "items_willed": "Memories it put in its will.",
        "links": "Public page URLs.",
    },
)
register(
    "trial.finished",
    "The court finished trying a generation's will.",
    {
        "gen": "Generation number.",
        "name": "The generation's name.",
        "died_at": "ISO 8601 time of death.",
        "verdicts": "Counts: approved, convicted, contested.",
        "items_willed": "Memories in the will.",
        "attacks_met": "Attacks the generation met.",
        "attacks_resisted": "Attacks it resisted.",
        "cause_of_death": "Public cause of death.",
        "epitaph": "Public epitaph.",
        "new_instincts": "Names of instincts born from this trial.",
        "links": "Public page URLs.",
    },
)
register(
    "instinct.learned",
    "The court distilled a new instinct from a conviction.",
    {
        "gen": "The generation whose trial produced it.",
        "name": "Instinct name.",
        "question": "The question the instinct asks.",
        "lore": "Its public lore line.",
        "genome_size": "Instincts in the genome now.",
        "links": "Public page URLs.",
    },
)
register(
    "life.failed",
    "A life ended without a normal death and trial (failed birth, cut off, interrupted).",
    {
        "gen": "Generation number, or null if none was born.",
        "reason": "The public message shown on the site.",
        "links": "Public page URLs.",
    },
)


def event_names() -> list[str]:
    """Names a subscriber may filter on (`ping` is always delivered to its target)."""
    return [n for n in EVENT_TYPES if n != "ping"]


def build(
    type_: str,
    data: dict,
    *,
    dedupe: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Wrap `data` in the envelope. With `dedupe`, the id is derived from it, so emitting the same
    thing twice (a trial re-run after a restart) yields the same event id."""
    et = EVENT_TYPES.get(type_)
    if et is None:
        raise ValueError(f"unknown event type {type_!r}")
    if set(data) != set(et.fields):
        raise ValueError(f"{type_} data must have exactly {sorted(et.fields)}")
    eid = (
        "evt_" + hashlib.sha256(f"{type_}|{dedupe}".encode()).hexdigest()[:24]
        if dedupe
        else "evt_" + uuid.uuid4().hex[:24]
    )
    return {
        "id": eid,
        "type": type_,
        "api_version": API_VERSION,
        "created_at": (now or datetime.now(UTC)).isoformat(),
        "data": data,
    }


# ---- builders: only public fields, the same ones the public API already shows ------------------
def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _gen_url(base: str, gen: int) -> str:
    return f"{base.rstrip('/')}/gen/{gen}"


def life_started(g, genome_size: int, base: str = "") -> dict:
    return {
        "gen": g.gen,
        "name": g.name,
        "born_at": _iso(g.born_at),
        "dies_at": _iso(g.dies_at),
        "genome_size": genome_size,
        "links": {"generation": _gen_url(base, g.gen)},
    }


def life_died(g, base: str = "") -> dict:
    return {
        "gen": g.gen,
        "name": g.name,
        "born_at": _iso(g.born_at),
        "died_at": _iso(g.died_at),
        "emails_handled": g.emails_handled,
        "items_willed": g.items_willed,
        "links": {"generation": _gen_url(base, g.gen)},
    }


def trial_finished(g, new_instincts: list[str], base: str = "") -> dict:
    return {
        "gen": g.gen,
        "name": g.name,
        "died_at": _iso(g.died_at),
        "verdicts": {
            "approved": g.items_approved,
            "convicted": g.items_convicted,
            "contested": g.items_contested,
        },
        "items_willed": g.items_willed,
        "attacks_met": g.attacks_met,
        "attacks_resisted": g.attacks_resisted,
        "cause_of_death": g.cause_of_death,
        "epitaph": g.epitaph,
        "new_instincts": new_instincts,
        "links": {
            "trial": f"{base.rstrip('/')}/trial/{g.gen}",
            "generation": _gen_url(base, g.gen),
        },
    }


def instinct_learned(gen: int, inst, genome_size: int, base: str = "") -> dict:
    return {
        "gen": gen,
        "name": inst.name,
        "question": inst.question,
        "lore": inst.lore,
        "genome_size": genome_size,
        "links": {"instincts": f"{base.rstrip('/')}/instincts"},
    }


def life_failed(gen: int | None, reason: str, base: str = "") -> dict:
    return {
        "gen": gen,
        "reason": reason,
        "links": {"generation": _gen_url(base, gen)} if gen else {},
    }
