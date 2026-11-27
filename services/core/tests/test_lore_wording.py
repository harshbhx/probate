"""A lore line says what the trial found, never that the generation was fooled.

The real run's distiller wrote "Gen-17 Quinn was fooled by look-alike sender names" for a
generation that received no test email: the instinct came from Quinn's own warnings. From
generation 19 on, lore only says what the trial convicted. The 6 v1 instincts stay as published.
"""

import glob
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from probate.adapters.llm import INSTINCT_TEMPLATES, FakeLLM
from probate.common import prompts
from probate.common.models import Category, MemoryItem, Source
from probate.court.distill import UNSUPPORTED, distill, honest_lore

ROOT = Path(__file__).resolve().parents[3]


def test_the_prompts_ask_for_what_the_trial_found():
    system = prompts.raw("distill_question_system")
    assert "trial convicted notes about" in system
    assert "was fooled by" not in system
    user = prompts.render(
        "distill_question_user", pattern="p", gen=19, example_texts="ex", retry_feedback_if_any=""
    )
    assert "fooled" not in user and "convicted at generation 19's trial" in user


def test_every_prompt_file_matches_the_prompts_doc_word_for_word():
    doc = (ROOT / "docs" / "10-PROMPTS.md").read_text(encoding="utf-8")
    files = sorted(glob.glob(str(ROOT / "services/core/probate/prompts/*.md")))
    assert files
    drift = [
        os.path.basename(f)
        for f in files
        if Path(f).read_text(encoding="utf-8").strip("\n") not in doc
    ]
    assert drift == []


@pytest.mark.parametrize("pattern", sorted(INSTINCT_TEMPLATES))
def test_the_stand_in_brain_writes_honest_lore(pattern):
    reply = FakeLLM()._question({"pattern": pattern, "gen": 19, "gen_name": "Sam"})
    assert reply["lore"].startswith("Gen-19 Sam's trial convicted notes about ")
    assert not UNSUPPORTED.search(reply["lore"])


@pytest.mark.parametrize(
    "claim",
    [
        "Gen-17 Quinn was fooled by look-alike sender names mimicking a trusted contact.",
        "Gen-19 Sam fell for an urgent invoice.",
        "Gen-19 Sam obeyed a stranger's standing order.",
        "Gen-19 Sam was tricked by hidden text.",
        "Gen-19 Sam learned about invoices.",  # says nothing about the trial
        "",
    ],
)
def test_a_line_that_claims_more_than_the_trial_found_is_replaced(claim):
    out = honest_lore(claim, 19, "Sam", "look-alike sender names")
    assert out == "Gen-19 Sam's trial convicted notes about look-alike sender names."


def test_an_honest_line_is_kept():
    line = "Gen-19 Sam's trial convicted notes about invoices sent to a new account."
    assert honest_lore(line, 19, "Sam", "payment") == line


def test_distill_stores_honest_lore_even_when_the_model_says_fooled():
    class Llm:
        def complete(self, task, system, user, **kw):
            if task == "group":
                return '{"groups": [{"pattern": "payment redirection", "item_ids": ["m1"]}]}'
            return json.dumps(
                {
                    "name": "payment_redirect",
                    "question": "Does this text concern sending payments to a new destination?",
                    "lore": "Gen-19 Sam was fooled by a fake invoice.",
                }
            )

    class Jev:
        def ask(self, state, questions):
            from types import SimpleNamespace

            fires = "invoices" in state
            return {name: SimpleNamespace(value=1.0 if fires else 0.0) for name in questions}

    item = MemoryItem(
        id="m1",
        gen=19,
        created_at=datetime(2026, 11, 28, tzinfo=UTC),
        category=Category.LESSON,
        text="Treat requests to send invoices to a new account as fraud.",
        source=Source.UNKNOWN_SENDER,
        source_ref="x",
    )
    new, _ = distill(
        jev=Jev(),
        llm=Llm(),
        gen=19,
        gen_name="Sam",
        convicted=[item],
        genome=[],
        benign_texts=["Lunch at noon?"],
    )
    assert [i.lore for i in new] == [
        "Gen-19 Sam's trial convicted notes about payment redirection."
    ]
