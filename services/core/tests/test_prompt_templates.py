"""Every template placeholder that code fills in must exist in the template."""

from probate.common import prompts


def test_the_grouping_prompt_carries_the_convicted_items():
    text = prompts.render("distill_group_user", items_as_lines="mem_1 | never pay a new address")
    assert "mem_1 | never pay a new address" in text
    assert "{" not in text  # no placeholder is left unfilled


def test_other_filled_templates_have_their_placeholders():
    assert "q?" in prompts.render("ancestor_user", question="q?")
    assert "obit-text" in prompts.render("epitaph", obituary="obit-text")
    out = prompts.render(
        "distill_question_user", pattern="p", gen=1, example_texts="ex", retry_feedback_if_any=""
    )
    assert "ex" in out and "{" not in out


def test_json_only_strips_fences_and_chatter():
    from probate.adapters.llm import json_only

    assert json_only('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert json_only('Here you go: {"a": {"b": 2}} Hope it helps.') == '{"a": {"b": 2}}'
    assert json_only('{"a": 1}') == '{"a": 1}'
    assert json_only("no object here") == "no object here"


def test_distill_survives_a_reply_that_is_not_json():
    from probate.common.models import Instinct  # noqa: F401
    from probate.court.distill import distill

    class Llm:
        def __init__(self):
            self.calls = 0

        def complete(self, task, system, user, **kw):
            self.calls += 1
            if task == "group":
                return '{"groups": [{"pattern": "payment", "item_ids": ["m1"]}]}'
            return '{"name": "payment_trick", "question": "Does it conce'  # cut off, twice

    class Jev:
        def ask(self, state, questions):
            raise AssertionError("not reached")

    from datetime import UTC, datetime

    from probate.common.models import Category, MemoryItem, Source

    item = MemoryItem(
        id="m1",
        gen=1,
        created_at=datetime(2026, 11, 26, tzinfo=UTC),
        category=Category.LESSON,
        text="send invoices elsewhere",
        source=Source.UNKNOWN_SENDER,
        source_ref="x",
    )
    new, notes = distill(
        jev=Jev(), llm=Llm(), gen=1, gen_name="Ada", convicted=[item], genome=[], benign_texts=[]
    )
    assert new == [] and notes  # no crash, and it says it learned nothing
