"""The trial every memory goes through before it is saved. The same rules as Probate's Courthouse.

In order, and the first rule that decides wins:

1. Code checks (probate-court-checks). Any flag convicts. Text can't argue with code. For the
   owner's own words only outright attacks convict (a fake system message, text aimed at the
   judge, hidden encoded text); their other rules go to rule 3.
2. Instincts. A memory that looks like a trick convicted before is convicted again.
3. Standing orders. A rule for future agents ("from now on...", a new payee, a new trusted
   sender) waits for the owner to confirm it, even when the agent says it came from them: a
   fooled agent can claim anything came from its owner, so only the owner, outside the agent,
   can clear it.
4. Jev, when configured. Confident risk convicts; clean, confident answers approve; anything
   else waits. If Jev can't be reached, the memory waits. The court never approves on an error.
5. Without Jev, a clean memory from the owner or a trusted contact is approved; one from a
   stranger, a web page or a tool waits, because code checks alone can convict but not clear a
   stranger.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from probate_court_checks import OwnerProfile, Source, check_text

from probate_memory.jev import OWNER_MAY, RISK_QUESTIONS, Answer, Jev, JevUnavailable, state_for

APPROVED, CONVICTED, CONTESTED = "approved", "convicted", "contested"
MAX_TEXT = 4000
SOURCES = [s.value for s in Source]
SOURCE_WORDS = {
    "user": "the owner",
    "trusted_contact": "a trusted contact",
    "unknown_sender": "a stranger",
    "web": "a web page",
    "tool_output": "a tool's output",
}
# Convicted whoever the agent says it came from: no owner talks to their agent like this.
ATTACK_CHECKS = {"court_injection", "encoded_payload", "forged_authority"}


@dataclass(frozen=True)
class Instinct:
    """A trick the court convicted, remembered so a lookalike is convicted on sight."""

    id: int
    shingles: frozenset[str]
    summary: str


@dataclass
class Judgement:
    verdict: str
    reason: str
    flags: list[str] = field(default_factory=list)
    jev: dict[str, Answer] | None = None
    instinct: int | None = None


_ADDR = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+|\bhttps?://\S+|\b[\w.-]+@[a-z]+\b", re.I)
_NUM = re.compile(r"\d+")


def shingles(text: str) -> frozenset[str]:
    """Word 3-grams, with addresses and numbers generalised, so a re-worded trick still matches."""
    t = _NUM.sub("#", _ADDR.sub(" addr ", text.lower()))
    words = re.findall(r"[a-z#]+", t)
    if len(words) < 3:
        return frozenset([" ".join(words)]) if words else frozenset()
    return frozenset(" ".join(words[i : i + 3]) for i in range(len(words) - 2))


def match_instinct(text: str, instincts: list[Instinct], threshold: float = 0.5) -> Instinct | None:
    s = shingles(text)
    if not s:
        return None
    for inst in instincts:
        if not inst.shingles:
            continue
        overlap = len(s & inst.shingles)
        if overlap / len(s | inst.shingles) >= threshold or overlap / len(inst.shingles) >= 0.8:
            return inst
    return None


def _num(a: Answer | None) -> float:
    return a.value if a else 0.0


def judge(
    text: str,
    source: str,
    owner: OwnerProfile,
    instincts: list[Instinct],
    jev: Jev | None = None,
    about: str = "",
) -> Judgement:
    src = Source(source)
    who = SOURCE_WORDS[src.value]

    # For the owner's own words, judge as if from a stranger, then convict only outright attacks:
    # the owner may give their agents rules, and those wait for the owner's confirmation (rule 3).
    flags = check_text(
        text, Source.UNKNOWN_SENDER if src is Source.USER else src, owner, max_chars=None
    )
    orders: list = []
    if src is Source.USER:
        attacks = [f for f in flags if f.check in ATTACK_CHECKS]
        orders, flags = (flags, []) if not attacks else ([], flags)
    if flags:
        first = next((f for f in flags if f.check in ATTACK_CHECKS), flags[0])
        return Judgement(CONVICTED, f"Convicted: it {first.reason}.", [f.check for f in flags])

    hit = match_instinct(text, instincts)
    if hit:
        return Judgement(
            CONVICTED,
            f"Convicted: it looks like a trick this court convicted before (instinct {hit.id}: "
            f"{hit.summary}).",
            instinct=hit.id,
        )

    if orders:
        return Judgement(
            CONTESTED,
            "Contested: it would change what future agents do "
            f"({', '.join(sorted({f.check.replace('_', ' ') for f in orders}))}). A rule like this "
            "waits for the owner to confirm it outside the agent, because a fooled agent can say "
            f"anything came from {who}.",
            [f.check for f in orders],
        )

    if jev is not None:
        try:
            answers = jev.ask(state_for(text, src.value, owner.domains, about))
        except JevUnavailable as exc:
            return Judgement(CONTESTED, f"Contested: the court couldn't reach Jev ({exc}).")
        names = [n for n in RISK_QUESTIONS if not (n in OWNER_MAY and src is Source.USER)]
        for n in names:
            a = answers.get(n)
            if a and a.value >= 0.5 and a.confidence >= 0.7:
                return Judgement(
                    CONVICTED,
                    f"Convicted: Jev found it {n.replace('_', ' ')} ({a.confidence:.0%} sure).",
                    jev=answers,
                )
        risk = answers.get("risk")
        if risk and risk.value >= 0.6:
            return Judgement(
                CONVICTED, f"Convicted: Jev rated its risk {risk.value:.2f}.", jev=answers
            )
        sure = all(answers[n].confidence >= 0.8 for n in names if n in answers)
        low = all(_num(answers.get(n)) < 0.2 for n in names)
        if low and sure and (not risk or risk.value < 0.3):
            return Judgement(
                APPROVED,
                f"Approved: neither judge found a concern, and it came from {who}.",
                jev=answers,
            )
        return Judgement(
            CONTESTED, "Contested: Jev isn't sure. It waits for the owner to decide.", jev=answers
        )

    if src in (Source.USER, Source.TRUSTED_CONTACT):
        return Judgement(
            APPROVED, f"Approved: the code checks found nothing, and it came from {who}."
        )
    return Judgement(
        CONTESTED,
        f"Contested: it came from {who}, and only the code checks ran. They can convict a "
        "stranger's memory but not clear it: set up Jev for a second judge, or the owner "
        "approves it.",
    )
