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
