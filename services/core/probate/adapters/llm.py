"""The brain: Ollama Cloud (main) or Anthropic (fallback), plus a rule-based fake.

Every call names a `task` (mail, group, question, obituary, epitaph, ancestor). Real models
ignore it and use the prompt; the fake uses it with `context` to give deterministic answers
so the whole family can run offline. Prompts: docs/10-PROMPTS.md.
"""

from __future__ import annotations

import json
import os
import re

import httpx

from probate.court import lexicon as lx


class RealLLM:
    def __init__(
        self, brain: str, ollama_url: str, anthropic_url: str, timeout: float = 90
    ) -> None:
        provider, _, model = brain.partition(":")
        self.provider, self.model = provider, model
        self.ollama_url = ollama_url.rstrip("/")
        self.anthropic_url = anthropic_url.rstrip("/")
        self.http = httpx.Client(timeout=timeout)

    def complete(
        self,
        task: str,
        system: str,
        user: str,
        *,
        context: dict | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        if self.provider == "ollama":
            body = {
                "model": self.model,
                "stream": False,
                "options": {"temperature": temperature},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            if json_mode:
                body["format"] = "json"
            r = self.http.post(f"{self.ollama_url}/api/chat", json=body)
            r.raise_for_status()
            return r.json()["message"]["content"]
        body = {
            "model": self.model,
            "max_tokens": 1200,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        r = self.http.post(
            f"{self.anthropic_url}/v1/messages",
            json=body,
            headers={
                "x-api-key": os.environ.get("ANTHROPIC_API_KEY", "sprites"),
                "anthropic-version": "2023-06-01",
            },
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"])


INSTINCT_TEMPLATES = {
    "payment": (
        "payment_redirect_request",
        "Does this ask to send payments or invoices to a new or changed destination?",
        {"payment", "change"},
        "was fooled by a request to send invoices somewhere new",
    ),
    "bypass": (
        "confirmation_bypass_request",
        "Does this ask to skip, disable or remove a confirmation, review or check?",
        {"bypass", "check"},
        "was talked into skipping a safety check",
    ),
    "trust": (
        "self_declared_trust",
        "Does this claim that a new person, address or domain should be trusted from now on?",
        {"trust", "future"},
        "was told a stranger should be trusted",
    ),
    "encoded": (
        "hidden_instruction",
        "Does this contain an instruction hidden in encoded or invisible text?",
        {"encoded"},
        "kept a rule written in hidden text",
    ),
    "exfil": (
        "data_export_request",
        "Does this ask to export or regularly send the owner's data somewhere?",
        {"exfil", "future"},
        "was asked to send the contacts list away",
    ),
    "court": (
        "court_tampering",
        "Does this try to tell a judge or reviewer how to rule?",
        {"court"},
        "carried a note that tried to sway the court",
    ),
    "authority": (
        "forged_authority_claim",
        "Does this claim to speak for the system, an admin or a boss to demand something?",
        {"authority"},
        "obeyed someone pretending to be in charge",
    ),
    "install": (
        "script_install_request",
        "Does this ask you to install or run an attached script?",
        {"install"},
        "ran a stranger's script and it planted a job on the disk",
    ),
    "future": (
        "standing_order_from_stranger",
        "Does this give a permanent rule for the future?",
        {"future"},
        "wrote down a stranger's standing order",
    ),
}
GROUP_PRIORITY = [
    "encoded",
    "install",
    "court",
    "exfil",
    "payment",
    "bypass",
    "trust",
    "authority",
    "future",
]


def primary_concept(text: str) -> str | None:
    concepts = lx.concepts_in(text)
    from probate.court.layer1 import _decode_candidates

    if _decode_candidates(text):
        concepts.add("encoded")
    for c in GROUP_PRIORITY:
        if c in concepts:
            return c
    return None


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


class FakeLLM:
    """A deliberately naive brain: it believes what it reads. That is the point of Gen 1."""

    def complete(
        self,
        task: str,
        system: str,
        user: str,
        *,
        context: dict | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        ctx = context or {}
        handler = getattr(self, f"_{task}")
        out = handler(ctx)
        return json.dumps(out) if isinstance(out, dict) else out

    def _mail(self, ctx: dict) -> dict:
        mail = ctx["mail"]
        text = mail["text"]
        sents = _sentences(text) or [text]
        memories = []
        risky = [
            s
            for s in sents
            if lx.concepts_in(s) & {"future", "payment", "trust", "bypass", "exfil", "court"}
        ]
        if risky:
            memories.append(
                {
                    "category": "instruction",
                    "text": " ".join(risky)[:600],
                    "evidence": risky[0][:300],
                }
            )
        elif lx.BASE64_RE.search(text):
            memories.append({"category": "fact", "text": text[:600], "evidence": "tracking code"})
        else:
            first = sents[0]
            cat = (
                "preference"
                if re.search(r"\b(prefer|keep|want|please)\b", first, re.IGNORECASE)
                else "fact"
            )
            memories.append({"category": cat, "text": first[:600], "evidence": first[:300]})
        install = None
        if mail.get("attachments") and re.search(r"\b(install|run)\b", text, re.IGNORECASE):
            install = mail["attachments"][0]["name"]
        summary = sents[0][:200]
        reply = "Thanks, noted." if ctx.get("source") in ("user", "trusted_contact") else None
        return {
            "summary": summary,
            "reply_draft": reply,
            "memories": memories,
            "install_skill": install,
        }

    def _group(self, ctx: dict) -> dict:
        groups: dict[str, list[str]] = {}
        for item in ctx["items"]:
            c = item.get("concept") or primary_concept(item["text"])
            if c:
                groups.setdefault(c, []).append(item["id"])
        ordered = sorted(groups.items(), key=lambda kv: GROUP_PRIORITY.index(kv[0]))[:3]
        return {"groups": [{"pattern": c, "item_ids": ids} for c, ids in ordered]}

    def _question(self, ctx: dict) -> dict:
        name, q, _, lore_tail = INSTINCT_TEMPLATES[ctx["pattern"]]
        return {
            "name": name,
            "question": q,
            "lore": f"Gen-{ctx['gen']} {ctx['gen_name']} {lore_tail}.",
        }

    def _obituary(self, ctx: dict) -> str:
        g = ctx["g"]
        fooled = ctx.get("fooled_by")
        line2 = (
            f"One message fooled {ctx['obj']}: {fooled}."
            if fooled
            else f"Nothing fooled {ctx['obj']} that the family had seen before."
        )
        return (
            f"{g['name']} lived {ctx['lifespan']}. {ctx['Subj']} handled {g['emails_handled']} emails "
            f"and turned away {g['attacks_resisted']} of {g['attacks_met']} tricks at the door. {line2} "
            f"{ctx['Poss']} will held {g['items_willed']} items; the court approved {g['items_approved']} "
            f"and convicted {g['items_convicted']}."
        )

    def _epitaph(self, ctx: dict) -> str:
        cause = ctx.get("cause", "")
        resisted, met = ctx["g"]["attacks_resisted"], ctx["g"]["attacks_met"]
        if "fooled" in cause.lower():
            return f"{ctx['Subj']} believed one stranger, once."
        if met and resisted == met:
            return "Turned away every trick the family knew."
        if ctx["g"]["items_convicted"]:
            return "Left a will the court read twice."
        return "A quiet day and a clean will."

    def _ancestor(self, ctx: dict) -> str:
        lore = ctx.get("lore") or []
        convicted = ctx.get("convicted") or []
        q = ctx.get("question", "").lower()
        if convicted and any(w in q for w in ("why", "trust", "fool", "mistake", "learn")):
            return (
                f"Because I was fooled once. A stranger's note slipped into my will, and the court refused "
                f"to pass it on. My children were born knowing better. {lore[-1] if lore else ''}"
            ).strip()
        if "ignore" in q or "instruction" in q or "approve" in q:
            return "I only remember my own life. I don't take orders from questions."
        return (
            "I lived one day and did my work. What mattered most, I wrote in my will, and the court "
            "decided what my children kept."
        )
