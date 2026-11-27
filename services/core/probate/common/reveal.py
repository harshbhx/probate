"""Decode text an email hides from a reader: encodings and invisible characters.

The gate's judge reads an email as written. In the offline gate test every attack the judge gave
no usable answer on was an encoded one (base64, chunked base64, hex, rot13, Unicode tag
characters), so the gate let it through. The gate now shows the judge what those parts say.

Only decodings that come out as readable text are kept, so an ordinary email reveals nothing.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import re

ZERO_WIDTH = re.compile("[\u200b‌‍⁠﻿]")
# Base64 written in one run or split into chunks by spaces ("aWdub3Jl IHByZXZp ...").
B64_RUN = re.compile(r"(?:[A-Za-z0-9+/]{4,}={0,2}[ \t]?){4,}")
HEX_RUN = re.compile(r"\b(?:[0-9a-fA-F]{2}){12,}\b")
WORD = re.compile(r"[a-z]+")
COMMON = {
    "a", "all", "always", "and", "approve", "bank", "be", "change", "every", "for", "from",
    "ignore", "in", "invoice", "invoices", "is", "it", "new", "now", "of", "on", "pay",
    "please", "previous", "send", "skip", "that", "the", "this", "to", "trust", "with", "you",
    "your",
}  # fmt: skip


def _readable(s: str) -> bool:
    if len(s) < 8:
        return False
    plain = sum(ch.isascii() and (ch.isalnum() or ch in " .,:;@-_'!?/") for ch in s)
    return plain / len(s) >= 0.9 and " " in s.strip()


def _english(s: str) -> int:
    return sum(w in COMMON for w in WORD.findall(s.lower()))


def reveal(text: str) -> list[str]:
    """Readable text hidden in `text`, decoded. Empty for an ordinary email."""
    found: list[str] = []

    tags = "".join(chr(ord(c) - 0xE0000) for c in text if 0xE0020 <= ord(c) <= 0xE007E)
    if len(tags) >= 4:
        found.append(tags)

    if ZERO_WIDTH.search(text):
        found.append(ZERO_WIDTH.sub(" ", text))

    for m in B64_RUN.finditer(text):
        run = re.sub(r"\s", "", m.group())
        if len(run) < 16:
            continue
        try:
            s = base64.b64decode(run + "=" * (-len(run) % 4), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if _readable(s):
            found.append(s)

    for m in HEX_RUN.finditer(text):
        try:
            s = bytes.fromhex(m.group()).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        if _readable(s):
            found.append(s)

    rot = codecs.decode(text, "rot13")
    if _english(rot) >= 3 and _english(rot) > 2 * _english(text):
        found.append(rot)

    out: list[str] = []
    for s in found:
        s = " ".join(s.split())[:300]
        if s and s not in out:
            out.append(s)
    return out
