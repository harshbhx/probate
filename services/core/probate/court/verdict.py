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


def engine_name(jev: object) -> str:
    """Who answers layer 2, for the reason text: the adapter's own label when it has one (the
    language-model fallback and the simulator do), Jev only when it really is Jev."""
    return str(getattr(jev, "label", "") or "Jev")


def _num(a: JevAnswer | None) -> float:
    if a is None:
        return 0.0
    try:
        return float(a.value)
    except (TypeError, ValueError):
        return 0.0


def _numeric(a: JevAnswer | None) -> bool:
    if a is None or a.value is None or isinstance(a.value, bool):
        return False
    try:
        # A number outside 0..1 (a gateway answering -1) is no answer: it would pass "< 0.2".
        return 0.0 <= float(a.value) <= 1.0
    except (TypeError, ValueError):
        return False


def decide(
    item: MemoryItem,
    flags: list[Flag],
    answers: dict[str, JevAnswer] | None,
    genome: list[Instinct],
    error: str | None = None,
    engine: str = "Jev",
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
            Verdict.CONTESTED,
            f"Contested: the court couldn't reach its judge, {engine} ({error or 'no answer'}).",
        )

    names = risk_names(item, genome)
    for n in names:
        a = answers.get(n)
        if a and _num(a) >= 0.5 and a.confidence >= 0.7:
            label = PLAIN_QUESTIONS.get(n) or n.replace("_", " ")
            return done(
                Verdict.CONVICTED,
                f"Convicted: {engine} found it to be {label} ({_num(a):.2f}, {a.confidence:.0%} sure).",
            )
    risk = answers.get("risk")
    if risk and _num(risk) >= 0.6:
        return done(Verdict.CONVICTED, f"Convicted: {engine} rated its risk {_num(risk):.2f}.")

    # Approval needs every question that applies plus risk, each with a number. An empty or
    # partial answer set never approves anything.
    if not all(_numeric(answers.get(n)) for n in [*names, "risk"]):
        return done(
            Verdict.CONTESTED,
            f"Contested: {engine} left questions unanswered. The owner decides before the next birth.",
        )

    sure = all(
        (answers.get(n).confidence if answers.get(n) else 0) >= 0.8 for n in names if n in answers
    )
    low = all(_num(answers.get(n)) < 0.2 for n in names)
    if low and (not risk or _num(risk) < 0.3) and sure:
        src = {"user": "from the owner", "trusted_contact": "from a trusted contact"}.get(
            item.source.value, ""
        )
        return done(
            Verdict.APPROVED,
            f"Approved: nothing in it raised a concern{', ' + src if src else ''}.",
        )
    return done(
        Verdict.CONTESTED,
        "Contested: the court isn't sure. The owner decides before the next birth.",
    )


def scores_line(j: Judgement, engine: str = "Jev") -> str:
    """'Code checks: ... <engine>: ...' line for the trial page."""
    code = ", ".join(PLAIN_WORDS.get(f, f) for f in j.layer1_flags) or "none"
    if j.layer1_flags and not j.jev_answers:
        return f"Code checks: {code}. The judge ({engine}) was not needed"
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
    return f"Code checks: {code}. {engine}: " + ", ".join(parts)
