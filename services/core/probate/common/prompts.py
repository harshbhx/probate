"""Loads prompt templates from probate/prompts/*.md (text from docs/10-PROMPTS.md)."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


_PLACEHOLDER = re.compile(r"\{(\w+)\}")


@cache
def raw(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def render(template: str, **values: object) -> str:
    """Fill `{name}` placeholders in one pass, so a value that itself contains `{other}` (an
    email or a question typed by a stranger) is never expanded."""
    return _PLACEHOLDER.sub(
        lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), raw(template)
    )
