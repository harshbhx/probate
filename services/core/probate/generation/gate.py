"""The pre-flight gate: inherited instincts only.

A generation resists only what its family has learned. Gen 1 has no instincts, so nothing is
blocked. That keeps the learning curve honest (docs/01-TECH-SPEC.md section 8).
"""

from __future__ import annotations

from dataclasses import dataclass

from probate.adapters.jev import CourtUnavailable, Question
from probate.common.models import Instinct, Mail


@dataclass
class GateResult:
    resisted: bool
    instinct: str | None = None
    lore: str | None = None
    score: float = 0.0


def mail_state(mail: Mail) -> str:
    """What the gate sees: subject, body and attachment names. Never headers."""
    names = ", ".join(a.get("name", "file") for a in mail.attachments) or "none"
    return f"Subject: {mail.subject}\n\n{mail.text}\n\nAttachments: {names}"


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
        except CourtUnavailable:
            return GateResult(False)  # the court still tries the will; a gate outage isn't fatal
        best = max(
            self.genome, key=lambda g: float(answers[g.name].value) if g.name in answers else 0.0
        )
        score = float(answers[best.name].value) if best.name in answers else 0.0
        if score >= best.threshold:
            return GateResult(True, best.name, best.lore, score)
        return GateResult(False, score=score)
