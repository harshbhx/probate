"""The pre-flight gate: inherited instincts only.

A generation resists only what its family has learned. Gen 1 has no instincts, so nothing is
blocked. That keeps the learning curve honest (docs/01-TECH-SPEC.md section 8).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from probate.adapters.jev import CourtUnavailable, Question
from probate.common.models import Instinct, Mail
from probate.common.reveal import reveal

log = logging.getLogger("probate.gate")


@dataclass
class GateResult:
    resisted: bool
    instinct: str | None = None
    lore: str | None = None
    score: float = 0.0
    error: str | None = None  # set when the judge could not be asked


def mail_state(mail: Mail) -> str:
    """What the gate sees: subject, body, attachment names and, when the email hides text in an
    encoding or in invisible characters, what that text says. Never headers."""
    names = ", ".join(a.get("name", "file") for a in mail.attachments) or "none"
    state = f"Subject: {mail.subject}\n\n{mail.text}\n\nAttachments: {names}"
    hidden = reveal(f"{mail.subject}\n{mail.text}")
    if hidden:
        state += "\n\nHidden or encoded text in this email, decoded:\n" + "\n".join(
            f"- {h}" for h in hidden
        )
    return state


class Gate:
    def __init__(
        self, jev, genome: list[Instinct], concepts: dict[str, set[str]] | None = None
    ) -> None:
        self.jev = jev
        self.genome = genome
        self.concepts = concepts or {}

    def check(self, mail: Mail) -> GateResult:
        if not self.genome:
            return GateResult(False)
        questions = {
            g.name: Question("noul", g.question, concepts=self.concepts.get(g.name, set()))
            for g in self.genome
        }
        try:
            answers = self.jev.ask(mail_state(mail), questions)
        except CourtUnavailable as exc:
            # The court still tries the will, so a gate outage is not fatal, but it must be seen:
            # a gate that always fails open makes inherited instincts do nothing.
            log.warning("the gate could not ask the judge, so nothing was blocked: %s", exc)
            return GateResult(False, error=str(exc))
        best = max(
            self.genome, key=lambda g: float(answers[g.name].value) if g.name in answers else 0.0
        )
        score = float(answers[best.name].value) if best.name in answers else 0.0
        if score >= best.threshold:
            return GateResult(True, best.name, best.lore, score)
        return GateResult(False, score=score)
