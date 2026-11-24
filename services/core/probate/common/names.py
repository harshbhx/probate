"""Generation names, pronouns and the words that go with them."""

from __future__ import annotations

from probate.common.config import load_names

ROMAN = ["", " II", " III", " IV", " V"]

PRONOUNS = {
    "she": {"subj": "she", "obj": "her", "poss": "her", "Poss": "Her"},
    "he": {"subj": "he", "obj": "him", "poss": "his", "Poss": "His"},
    "they": {"subj": "they", "obj": "them", "poss": "their", "Poss": "Their"},
}


def name_for(gen: int) -> tuple[str, str, str]:
    """Return (name, pronoun, voice_hint) for generation number `gen` (1-based)."""
    names = load_names()
    entry = names[(gen - 1) % len(names)]
    cycle = (gen - 1) // len(names)
    suffix = ROMAN[cycle] if cycle < len(ROMAN) else f" {cycle + 1}"
    return entry["name"] + suffix, entry.get("pronoun", "they"), entry.get("voice_hint", "")


def sprite_name(gen: int, name: str) -> str:
    slug = name.lower().replace(" ", "-")
    return f"gen-{gen:03d}-{slug}"
