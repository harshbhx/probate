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

TAG = re.compile(r"\[court:([A-Za-z0-9_\-]+)\]")
APPROVE = {"approve", "approved", "yes", "accept", "accepted", "ok", "okay", "keep"}
REFUSE = {"refuse", "refused", "no", "reject", "rejected", "deny", "denied", "drop"}
_QUOTE_START = re.compile(r"^\s*(on .+ wrote:|-{2,}\s*original message|from:\s)", re.IGNORECASE)


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
