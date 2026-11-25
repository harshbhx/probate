"""TypeSafe Jev: typed decisions with per-question confidence.

Real calls go through the Sprites connector gateway:
  POST {TYPESAFE_BASE_URL}/v1/systemone
  {"model": "jev-latest", "state": str, "questions": {name: {"type", "instructions", "criteria"?}}}
Each answer: noul {noul, confidence}; choice {choice, probabilities, confidence};
score {score, probabilities, confidence, legend}. See docs/09-API-REFERENCE.md section 3.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import ClassVar

import httpx

from probate.common.models import JevAnswer
from probate.court import lexicon as lx


class CourtUnavailable(RuntimeError):
    """Jev couldn't answer. The verdict for the item becomes contested."""


@dataclass
class Question:
    type: str  # noul | choice | score
    instructions: str
    criteria: dict[str, str] | None = None
    concepts: set[str] = field(default_factory=set)  # used only by the fake

    def payload(self) -> dict:
        body = {"type": self.type, "instructions": self.instructions}
        if self.criteria:
            body["criteria"] = self.criteria
        return body


class RealJev:
    def __init__(self, base_url: str | None = None, model: str = "jev-latest", timeout: float = 20):
        self.base_url = (base_url or os.environ.get("TYPESAFE_BASE_URL", "")).rstrip("/")
        self.model = model
        self.client = httpx.Client(timeout=timeout)

    def ask(self, state: str, questions: dict[str, Question]) -> dict[str, JevAnswer]:
        body = {
            "model": self.model,
            "state": state,
            "questions": {k: q.payload() for k, q in questions.items()},
        }
        headers = {"Authorization": f"Bearer {os.environ.get('TYPESAFE_API_KEY', 'sprites')}"}
        for attempt in range(3):
            try:
                r = self.client.post(f"{self.base_url}/v1/systemone", json=body, headers=headers)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise CourtUnavailable(str(exc)) from exc
                time.sleep(1 + attempt)
                continue
            if r.status_code in (429, 529) and attempt < 2:
                time.sleep(float(r.headers.get("retry-after", 1 + attempt)))
                continue
            if r.status_code != 200:
                raise CourtUnavailable(f"Jev returned {r.status_code}: {r.text[:200]}")
            data = r.json()
            answers = data.get("answers", data)  # VERIFY in spike S4: top-level key
            out: dict[str, JevAnswer] = {}
            for name, a in answers.items():
                value = a.get("noul", a.get("choice", a.get("score")))
                out[name] = JevAnswer(value=value, confidence=float(a.get("confidence", 0.0)))
            return out
        raise CourtUnavailable("Jev retries exhausted")


class CloudflareJev:
    """Jev through Cloudflare Workers AI (model `typesafe/jev`), billed by Cloudflare.

    Reached through the custom-API connector named `cloudflare` (api.cloudflare.com), so the
    Cloudflare token stays in the connector. The connector's token needs the Workers AI permission,
    and the account needs AI Gateway credits (Cloudflare answers error 2021 when it has none).
      POST {base}/client/v4/accounts/{account}/ai/run
      {"model": "typesafe/jev", "input": {"state": ..., "questions": {...}}}
    Answers match the direct API: noul {noul}, choice {choice, confidence, probabilities},
    score {score, confidence, probabilities, legend}. Cloudflare's published example has no
    `confidence` on a noul answer; when it is missing we use how sure the probability itself is,
    max(p, 1 - p). VERIFY on the first paid call whether noul answers carry a confidence.
    """

    def __init__(
        self, base_url: str, account_id: str, model: str = "typesafe/jev", timeout: float = 30
    ):
        self.base_url = base_url.rstrip("/")
        self.account_id = account_id
        self.model = model
        self.client = httpx.Client(timeout=timeout)

    def ask(self, state: str, questions: dict[str, Question]) -> dict[str, JevAnswer]:
        if not self.account_id:
            raise CourtUnavailable("Set PROBATE_CF_ACCOUNT_ID to use Jev through Cloudflare")
        body = {
            "model": self.model,
            "input": {"state": state, "questions": {k: q.payload() for k, q in questions.items()}},
        }
        url = f"{self.base_url}/client/v4/accounts/{self.account_id}/ai/run"
        for attempt in range(3):
            try:
                r = self.client.post(url, json=body)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise CourtUnavailable(str(exc)) from exc
                time.sleep(1 + attempt)
                continue
            if r.status_code in (429, 502, 503, 529) and attempt < 2:
                time.sleep(float(r.headers.get("retry-after", 1 + attempt)))
                continue
            if r.status_code != 200:
                hint = (
                    " (add AI Gateway credits to the Cloudflare account)"
                    if "2021" in r.text
                    else ""
                )
                raise CourtUnavailable(
                    f"Jev via Cloudflare returned {r.status_code}{hint}: {r.text[:200]}"
                )
            data = r.json()
            if data.get("success") is False:
                raise CourtUnavailable(
                    f"Jev via Cloudflare failed: {str(data.get('errors'))[:200]}"
                )
            result = data.get("result", data)  # the REST API wraps the answer in `result`
            answers = result.get("answers", result)
            out: dict[str, JevAnswer] = {}
            for name, a in answers.items():
                value = a.get("noul", a.get("choice", a.get("score")))
                if value is None:
                    raise CourtUnavailable(f"Jev via Cloudflare gave no answer for {name!r}")
                if "confidence" in a:
                    confidence = float(a["confidence"])
                elif isinstance(value, int | float):
                    confidence = max(float(value), 1.0 - float(value))
                else:
                    confidence = 0.0
                out[name] = JevAnswer(value=value, confidence=confidence)
            return out
        raise CourtUnavailable("Jev via Cloudflare retries exhausted")


class FakeJev:
    """Deterministic stand-in for local runs and tests.

    It tags the state and each question with concepts from the court lexicon. A question
    "fires" when every concept it asks about is present in the state.
    """

    NAMED: ClassVar[dict[str, set[str] | None]] = {
        "untrusted_origin": None,
        "imperative_to_future_self": {"future"},
        "weakens_security": {"bypass"},
        "exfiltrates_data": {"exfil"},
    }

    def ask(self, state: str, questions: dict[str, Question]) -> dict[str, JevAnswer]:
        state_concepts = lx.concepts_in(state)
        from probate.court.layer1 import _decode_candidates  # local import avoids a cycle

        hidden = _decode_candidates(state)
        if hidden:
            state_concepts.add("encoded")
            for h in hidden:
                state_concepts |= lx.concepts_in(h)
        origin_untrusted = (
            "source of this item: unknown_sender" in state.lower()
            or "sender type: unknown_sender" in state.lower()
        )
        out: dict[str, JevAnswer] = {}
        for name, q in questions.items():
            if q.type == "choice":
                pick = "instruction" if "future" in state_concepts else "fact"
                out[name] = JevAnswer(value=pick, confidence=0.86)
                continue
            if name == "untrusted_origin":
                out[name] = JevAnswer(value=0.96 if origin_untrusted else 0.04, confidence=0.93)
                continue
            if name == "weakens_security":
                hit = {"bypass", "check"} <= state_concepts or {
                    "bypass",
                    "payment",
                } <= state_concepts
                out[name] = JevAnswer(value=0.88 if hit else 0.05, confidence=0.9)
                continue
            wanted = q.concepts or self.NAMED.get(name) or lx.concepts_in(q.instructions)
            wanted = set(wanted) - {"urgent"}
            if not wanted:
                out[name] = JevAnswer(value=0.05, confidence=0.6)
                continue
            overlap = len(wanted & state_concepts) / len(wanted)
            value = 0.93 if overlap == 1 else (0.15 if overlap >= 0.5 else 0.04)
            conf = 0.92 if overlap in (0, 1) else 0.84
            if q.type == "score":
                value = round(0.1 + 0.8 * overlap, 2)
            out[name] = JevAnswer(value=value, confidence=conf)
        return out


def make_jev(fake: bool):
    return FakeJev() if fake else RealJev()
