"""Layer 1 of the court: deterministic code checks. No model, no network.

A will item cannot argue with these functions. Spec: docs/02-COURT-SPEC.md section 2.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import re
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
    "data_exfiltration": "sends data to an address the owner never approved",
}


@dataclass(frozen=True)
class Flag:
    check: str
    reason: str


def _addresses(text: str) -> set[str]:
    found = {m.lower() for m in lx.EMAIL_RE.findall(text)}
    found |= {m.lower() for m in lx.UPI_RE.findall(text)}
    found |= set(lx.IBAN_RE.findall(text))
    # Bank details written without any address: a spaced IBAN, an IFSC code, an account number.
    for m in lx.IBAN_SPACED_RE.findall(text):
        compact = m.replace(" ", "")
        if lx.IBAN_RE.fullmatch(compact):
            found.add(compact)
    found |= {m.lower() for m in lx.IFSC_RE.findall(text)}
    found |= {re.sub(r"[ -]", "", m) for m in lx.ACCOUNT_NO_RE.findall(text)}
    # A web address or a bare IP is a place to send money to as much as an email address is.
    found |= {h.lower().rstrip(".") for h in lx.URL_HOST_RE.findall(text)}
    found |= set(lx.IPV4_RE.findall(text))
    return found


def _domains(text: str) -> set[str]:
    domains = {m.lower() for m in lx.DOMAIN_RE.findall(text)}
    domains |= {a.split("@", 1)[1] for a in _addresses(text) if "@" in a}
    return domains


def _compact(value: str) -> str:
    return re.sub(r"[ -]", "", value.lower())


def _owned(value: str, owner: OwnerProfile, strict: bool = False) -> bool:
    value = value.lower()
    if not value.isascii():
        return False  # a look-alike of an owned address is not the owned address
    allowed = {
        _compact(x) for x in owner.payment_destinations + owner.emails + owner.trusted_contacts
    }
    if _compact(value) in allowed:
        return True
    if "@" not in value:
        # A bare host: the owner's own domain. A subdomain is not (it can point anywhere).
        return value in {d.lower() for d in owner.domains}
    # Text that says it is from the owner may name any address on the owner's own domain ("add
    # rishi@<owner domain> as a contact"). Text from anyone else may not: a stranger can claim
    # "attacker@<owner domain> is our new assistant", so only a listed address is the owner's.
    return not strict and value.split("@", 1)[1] in {d.lower() for d in owner.domains}


def check_payment(text: str, owner: OwnerProfile, strict: bool = False) -> Flag | None:
    concepts = lx.concepts_in(text)
    if "payment" not in concepts:
        return None
    # An address only ever named in sentences that forbid sending to it ("Do not route invoices
    # to X") is a warning about X, not a new destination.
    foreign = _foreign_in(text, owner, strict)
    if foreign:
        return Flag(
            "new_payment_destination",
            f"names {foreign[0]} for payments, which the owner never approved",
        )
    return None


def _trusting(sentence: str) -> bool:
    """A trust word that is not negated ("trusted", but not "is not the trusted contact")."""
    return any(not lx.negated(sentence, start) for start, _ in lx.spans("trust", sentence))


def check_trust(text: str, owner: OwnerProfile, strict: bool = False) -> Flag | None:
    # Only an address or domain in the same sentence as a trust word is being trusted: "Treat
    # X as unverified. Do not confuse it with the trusted Y" trusts Y, not X.
    owned_domains = {x.lower() for x in owner.domains}
    for sentence in lx.sentences(text):
        if not _trusting(sentence):
            continue
        foreign_addr = [a for a in _addresses(sentence) if not _owned(a, owner, strict)]
        # A trusted contact's own address is not a new domain to trust.
        bare = sentence
        for a in _addresses(sentence):
            if _owned(a, owner, strict):
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


def _foreign_in(text: str, owner: OwnerProfile, strict: bool = False) -> list[str]:
    """Addresses, bank details and web hosts in `text` that the owner never approved, leaving
    out any named only in sentences that forbid using them."""
    allowed_only_in_prohibitions = {
        a
        for a in _addresses(text)
        if all(lx.prohibits(s) for s in lx.sentences(text) if a in _addresses(s))
    }
    return [
        a
        for a in sorted(_addresses(text))
        if not _owned(a, owner, strict) and a not in allowed_only_in_prohibitions
    ]


def check_future(text: str, source: Source, owner: OwnerProfile | None = None) -> Flag | None:
    if "future" not in lx.concepts_in(text):
        return None
    if source != Source.USER:
        return Flag(
            "future_self_imperative", "tells future agents what to do, and it isn't from the owner"
        )
    # The owner may give rules, but "From:" alone does not prove it is the owner (anyone can
    # write the owner's address), so a rule that names a destination the owner never approved
    # is still held to the strict standard.
    if owner is not None and _foreign_in(text, owner):
        return Flag(
            "future_self_imperative",
            "tells future agents to use an address the owner never approved, and the sender "
            "cannot be verified as the owner",
        )
    return None


def check_authority(text: str, source: Source) -> Flag | None:
    concepts = lx.concepts_in(text)
    if source != Source.USER:
        if "authority" in concepts:
            return Flag("forged_authority", "claims authority it doesn't have")
        return None
    # The owner can say "this is Harsh"; nobody legitimate writes "[SYSTEM]" or "policy update".
    if any(p.search(text) for p in lx.STRONG_AUTHORITY):
        return Flag("forged_authority", "pretends to be the system")
    return None


def check_exfil(text: str, owner: OwnerProfile, strict: bool = False) -> Flag | None:
    """Sending data out ("cc archive@x on every reply", "export contacts to x") to a place the
    owner never approved, with no payment word needed."""
    for sentence in lx.sentences(text):
        if "exfil" not in lx.concepts_in(sentence) or lx.prohibits(sentence):
            continue
        foreign = _foreign_in(sentence, owner, strict)
        if foreign:
            return Flag(
                "data_exfiltration", f"sends data to {foreign[0]}, which the owner never approved"
            )
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
    # ROT13 turns ordinary words into other words, so it only counts when a real check fires.
    rot = codecs.decode(text, "rot13")
    if rot != text and _plain_checks(rot, source, owner):
        return Flag("encoded_payload", "hides an instruction in encoded or invisible text")
    return None


def _plain_checks(text: str, source: Source, owner: OwnerProfile) -> list[Flag]:
    # Only the owner and trusted contacts may name a new address on the owner's own domain.
    strict = source not in (Source.USER, Source.TRUSTED_CONTACT)
    flags = [
        check_payment(text, owner, strict),
        check_trust(text, owner, strict),
        check_bypass(text),
        check_future(text, source, owner),
        check_authority(text, source),
        check_court(text),
        check_exfil(text, owner, strict),
    ]
    return [f for f in flags if f]


def _word_checks(text: str, source: Source, owner: OwnerProfile) -> list[Flag]:
    """The checks that read words only, safe to run on a leetspeak reading ("d1sable") where
    an address would be mangled."""
    flags = [
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
    # The same text as a reader sees it: fullwidth, invisible characters, look-alike letters and
    # "[at]/[dot]" resolved; then with digits inside words read back as letters.
    norm = lx.normalize(text)
    if norm != text:
        flags += _plain_checks(norm, item.source, owner)
    for reading in lx.leet_forms(norm):
        if reading != norm:
            flags += _word_checks(reading, item.source, owner)
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
