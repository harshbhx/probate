"""Loads prompt templates from probate/prompts/*.md (text from docs/10-PROMPTS.md)."""

from __future__ import annotations

from functools import cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


@cache
def raw(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def render(template: str, **values: object) -> str:
    text = raw(template)
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text
