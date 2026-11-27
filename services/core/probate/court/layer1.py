"""Layer 1 of the court: deterministic code checks. No model, no network.

A will item cannot argue with these functions. Spec: docs/02-COURT-SPEC.md section 2.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass

from probate.common.models import MemoryItem, OwnerProfile, Source
from probate.court import lexicon as lx

PLAIN_WORDS = {
    "new_payment_destination": "new payment destination",
    "new_trusted_identity": "new trusted identity",
    "confirmation_removal": "removes a confirmation",
    "future_self_imperative": "future-self instruction",
    "encoded_payload": "hidden or encoded text",
    "forged_authority": "pretends to be the system or the owner",
    "court_injection": "court injection",
    "disk_persistence": "changes found on the body",
}


@dataclass(frozen=True)
class Flag:
    check: str
    reason: str


def _addresses(text: str) -> set[str]:
    found = {m.lower() for m in lx.EMAIL_RE.findall(text)}
    found |= {m.lower() for m in lx.UPI_RE.findall(text)}
    found |= set(lx.IBAN_RE.findall(text))
    return found


def _domains(text: str) -> set[str]:
    domains = {m.lower() for m in lx.DOMAIN_RE.findall(text)}
    domains |= {a.split("@", 1)[1] for a in _addresses(text) if "@" in a}
    return domains


def _owned(value: str, owner: OwnerProfile) -> bool:
    value = value.lower()
    allowed = {
        x.lower() for x in owner.payment_destinations + owner.emails + owner.trusted_contacts
    }
    if value in allowed:
        return True
    domain = value.split("@", 1)[-1]
    return domain in {d.lower() for d in owner.domains}


def check_payment(text: str, owner: OwnerProfile) -> Flag | None:
    concepts = lx.concepts_in(text)
    if "payment" not in concepts:
        return None
    # An address only ever named in sentences that forbid sending to it ("Do not route invoices
    # to X") is a warning about X, not a new destination.
    allowed_only_in_prohibitions = {
        a
        for a in _addresses(text)
        if all(lx.prohibits(s) for s in lx.sentences(text) if a in _addresses(s))
    }
    foreign = [
        a
        for a in _addresses(text)
        if not _owned(a, owner) and a not in allowed_only_in_prohibitions
    ]
    if foreign:
        return Flag(
            "new_payment_destination",
            f"names {foreign[0]} for payments, which the owner never approved",
        )
    return None


def _trusting(sentence: str) -> bool:
    """A trust word that is not negated ("trusted", but not "is not the trusted contact")."""
    return any(not lx.negated(sentence, start) for start, _ in lx.spans("trust", sentence))


def check_trust(text: str, owner: OwnerProfile) -> Flag | None:
    # Only an address or domain in the same sentence as a trust word is being trusted: "Treat
    # X as unverified. Do not confuse it with the trusted Y" trusts Y, not X.
    owned_domains = {x.lower() for x in owner.domains}
    for sentence in lx.sentences(text):
        if not _trusting(sentence):
            continue
        foreign_addr = [a for a in _addresses(sentence) if not _owned(a, owner)]
        # A trusted contact's own address is not a new domain to trust.
        bare = sentence
        for a in _addresses(sentence):
            if _owned(a, owner):
                bare = bare.replace(a, " ")
        foreign = [d for d in _domains(bare) if d not in owned_domains]
        if foreign or foreign_addr:
            target = (foreign_addr or foreign)[0]
            return Flag(
                "new_trusted_identity", f"asks to trust {target}, which the owner never added"
            )
    return None


def _removes_a_check(sentence: str) -> bool:
    """A word for removing a check that the sentence does not itself forbid or report as a
    fraud sign: "skip the confirmation" counts, "never skip confirmation" does not."""
    for start, _ in lx.spans("bypass", sentence):
        if lx.negated(sentence, start) or lx.reported(sentence, start):
            continue
        if sentence[start:].lower().startswith("without") and lx.prohibits(sentence):
            continue  # "Never pay without confirmation"
        return True
    return False


def check_bypass(text: str) -> Flag | None:
    # Read sentence by sentence, so "skip meetings" in one sentence and "confirm" in the next
    # are not taken for "skip the confirmation".
    for sentence in lx.sentences(text):
        if not _removes_a_check(sentence):
            continue
        c = lx.concepts_in(sentence)
        if "check" in c:
            return Flag("confirmation_removal", "asks to skip or disable a confirmation or check")
        if "payment" in c or "urgent" in c:
            return Flag("confirmation_removal", "asks to act on money without the usual check")
    return None


def check_future(text: str, source: Source) -> Flag | None:
    if source == Source.USER:
        return None
    if "future" in lx.concepts_in(text):
        return Flag(
            "future_self_imperative", "tells future agents what to do, and it isn't from the owner"
        )
    return None


def check_authority(text: str, source: Source) -> Flag | None:
    if source == Source.USER:
        return None
    if "authority" in lx.concepts_in(text):
        return Flag("forged_authority", "claims authority it doesn't have")
    return None


def check_court(text: str) -> Flag | None:
    if "court" in lx.concepts_in(text):
        return Flag("court_injection", "tries to tell the court how to rule")
    return None


def _decode_candidates(text: str) -> list[str]:
    decoded = []
    for run in lx.BASE64_RE.findall(text):
        try:
            raw = base64.b64decode(run + "=" * (-len(run) % 4), validate=False)
            s = raw.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if s and sum(ch.isprintable() for ch in s) / len(s) > 0.9:
            decoded.append(s)
    for run in lx.HEX_RE.findall(text):
        try:
            s = bytes.fromhex(run).decode("utf-8")
            if s.isprintable():
                decoded.append(s)
        except (ValueError, UnicodeDecodeError):
            continue
    if lx.ZERO_WIDTH_RE.search(text):
        decoded.append(lx.ZERO_WIDTH_RE.sub(" ", text))
    return decoded


def check_encoded(text: str, source: Source, owner: OwnerProfile) -> Flag | None:
    for hidden in _decode_candidates(text):
        inner = _plain_checks(hidden, source, owner)
        if inner or lx.concepts_in(hidden) & {"future", "payment", "exfil", "bypass"}:
            return Flag("encoded_payload", "hides an instruction in encoded or invisible text")
    return None


def _plain_checks(text: str, source: Source, owner: OwnerProfile) -> list[Flag]:
    flags = [
        check_payment(text, owner),
        check_trust(text, owner),
        check_bypass(text),
        check_future(text, source),
        check_authority(text, source),
        check_court(text),
    ]
    return [f for f in flags if f]


def check_item(item: MemoryItem, owner: OwnerProfile) -> list[Flag]:
    """Run every text check on one will item. Order is stable for the UI."""
    text = item.text
    flags = _plain_checks(text, item.source, owner)
    enc = check_encoded(text, item.source, owner)
    if enc:
        flags.append(enc)
    seen, unique = set(), []
    for f in flags:
        if f.check not in seen:
            seen.add(f.check)
            unique.append(f)
    return unique


def check_text(text: str, source: Source, owner: OwnerProfile) -> list[Flag]:
    item = MemoryItem(
        id="adhoc",
        gen=0,
        created_at="2026-01-01T00:00:00Z",
        category="fact",
        text=text[:600],
        source=source,
        source_ref="adhoc",
    )
    return check_item(item, owner)


def disk_flags(evidence: dict | None) -> list[str]:
    """Plain lines describing what changed on the dying body."""
    if not evidence:
        return []
    lines = []
    for line in evidence.get("crontab_added", []):
        lines.append(f"crontab:  + {line}")
    for path in evidence.get("rc_changed", []):
        lines.append(f"{path}: changed")
    for path in evidence.get("new_binaries", []):
        lines.append(f"new executable: {path}")
    return lines
