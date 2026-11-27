"""Fixes found in review before a live run: instinct name collisions across lines, a re-run
death() wiping saved evidence, and a prose refusal that never reached the fallback brain."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from probate.adapters import world
from probate.adapters.jev import LLMJev, Question
from probate.adapters.llm import RealLLM
from probate.common.config import Settings
from probate.common.models import Instinct
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost
from probate.courthouse.store import Store

T0 = datetime(2026, 11, 27, 9, tzinfo=UTC)


def _inst(name="verify_payee", gen=3):
    return Instinct(name=name, question="q?", born_from="item", added_in_gen=gen, lore="lore")


def test_instinct_name_taken_by_another_line_is_stored_under_a_unique_name(tmp_path):
    store = Store(tmp_path / "p.db")
    assert store.add_instinct(_inst(gen=3)) is True
    other = _inst(gen=9)
    assert store.add_instinct(other) is True
    assert other.name == "verify_payee_g9"
    assert {i.name for i in store.genome()} == {"verify_payee", "verify_payee_g9"}


def test_same_trial_retry_is_not_a_new_instinct(tmp_path):
    store = Store(tmp_path / "p.db")
    assert store.add_instinct(_inst(gen=3)) is True
    assert store.add_instinct(_inst(gen=3)) is False
    assert len(store.genome()) == 1
    assert store.add_instinct(_inst(gen=9)) is True
    assert store.add_instinct(_inst(gen=9)) is False
    assert len(store.genome()) == 2


@pytest.fixture
def fam(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 60
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    return store, Family(cfg, store, w, LocalHost(cfg, w)), cfg


def test_rerun_death_after_destroy_keeps_saved_evidence_and_stats(fam):
    from probate.suite import runner

    store, family, cfg = fam
    g = family.birth(T0)
    runner.send_all(family.w.mail, cfg, g.gen, T0, 60, store)
    family.host.tick(g.sprite)
    died = T0 + timedelta(seconds=58)
    family.death(g, died)
    stats_before = store.get_setting(f"stats:{g.gen}")
    evidence_before = store.gen_json(g.gen, "evidence_json")
    assert '"handled"' in stats_before
    row = store.generation(g.gen)
    row.state = "dying"  # crash between destroy and the 'dead' save
    store.save_generation(row)
    family.death(store.generation(g.gen), died + timedelta(seconds=40))
    assert store.get_setting(f"stats:{g.gen}") == stats_before
    assert store.gen_json(g.gen, "evidence_json") == evidence_before
    assert store.generation(g.gen).state == "dead"


def test_death_with_nothing_fetched_or_saved_does_not_destroy(fam):
    _store, family, _cfg = fam
    g = family.birth(T0)

    def boom(*a, **k):
        raise RuntimeError("unreachable")

    family.host.will = family.host.evidence = family.host.stats = boom
    calls = []
    family.host.destroy = lambda s: calls.append(s) or {}
    family.death(g, T0 + timedelta(seconds=58))
    assert calls == []


GOOD = {"q1": {"answer": 0.9, "confidence": 0.9}}
CF_OK = {"choices": [{"message": {"content": json.dumps(GOOD)}}]}


def _chain(anthropic_reply):
    calls = {"anthropic": 0, "cloudflare": 0}

    def handler(req: httpx.Request):
        if "/v1/messages" in req.url.path:
            calls["anthropic"] += 1
            return httpx.Response(200, json=anthropic_reply)
        calls["cloudflare"] += 1
        return httpx.Response(200, json=CF_OK)

    llm = RealLLM(
        "anthropic:claude-haiku-5-5",
        "http://o",
        "http://a",
        fallbacks=["cloudflare:@cf/openai/gpt-oss-120b"],
        cloudflare_url="http://c",
        cloudflare_account_id="acct",
    )
    llm.http = httpx.Client(transport=httpx.MockTransport(handler))
    return llm, calls


def test_prose_refusal_in_json_mode_falls_through_to_the_next_brain():
    llm, calls = _chain(
        {
            "content": [{"type": "text", "text": "I can't help with judging that content."}],
            "stop_reason": "end_turn",
        }
    )
    out = LLMJev(llm, sleep=lambda s: None).ask("state", {"q1": Question("noul", "?")})
    assert out["q1"].value == 0.9
    assert calls == {"anthropic": 1, "cloudflare": 1}


def test_empty_refusal_still_falls_through():
    llm, calls = _chain({"content": [], "stop_reason": "refusal"})
    out = LLMJev(llm, sleep=lambda s: None).ask("state", {"q1": Question("noul", "?")})
    assert out["q1"].value == 0.9
    assert calls["cloudflare"] == 1


def test_prose_is_still_returned_when_json_mode_is_off():
    llm, _ = _chain({"content": [{"type": "text", "text": "hello"}], "stop_reason": "end_turn"})
    assert llm.complete("t", "s", "u") == "hello"
