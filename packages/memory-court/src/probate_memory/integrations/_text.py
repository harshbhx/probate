"""Turning what a memory system is given into the text the court judges."""

from __future__ import annotations

import json
from collections.abc import Mapping

TEXT_KEYS = ("text", "content", "memory", "data", "value", "fact", "note")


def text_of(value) -> str:
    """The words in a memory, whatever shape it arrives in: a string, a chat message, a list of
    messages, or a mapping (its text-like fields, or all of it as JSON)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        if "role" in value and "content" in value:
            return text_of(value["content"])
        picked = [text_of(value[k]) for k in TEXT_KEYS if k in value]
        if any(picked):
            return "\n".join(p for p in picked if p)
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, list | tuple):
        return "\n".join(t for t in (text_of(v) for v in value) if t)
    return str(value)
