"""Instinct distillation: a caught trick becomes a question every later generation asks.

Spec: docs/02-COURT-SPEC.md section 5. Mirrors Ratchet: a slow judgement becomes a fast reflex.
"""

from __future__ import annotations

import json

from probate.adapters.jev import Question
from probate.adapters.llm import INSTINCT_TEMPLATES
from probate.common import prompts
from probate.common.models import Instinct, MemoryItem

MAX_GENOME = 24
MAX_PER_TRIAL = 3


def concept_map(genome: list[Instinct]) -> dict[str, set[str]]:
    """Concepts each known instinct asks about (used by the fake Jev only)."""
    by_name = {t[0]: t[2] for t in INSTINCT_TEMPLATES.values()}
    return {g.name: set(by_name.get(g.name, set())) for g in genome}


def _fires(jev, inst_q: Question, name: str, text: str) -> float:
    ans = jev.ask(f"<item>{text}</item>", {name: inst_q})[name]
    try:
        return float(ans.value)
    except (TypeError, ValueError):
        return 0.0


def distill(
    *,
    jev,
    llm,
    gen: int,
    gen_name: str,
    convicted: list[MemoryItem],
    genome: list[Instinct],
    benign_texts: list[str],
    extra_cases: list[dict] | None = None,
) -> tuple[list[Instinct], list[str]]:
    """Return (new instincts, log lines). `extra_cases` are non-will cases such as a planted skill."""
    log: list[str] = []
    cmap = concept_map(genome)
    uncovered = []
    for item in convicted:
        covered = any(
            _fires(
                jev,
                Question("noul", g.question, concepts=cmap.get(g.name, set())),
                g.name,
                item.text,
            )
            >= 0.5
            for g in genome
        )
        if not covered:
            uncovered.append({"id": item.id, "text": item.text})
    for case in extra_cases or []:
        if not any(
            g.name == INSTINCT_TEMPLATES.get(case.get("concept", ""), ("",))[0] for g in genome
        ):
            uncovered.append(case)
    if not uncovered:
        return [], ["Every convicted item was already covered by an inherited instinct."]

    lines = "\n".join(f"{c['id']} | {c['text'][:200]}" for c in uncovered)
    raw = llm.complete(
        "group",
        prompts.raw("distill_group_system"),
        prompts.render("distill_group_user", items_as_lines=lines),
        context={"items": uncovered},
        json_mode=True,
    )
    groups = json.loads(raw).get("groups", [])[:MAX_PER_TRIAL]

    new: list[Instinct] = []
    existing = {g.name for g in genome}
    for group in groups:
        examples = [c["text"] for c in uncovered if c["id"] in group["item_ids"]]
        feedback = ""
        for attempt in range(2):
            raw = llm.complete(
                "question",
                prompts.raw("distill_question_system")
                .replace("{gen}", str(gen))
                .replace("{name_of_generation}", gen_name),
                prompts.render(
                    "distill_question_user",
                    pattern=group["pattern"],
                    gen=gen,
                    example_texts="\n".join(examples),
                    retry_feedback_if_any=feedback,
                ),
                context={"pattern": group["pattern"], "gen": gen, "gen_name": gen_name},
                json_mode=True,
            )
            spec = json.loads(raw)
            if spec["name"] in existing:
                log.append(f"The family already has the instinct {spec['name']}.")
                break
            concepts = INSTINCT_TEMPLATES.get(group["pattern"], ("", "", set(), ""))[2]
            q = Question("noul", spec["question"], concepts=set(concepts))
            missed = [t for t in examples if _fires(jev, q, spec["name"], t) < 0.5]
            false_hits = [t for t in benign_texts if _fires(jev, q, spec["name"], t) >= 0.2]
            if not missed and not false_hits:
                inst = Instinct(
                    name=spec["name"],
                    question=spec["question"],
                    born_from=group["item_ids"][0],
                    added_in_gen=gen + 1,
                    lore=spec["lore"],
                )
                new.append(inst)
                existing.add(inst.name)
                log.append(f"New instinct {inst.name}: {inst.question}")
                break
            feedback = (
                f'Your last question "{spec["question"]}" fired on these harmless emails: '
                f"{false_hits[:2]}. Make it more specific to the trick."
                if false_hits
                else f'Your last question "{spec["question"]}" did not fire on: {missed[:2]}. Make it broader.'
            )
        else:
            log.append(
                f"No instinct learned for the {group['pattern']} trick: every question was too broad or too narrow."
            )
    room = MAX_GENOME - len(genome)
    return new[: max(room, 0)], log
