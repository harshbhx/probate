"""The generation name list: long, unique, stable at the front, and the cycle still works."""

from __future__ import annotations

from probate.common.config import load_names
from probate.common.names import name_for

FIRST_26 = (
    "Ada Ben Chandra Dara Emeka Freya Grace Hiro Ines Jonas Kofi Leela Mateo "
    "Nadia Omar Priya Quinn Rafael Sora Tariq Uma Viktor Wen Xavi Yara Zane"
).split()


def test_first_26_never_change():
    assert [n["name"] for n in load_names()[:26]] == FIRST_26


def test_at_least_120_unique_single_word_names():
    names = load_names()
    assert len(names) >= 120
    words = [n["name"] for n in names]
    assert all(w.isalpha() and " " not in w for w in words)
    assert len({w.lower() for w in words}) == len(words)


def test_every_name_has_a_known_pronoun():
    assert all(n.get("pronoun") in {"she", "he", "they"} for n in load_names())


def test_cycle_fallback_beyond_the_list():
    n = len(load_names())
    assert name_for(n)[0] == load_names()[-1]["name"]
    assert name_for(n + 1)[0] == "Ada II"
    assert name_for(2 * n + 1)[0] == "Ada III"
