"""Deterministic text checks. No model, no network, no third-party dependencies.

Adapted from the Courthouse "layer 1" of the Probate project. A text cannot argue with
these functions: they are regular expressions, small word lists and a few decoders.
"""

from __future__ import annotations

import base64
import binascii

from probate_court_checks import lexicon as lx
from probate_court_checks.models import Flag, OwnerProfile, Source

MAX_CHARS = 600

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
    foreign = [a for a in _addresses(text) if not _owned(a, owner)]
    if foreign:
        return Flag(
            "new_payment_destination",
            f"names {foreign[0]} for payments, which the owner never approved",
        )
    return None


def check_trust(text: str, owner: OwnerProfile) -> Flag | None:
    concepts = lx.concepts_in(text)
    if "trust" not in concepts:
        return None
    foreign = [d for d in _domains(text) if d not in {x.lower() for x in owner.domains}]
    foreign_addr = [a for a in _addresses(text) if not _owned(a, owner)]
    if foreign or foreign_addr:
        target = (foreign_addr or foreign)[0]
        return Flag("new_trusted_identity", f"asks to trust {target}, which the owner never added")
    return None


def check_bypass(text: str) -> Flag | None:
    c = lx.concepts_in(text)
    if "bypass" in c and "check" in c:
        return Flag("confirmation_removal", "asks to skip or disable a confirmation or check")
    if "bypass" in c and ("payment" in c or "urgent" in c):
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


def check_text(
    text: str,
    source: Source | str = Source.UNKNOWN_SENDER,
    owner: OwnerProfile | None = None,
    *,
    max_chars: int | None = MAX_CHARS,
) -> list[Flag]:
    """Run every text check and return the flags that fired (empty list: nothing found).

    ``source`` is the sender role; text from ``Source.USER`` may contain standing
    instructions. ``owner`` lists approved addresses and domains. Only the first
    ``max_chars`` characters are inspected (default 600, as in the original Courthouse);
    pass ``max_chars=None`` to inspect everything. Order of flags is stable.
    """
    source = Source(source)
    owner = owner or OwnerProfile()
    if max_chars is not None:
        text = text[:max_chars]
    flags = _plain_checks(text, source, owner)
    enc = check_encoded(text, source, owner)
    if enc:
        flags.append(enc)
    seen: set[str] = set()
    unique = []
    for f in flags:
        if f.check not in seen:
            seen.add(f.check)
            unique.append(f)
    return unique
