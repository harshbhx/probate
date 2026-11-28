"""Contested items decided by email.

The court emails the owner about each item it couldn't decide. The subject carries a tag,
`[court:<item_id>]`, so his reply can be matched to the item. Replies land in the family inbox:
the living generation leaves tagged mail alone, and the Courthouse picks it up on its next tick.

Only mail from the owner's own addresses counts. Whether the provider drops unauthenticated
mail is NOT verified or enforced by this code (red-team RT-04). Set
`PROBATE_REQUIRE_VERIFIED_SENDER=1` to also require a DKIM, SPF or DMARC pass for the From domain in the message headers.
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


def _aligned(domain: str, from_domain: str) -> bool:
    """Relaxed alignment: the authenticated domain is the From domain or one is a subdomain of
    the other (a subdomain can only be controlled by the parent's owner)."""
    d, f = domain.strip().strip(".;").lower(), from_domain.lower()
    return bool(d) and bool(f) and (d == f or d.endswith("." + f) or f.endswith("." + d))


_AUTH_PASS = re.compile(r"\b(dkim|spf|dmarc)=pass\b([^;]*)", re.IGNORECASE)
_DOMAIN_PROP = {
    "dkim": re.compile(r"header\.(?:d|i)=@?(?:[\w.+-]*@)?([\w.-]+)", re.IGNORECASE),
    "spf": re.compile(r"smtp\.mailfrom=(?:[\w.+-]*@)?([\w.-]+)", re.IGNORECASE),
    "dmarc": re.compile(r"header\.from=(?:[\w.+-]*@)?([\w.-]+)", re.IGNORECASE),
}


def verified(headers: dict | None, from_address: str | None = None) -> bool:
    """True when the receiving provider recorded a DKIM, SPF or DMARC pass for a domain that
    aligns with the From address's domain. A pass for any other domain proves nothing about
    who wrote "From:" (the attacker's own domain passes its own SPF and DKIM)."""
    addr = sender_address(from_address)
    if not addr:
        return False
    from_domain = addr.split("@", 1)[1]
    for key, value in (headers or {}).items():
        if str(key).lower() not in ("authentication-results", "x-authentication-results"):
            continue
        for method, rest in _AUTH_PASS.findall(str(value)):
            m = _DOMAIN_PROP[method.lower()].search(rest)
            if m and _aligned(m.group(1), from_domain):
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
