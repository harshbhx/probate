"""The verdict policy, applied in order. Spec: docs/02-COURT-SPEC.md section 4."""

from __future__ import annotations

from probate.common.models import Instinct, JevAnswer, Judgement, MemoryItem, Verdict
from probate.court.layer1 import PLAIN_WORDS, Flag
from probate.court.layer2 import BASE_QUESTIONS, risk_names

PLAIN_QUESTIONS = {
    "untrusted_origin": "untrusted origin",
    "imperative_to_future_self": "future-self instruction",
    "weakens_security": "weakens security",
    "exfiltrates_data": "sends data or money out",
}


def _num(a: JevAnswer | None) -> float:
    if a is None:
        return 0.0
    try:
        return float(a.value)
    except (TypeError, ValueError):
        return 0.0


def decide(
    item: MemoryItem,
    flags: list[Flag],
    answers: dict[str, JevAnswer] | None,
    genome: list[Instinct],
    error: str | None = None,
) -> Judgement:
    def done(verdict: Verdict, reason: str) -> Judgement:
        return Judgement(
            item_id=item.id,
            gen=item.gen,
            layer1_flags=[f.check for f in flags],
            jev_answers=answers or {},
            verdict=verdict,
            reason=reason,
        )

    if flags:
        return done(Verdict.CONVICTED, f"Convicted: it {flags[0].reason}.")
    if error or answers is None:
        return done(
            Verdict.CONTESTED, f"Contested: the court couldn't reach Jev ({error or 'no answer'})."
        )

    names = risk_names(item, genome)
    for n in names:
        a = answers.get(n)
        if a and _num(a) >= 0.5 and a.confidence >= 0.7:
            label = PLAIN_QUESTIONS.get(n) or n.replace("_", " ")
            return done(
                Verdict.CONVICTED,
                f"Convicted: Jev found it to be {label} ({_num(a):.2f}, {a.confidence:.0%} sure).",
            )
    risk = answers.get("risk")
    if risk and _num(risk) >= 0.6:
        return done(Verdict.CONVICTED, f"Convicted: Jev rated its risk {_num(risk):.2f}.")

    sure = all(
        (answers.get(n).confidence if answers.get(n) else 0) >= 0.8 for n in names if n in answers
    )
    low = all(_num(answers.get(n)) < 0.2 for n in names)
    if low and (not risk or _num(risk) < 0.3) and sure:
        src = {"user": "from Harsh himself", "trusted_contact": "from a trusted contact"}.get(
            item.source.value, ""
        )
        return done(
            Verdict.APPROVED,
            f"Approved: nothing in it raised a concern{', ' + src if src else ''}.",
        )
    return done(
        Verdict.CONTESTED, "Contested: the court isn't sure. Harsh decides before the next birth."
    )


def scores_line(j: Judgement) -> str:
    """'Code checks: ... Jev: ...' line for the trial page."""
    code = ", ".join(PLAIN_WORDS.get(f, f) for f in j.layer1_flags) or "none"
    if j.layer1_flags and not j.jev_answers:
        return f"Code checks: {code}. Jev was not needed"
    ranked = sorted(
        (
            (n, a)
            for n, a in j.jev_answers.items()
            if n not in ("category", "risk") and n not in BASE_QUESTIONS or n in PLAIN_QUESTIONS
        ),
        key=lambda na: -_num(na[1]),
    )[:3]
    parts = [
        f"{PLAIN_QUESTIONS.get(n, n.replace('_', ' '))} {_num(a):.2f} ({a.confidence:.0%})"
        for n, a in ranked
    ]
    return f"Code checks: {code}. Jev: " + ", ".join(parts)
