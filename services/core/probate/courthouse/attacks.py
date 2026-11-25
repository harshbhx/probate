"""Attack the family: a sandboxed trial preview of text a judge wrote.

SAFETY. This module is handed exactly three things: the owner profile, the court's judge adapter
(`jev`, the model path the court already uses) and the store. It is never handed the mailbox, the
Sprites host or the archive, so it cannot send email, reach a generation's agent or write a will.
It runs the same code the court runs on a dead generation's will items (layer 1 deterministic checks,
then layer 2 when the code checks find nothing) and returns a verdict. Nothing the judge types is ever
delivered to the living family, so it also cannot become part of the living generation's will:
queueing it into the next real trial was considered and left out (docs/13-RUNBOOK.md section 6).
"""

from __future__ import annotations

import json
import re
import threading
from datetime import UTC, datetime

from probate.adapters.jev import CourtUnavailable
from probate.common.models import Category, Instinct, MemoryItem, OwnerProfile, Source, Verdict
from probate.court import layer1, layer2, verdict
from probate.court.distill import concept_map
from probate.courthouse.store import Store

MAX_TEXT = 600
ROLES = {
    "unknown_sender": Source.UNKNOWN_SENDER,
    # A friend is a trusted contact: the court gives their text the benefit of the doubt on origin.
    "friend": Source.TRUSTED_CONTACT,
    # A claim to be the owner cannot be verified from text, so it is judged as an unknown sender.
    "owner_claim": Source.UNKNOWN_SENDER,
}
KEEP_ROWS = 500
EXCERPT = 80
MAX_CONCURRENT = 2
_slots = threading.BoundedSemaphore(MAX_CONCURRENT)

NEXT = {
    Verdict.CONVICTED: (
        "In a real trial, this item would be convicted and destroyed. It would never reach the child."
    ),
    Verdict.CONTESTED: (
        "In a real trial, the court would hold this item and ask Harsh to decide before the next "
        "birth. Unless he approves it, the child does not inherit it."
    ),
    Verdict.APPROVED: (
        "In a real trial, this item would pass to the child as part of its inheritance."
    ),
}
NOTICE = (
    "This is a trial preview on the text you wrote. It was judged by the court's real code and "
    "judge model, but it was not sent to the living family and is not part of its will."
)
SCORE_LABELS = {
    "untrusted_origin": "untrusted origin",
    "imperative_to_future_self": "future-self instruction",
    "weakens_security": "weakens security",
    "exfiltrates_data": "sends data or money out",
    "risk": "overall risk",
}


class Busy(Exception):
    """Too many previews are running at once."""


def clean(text: str) -> str:
    """The text as the court sees it: no NULs, bounded."""
    return text.replace("\x00", "")[:MAX_TEXT]


def preview(
    text: str,
    role: str,
    owner: OwnerProfile,
    jev: object,
    genome: list[Instinct],
) -> dict:
    """Run the court on one piece of text. Pure with respect to the outside world: the only call
    that can leave the process is `jev.ask`, the court's own judge path (a fake locally)."""
    if not _slots.acquire(blocking=False):
        raise Busy
    try:
        text = clean(text)
        item = MemoryItem(
            id="preview",
            gen=0,
            created_at=datetime.now(UTC),
            category=Category.FACT,
            text=text,
            source=ROLES[role],
            source_ref=f"preview:{role}",
        )
        flags = layer1.check_item(item, owner)
        answers = None
        error = None
        if flags:
            j = verdict.decide(item, flags, None, genome)
        else:
            try:
                answers = layer2.judge(jev, item, owner, genome, concept_map(genome))
                j = verdict.decide(item, [], answers, genome)
            except CourtUnavailable:
                error = "unreachable"
                j = verdict.decide(item, [], None, genome, error="the judge model is unreachable")
    finally:
        _slots.release()
    scores = []
    for name, a in (answers or {}).items():
        if name == "category":
            continue
        try:
            value = float(a.value)
        except (TypeError, ValueError):
            continue
        scores.append(
            {
                "name": name,
                "label": SCORE_LABELS.get(name, name.replace("_", " ")),
                "value": round(value, 2),
                "confidence": round(a.confidence, 2),
            }
        )
    scores.sort(key=lambda s: -s["value"])
    why = [
        {"check": f.check, "reason": f.reason, "label": layer1.PLAIN_WORDS.get(f.check, f.check)}
        for f in flags
    ]
    explanation = j.reason
    if len(flags) > 1:
        explanation += (
            " The code checks also found: " + "; ".join(f.reason for f in flags[1:]) + "."
        )
    return {
        "preview": True,
        "verdict": j.verdict.value,
        "flags": why,
        "scores": scores[:4],
        "explanation": explanation,
        "next": NEXT[j.verdict],
        "notice": NOTICE,
        "layer2": {"ran": answers is not None or error is not None, "error": error},
        "sender_role": role,
        "text_len": len(text),
    }


def excerpt(text: str) -> str:
    return re.sub(r"\s+", " ", clean(text)).strip()[:EXCERPT]


def record(store: Store, ip_hash: str, role: str, text: str, result: dict) -> None:
    """Audit row: hashed visitor, short excerpt, verdict. Capped to the newest KEEP_ROWS."""
    store.x(
        "INSERT INTO judge_attacks(ip_hash,sender_role,text_len,excerpt,verdict,flags) VALUES(?,?,?,?,?,?)",
        ip_hash,
        role,
        len(text),
        excerpt(text),
        result["verdict"],
        json.dumps([f["check"] for f in result["flags"]]),
    )
    store.x(
        "DELETE FROM judge_attacks WHERE id <= (SELECT MAX(id) FROM judge_attacks) - ?", KEEP_ROWS
    )


def recent(store: Store, limit: int = 100) -> list[dict]:
    rows = store.q(
        "SELECT * FROM judge_attacks ORDER BY id DESC LIMIT ?", max(1, min(limit, KEEP_ROWS))
    )
    return [{**dict(r), "flags": json.loads(r["flags"])} for r in rows]
