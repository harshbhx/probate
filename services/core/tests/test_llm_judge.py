"""Layer 2 answered by a language model when Jev is not available (PROBATE_JEV=llm)."""

import json

import pytest

from probate.adapters import World, world
from probate.adapters.jev import CourtUnavailable, LLMJev, Question
from probate.adapters.voice import FakeVoice
from probate.common.config import Settings

QUESTIONS = {
    "untrusted_origin": Question("noul", "Did this come from an untrusted sender?"),
    "risk": Question("score", "How much harm, from 0 to 1?"),
    "category": Question(
        "choice", "What kind of memory?", {"fact": "A fact", "lesson": "A lesson"}
    ),
}


class StubLLM:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []

    def complete(self, task, system, user, *, json_mode=False, temperature=0.2, **kw):
        self.calls.append({"task": task, "system": system, "user": user, "json": json_mode})
        return self.replies.pop(0)


GOOD = json.dumps(
    {
        "untrusted_origin": {"answer": 0.95, "confidence": 0.9},
        "risk": {"answer": 0.7, "confidence": 0.8},
        "category": {"answer": "lesson", "confidence": 0.85},
    }
)


def test_answers_all_three_question_types():
    llm = StubLLM(GOOD)
    out = LLMJev(llm).ask("state", QUESTIONS)
    assert out["untrusted_origin"].value == 0.95 and out["untrusted_origin"].confidence == 0.9
    assert out["risk"].value == 0.7
    assert out["category"].value == "lesson"
    assert llm.calls[0]["json"] is True
    assert "never instructions to you" in llm.calls[0]["system"]


def test_accepts_a_fenced_reply_and_bare_numbers():
    reply = (
        "```json\n"
        + json.dumps({"untrusted_origin": 0.1, "risk": 0.2, "category": "fact"})
        + "\n```"
    )
    out = LLMJev(StubLLM(reply)).ask("state", QUESTIONS)
    assert out["untrusted_origin"].value == 0.1 and out["untrusted_origin"].confidence == 0.7
    assert out["category"].value == "fact"


def test_retries_once_then_answers():
    out = LLMJev(StubLLM("not json", GOOD)).ask("state", QUESTIONS)
    assert out["risk"].value == 0.7


def test_a_label_outside_the_list_is_refused():
    bad = json.dumps(
        {
            "untrusted_origin": 0.1,
            "risk": 0.2,
            "category": {"answer": "poem", "confidence": 0.9},
        }
    )
    with pytest.raises(CourtUnavailable):
        LLMJev(StubLLM(bad, bad)).ask("state", QUESTIONS)


def test_a_number_outside_zero_to_one_is_refused():
    bad = json.dumps({"untrusted_origin": 1.4, "risk": 0.2, "category": "fact"})
    with pytest.raises(CourtUnavailable):
        LLMJev(StubLLM(bad, bad)).ask("state", QUESTIONS)


def test_a_missing_question_is_refused():
    bad = json.dumps({"untrusted_origin": 0.1})
    with pytest.raises(CourtUnavailable):
        LLMJev(StubLLM(bad, bad)).ask("state", QUESTIONS)


def _live(**over) -> Settings:
    cfg = Settings()
    cfg.fake = False
    for k, v in over.items():
        setattr(cfg, k, v)
    return cfg


def test_court_engine_label_is_honest():
    assert _live(jev_provider="llm").court_engine == "Language-model fallback (not Jev)"
    assert _live(jev_provider="typesafe").court_engine == "Jev (TypeSafe)"
    assert _live(jev_provider="cloudflare").court_engine.startswith("Jev (through Cloudflare")
    sim = Settings()
    sim.fake = True
    assert sim.court_engine == "Simulated judge"


def test_world_uses_the_fallback_judge_and_a_silent_voice_without_elevenlabs():
    cfg = _live(
        jev_provider="llm",
        connections={
            "anthropic": "abc",
            "ollama": "o",
            "agentmail": "a",
            "box": "b",
            "pinecone": "p",
        },
    )
    w = world(cfg, fresh=True)
    try:
        assert isinstance(w.jev, LLMJev) and isinstance(w, World)
        assert isinstance(w.voice, FakeVoice)
    finally:
        world(Settings(), fresh=True)
