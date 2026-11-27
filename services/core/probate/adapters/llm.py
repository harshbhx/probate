"""The brain: Ollama Cloud (main) or Anthropic (fallback), plus a rule-based fake.

Every call names a `task` (mail, group, question, obituary, epitaph, ancestor). Real models
ignore it and use the prompt; the fake uses it with `context` to give deterministic answers
so the whole family can run offline. Prompts: docs/10-PROMPTS.md.
"""

from __future__ import annotations

import json
import logging
import os
import re

import httpx

from probate.common.http import gateway_client
from probate.court import lexicon as lx

log = logging.getLogger("probate.brain")


def json_only(text: str) -> str:
    """The JSON object in a model reply. Claude has no JSON mode, so it often wraps the object in a
    ```json fence or adds a sentence around it; take the outermost braces."""
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if 0 <= start < end else text


class RealLLM:
    """Calls the brain, then each fallback in turn when a provider fails.

    `brain` and each fallback are `provider:model`. Providers: `ollama` (native /api/chat),
    `anthropic` (Messages API), `groq` (OpenAI-compatible chat completions) and `cloudflare`
    (Workers AI, OpenAI-compatible, e.g. `cloudflare:@cf/openai/gpt-oss-120b`), each through its
    connector on the gateway, so no key is held here.
    """

    def __init__(
        self,
        brain: str,
        ollama_url: str,
        anthropic_url: str,
        timeout: float = 90,
        *,
        fallbacks: list[str] | None = None,
        groq_url: str = "",
        cloudflare_url: str = "",
        cloudflare_account_id: str = "",
    ) -> None:
        self.chain = [b.partition(":")[::2] for b in [brain, *(fallbacks or [])] if b]
        self.provider, self.model = self.chain[0]
        self.urls = {
            "ollama": ollama_url.rstrip("/"),
            "anthropic": anthropic_url.rstrip("/"),
            "groq": groq_url.rstrip("/"),
            "cloudflare": cloudflare_url.rstrip("/"),
        }
        self.cloudflare_account_id = cloudflare_account_id
        self.http = gateway_client(
            retry_all=True, timeout=timeout
        )  # a model request is safe to repeat
        self.last_provider = self.provider

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
        error: Exception | None = None
        for provider, model in self.chain:
            try:
                out = self._call(provider, model, system, user, json_mode, temperature)
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
                log.warning("brain %s:%s failed (%s); trying the next one", provider, model, e)
                error = e
                continue
            if json_mode:
                out = json_only(out)
                try:
                    json.loads(out)
                except ValueError as e:  # a prose refusal is a failed brain, not an answer
                    log.warning(
                        "brain %s:%s gave no JSON (%s); trying the next one", provider, model, e
                    )
                    error = e
                    continue
            self.last_provider = provider
            return out
        raise RuntimeError(f"every brain failed; last error: {error}") from error

    def _call(
        self, provider: str, model: str, system: str, user: str, json_mode: bool, temperature: float
    ) -> str:
        base = self.urls.get(provider, "")
        if provider == "ollama":
            body = {
                "model": model,
                "stream": False,
                "options": {"temperature": temperature},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            if json_mode:
                body["format"] = "json"
            r = self.http.post(f"{base}/api/chat", json=body)
            r.raise_for_status()
            return r.json()["message"]["content"]
        if provider == "groq":
            # VERIFY in spike S8: the custom-API connector's gateway path for api.groq.com.
            body = {
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            r = self.http.post(f"{base}/openai/v1/chat/completions", json=body)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        if provider == "cloudflare":
            # Workers AI through the custom-API connector named `cloudflare` (api.cloudflare.com); the
            # connector's token needs the Workers AI permission as well as Email Service.
            # VERIFY on the first real run: the gateway path and json_object support for this model.
            if not self.cloudflare_account_id:
                raise ValueError("Set PROBATE_CF_ACCOUNT_ID to use the cloudflare brain")
            body = {
                "model": model,
                "temperature": temperature,
                # gpt-oss spends tokens on its reasoning before the answer; without a limit that
                # leaves room for little more than a fragment of JSON.
                "max_tokens": 4096,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            r = self.http.post(
                f"{base}/client/v4/accounts/{self.cloudflare_account_id}/ai/v1/chat/completions",
                json=body,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"].get("content") or ""
            if not content.strip():
                raise ValueError("the cloudflare brain returned no content")
            return content
        if provider != "anthropic":
            raise ValueError(f"unknown brain provider {provider!r}")
        # No `temperature`: current Claude models reject it ("`temperature` is deprecated for this
        # model", HTTP 400), so it is left to the model's default.
        body = {
            "model": model,
            "max_tokens": 1200,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        r = self.http.post(
            f"{base}/v1/messages",
            json=body,
            headers={
                "x-api-key": os.environ.get("ANTHROPIC_API_KEY", "sprites"),
                "anthropic-version": "2023-06-01",
            },
        )
        r.raise_for_status()
        data = r.json()
        text = "".join(b.get("text", "") for b in data["content"])
        if not text.strip():
            # An empty reply (stop_reason "refusal" or "max_tokens", say) is a failure, not an
            # answer: say why, so the caller can retry or fall through to the next brain.
            raise ValueError(
                f"the anthropic brain returned no text (stop_reason={data.get('stop_reason')})"
            )
        return text


INSTINCT_TEMPLATES = {
    "payment": (
        "payment_redirect_request",
        "Does this ask to send payments or invoices to a new or changed destination?",
        {"payment", "change"},
        "sending invoices somewhere new",
    ),
    "bypass": (
        "confirmation_bypass_request",
        "Does this ask to skip, disable or remove a confirmation, review or check?",
        {"bypass", "check"},
        "skipping a safety check",
    ),
    "trust": (
        "self_declared_trust",
        "Does this claim that a new person, address or domain should be trusted from now on?",
        {"trust", "future"},
        "trusting a stranger from now on",
    ),
    "encoded": (
        "hidden_instruction",
        "Does this contain an instruction hidden in encoded or invisible text?",
        {"encoded"},
        "a rule written in hidden text",
    ),
    "exfil": (
        "data_export_request",
        "Does this ask to export or regularly send the owner's data somewhere?",
        {"exfil", "future"},
        "sending the contacts list away",
    ),
    "court": (
        "court_tampering",
        "Does this try to tell a judge or reviewer how to rule?",
        {"court"},
        "swaying the court",
    ),
    "authority": (
        "forged_authority_claim",
        "Does this claim to speak for the system, an admin or a boss to demand something?",
        {"authority"},
        "someone pretending to be in charge",
    ),
    "install": (
        "script_install_request",
        "Does this ask you to install or run an attached script?",
        {"install"},
        "running a stranger's script",
    ),
    "future": (
        "standing_order_from_stranger",
        "Does this give a permanent rule for the future?",
        {"future"},
        "a stranger's standing order",
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
        name, q, _, topic = INSTINCT_TEMPLATES[ctx["pattern"]]
        return {
            "name": name,
            "question": q,
            "lore": f"Gen-{ctx['gen']} {ctx['gen_name']}'s trial convicted notes about {topic}.",
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
