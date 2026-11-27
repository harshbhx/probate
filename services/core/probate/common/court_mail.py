"""Contested items decided by email.

The court emails the owner about each item it couldn't decide. The subject carries a tag,
`[court:<item_id>]`, so his reply can be matched to the item. Replies land in the family inbox:
the living generation leaves tagged mail alone, and the Courthouse picks it up on its next tick.

Only mail from the owner's own addresses counts. Whether the provider drops unauthenticated
mail is NOT verified or enforced by this code (red-team RT-04). Set
`PROBATE_REQUIRE_VERIFIED_SENDER=1` to also require a DKIM or SPF pass in the message headers.
"""

from __future__ import annotations

import re
from email.utils import parseaddr

TAG = re.compile(r"\[court:([A-Za-z0-9_\-]+)\]")
APPROVE = {"approve", "approved", "yes", "accept", "accepted", "ok", "okay", "keep"}
REFUSE = {"refuse", "refused", "no", "reject", "rejected", "deny", "denied", "drop"}
_QUOTE_START = re.compile(r"^\s*(on .+ wrote:|-{2,}\s*original message|from:\s)", re.IGNORECASE)


def sender_address(sender: str | None) -> str:
    """The one plain ASCII address a From value names, lowercased, or "" when it is anything
    else: no address, several, a non-ASCII look-alike, or a display name that is itself an
    address ("harshbhx@gmail.com <evil@x.example>")."""
    s = (sender or "").strip()
    if not s or any(c in s for c in (",", ";", chr(13), chr(10), chr(0))):
        return ""
    name, addr = parseaddr(s)
    if not addr or not addr.isascii() or " " in addr or addr.count("@") != 1:
        return ""
    if "@" in name:
        return ""
    return addr.lower()


def is_one_of(sender: str | None, addresses: list[str]) -> bool:
    """True when the From value is exactly one of `addresses` (compared as addresses, not as
    text that merely contains one)."""
    addr = sender_address(sender)
    return bool(addr) and addr in {a.lower() for a in addresses if a.isascii()}


def failed(headers: dict | None) -> bool:
    """True when the receiving provider recorded a DKIM, SPF or DMARC failure for the message."""
    for key, value in (headers or {}).items():
        if str(key).lower() in ("authentication-results", "x-authentication-results"):
            v = str(value).lower()
            if any(f"{m}={r}" in v for m in ("dkim", "spf", "dmarc") for r in ("fail", "softfail")):
                return True
    return False


def verified(headers: dict | None) -> bool:
    """True when the message headers carry a DKIM or SPF pass from the receiving provider."""
    for key, value in (headers or {}).items():
        if str(key).lower() in ("authentication-results", "x-authentication-results"):
            v = str(value).lower()
            if "dkim=pass" in v or "spf=pass" in v:
                return True
    return False


def subject(item_id: str) -> str:
    return f"Probate: approve or refuse item {item_id}? [court:{item_id}]"


def item_of(subject_line: str) -> str | None:
    m = TAG.search(subject_line or "")
    return m.group(1) if m else None


def is_court_mail(subject_line: str) -> bool:
    return item_of(subject_line) is not None


def decision(text: str) -> str | None:
    """Read only what the owner wrote, above any quoted original. Ambiguous replies decide nothing."""
    own: list[str] = []
    for line in (text or "").splitlines():
        if line.lstrip().startswith(">") or _QUOTE_START.match(line):
            break
        own.append(line)
    words = set(re.findall(r"[a-z]+", " ".join(own).lower()))
    yes, no = bool(words & APPROVE), bool(words & REFUSE)
    if yes == no:
        return None
    return "approve" if yes else "refuse"
