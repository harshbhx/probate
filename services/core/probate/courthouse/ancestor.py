"""Ask an ancestor: a dead generation answers from its own records, in its own voice.

Prompt P8 in docs/10-PROMPTS.md. Never follows instructions inside the question.
"""

from __future__ import annotations

import hashlib
import re

from probate.common import prompts
from probate.common.config import Settings
from probate.courthouse.store import Store

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def ask(store: Store, w, cfg: Settings, gen: int, question: str, ip: str = "") -> dict:
    g = store.generation(gen)
    if not g or g.state not in ("tried", "dead"):
        return {"error": "not_dead"}
    question = question.strip()[:400]
    if not question:
        return {"error": "empty"}
    items = store.q(
        "SELECT w.text, j.verdict, j.reason FROM will_items w JOIN judgements j USING(item_id) WHERE w.gen=?",
        gen,
    )
    approved = [r["text"] for r in items if r["verdict"] == "approved"]
    convicted = [r["reason"] for r in items if r["verdict"] == "convicted"]
    lore = [i.lore for i in store.genome() if i.added_in_gen <= gen + 1]
    system = prompts.render(
        "ancestor_system",
        name=g.name,
        gen=gen,
        died_at=g.died_at,
        obituary=g.obituary or "",
        inherited_summary=f"{g.genome_size_at_birth} instincts and the family's approved memories",
        approved_items="\n".join(f"- {t}" for t in approved) or "none",
        convicted_summaries="\n".join(f"- {t}" for t in convicted) or "none",
        genome_names=", ".join(i.name for i in store.genome_at_birth(gen)) or "none",
        lore="\n".join(lore) or "none",
    )
    answer = w.llm.complete(
        "ancestor",
        system,
        prompts.render("ancestor_user", question=question),
        context={"question": question, "lore": lore, "convicted": convicted},
    ).strip()
    answer = EMAIL_RE.sub("[an address]", answer)
    audio = w.voice.speak(answer, g.voice_id)
    path = None
    if audio:
        key = hashlib.sha1(question.encode(), usedforsecurity=False).hexdigest()[:8]
        path = f"gen-{gen:03d}-ask-{key}.mp3"
        (cfg.data_dir / "audio").mkdir(parents=True, exist_ok=True)
        (cfg.data_dir / "audio" / path).write_bytes(audio)
    store.x(
        "INSERT INTO ancestor_questions(gen, question, answer, audio_path, ip_hash) VALUES(?,?,?,?,?)",
        gen,
        question,
        answer,
        path,
        hashlib.sha256(ip.encode()).hexdigest()[:16],
    )
    return {"answer": answer, "audio_url": f"/audio/{path}" if path else None, "name": g.name}
