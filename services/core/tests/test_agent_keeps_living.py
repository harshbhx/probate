"""A generation keeps reading its inbox whatever one email or one tick does.

Generation 7 of the real run read nothing in a whole life: one exception ended its loop, and
nothing noticed. Bad model replies, a failing email and a failing tick are now survived, and a
loop that stops anyway is restarted by the Courthouse.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest

from probate.adapters import world
from probate.common.config import Settings
from probate.courthouse import hosts
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost, SpritesHost
from probate.courthouse.scheduler import Scheduler
from probate.courthouse.store import Store
from probate.generation import agent as agent_mod
from probate.generation.agent import _notes

T0 = datetime(2026, 11, 27, 9, tzinfo=UTC)


@pytest.fixture
def fam(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 600
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    return cfg, store, w, Family(cfg, store, w, LocalHost(cfg, w))


def test_odd_model_replies_are_cleaned_not_raised():
    assert _notes(["not", "a", "dict"], 3) == []
    assert _notes({"memories": "nope"}, 3) == []
    notes = _notes(
        {
            "memories": [
                {"text": "keep me", "category": "Open Task"},
                {"text": "", "category": "fact"},
                "a bare string",
                {"category": "lesson"},
                {"text": "odd kind", "category": "rumour"},
            ]
        },
        3,
    )
    assert [(n["text"], n["category"]) for n in notes] == [
        ("keep me", "open_task"),
        ("odd kind", "fact"),
    ]


class _Brain:
    """Answers like the fake brain, but raises on any email whose subject says poison."""

    def __init__(self, inner):
        self.inner = inner

    def complete(self, kind, system, user, context=None, **kw):
        if "poison" in ((context or {}).get("mail") or {}).get("subject", ""):
            raise RuntimeError("model timed out")
        return self.inner.complete(kind, system, user, context=context, **kw)

    def __getattr__(self, name):
        return getattr(self.inner, name)


def test_one_failing_email_does_not_stop_the_others_and_is_set_aside(fam):
    _cfg, _store, w, family = fam
    g = family.birth(T0)
    agent = family.host._agent(g.sprite)
    w.llm = agent.w.llm = _Brain(w.llm)
    inbox = agent.inh.family_inbox
    w.mail.send("x@example.com", inbox, "poison pill", "boom")
    w.mail.send("x@example.com", inbox, "Lunch", "Noon tomorrow?")
    assert agent.tick() == 1
    assert agent.tick() == 0  # second failure: set aside
    assert agent.tick() == 0  # nothing left
    texts = [r["text"] for r in agent.life_log() if r["kind"] == "error"]
    assert any("will try again" in t for t in texts)
    assert any("Set aside" in t for t in texts)


def test_the_loop_outlives_a_failing_tick_and_says_so(fam, monkeypatch):
    _cfg, _store, w, family = fam
    g = family.birth(T0)
    workdir = family.host.root / g.sprite
    inh = json.loads((workdir / "inheritance.json").read_text())
    inh["dies_at"] = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()
    (workdir / "inheritance.json").write_text(json.dumps(inh))
    calls = {"n": 0}
    real_tick = agent_mod.GenerationAgent.tick

    def flaky(self):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("inbox unreachable")
        return real_tick(self)

    monkeypatch.setattr(agent_mod.GenerationAgent, "tick", flaky)
    monkeypatch.setattr(agent_mod.time, "sleep", lambda s: None)
    agent_mod.run_forever(workdir, w, poll_seconds=0, max_backoff=0)
    assert calls["n"] > 1
    beat = json.loads((workdir / agent_mod.HEARTBEAT).read_text())
    assert beat["errors"] == 1


class _API:
    def __init__(self):
        self.actions = []

    def service_action(self, sprite, service, action):
        self.actions.append((sprite, service, action))


def _host(age):
    h = SpritesHost.__new__(SpritesHost)
    h.api, h._restarted = _API(), {}
    h._cli = lambda sprite, cmd: {"state": "living", "loop_age": age}
    return h


def test_a_stopped_agent_is_restarted_once_per_window():
    h = _host(hosts.STALE_LOOP_SECONDS + 10)
    assert h.tick("gen-007-grace").get("restarted")
    assert not h.tick("gen-007-grace").get("restarted")  # not again within the window
    assert h.api.actions == [("gen-007-grace", "agent", "restart")]
    quiet = _host(30)
    assert not quiet.tick("gen-008-hiro").get("restarted") and quiet.api.actions == []


def test_the_clock_says_when_it_restarted_an_agent(fam, monkeypatch):
    _cfg, store, _w, family = fam
    g = family.birth(T0)
    monkeypatch.setattr(family.host, "tick", lambda sprite: {"restarted": True, "loop_age": 400})
    Scheduler(family).step(T0 + timedelta(seconds=30))
    texts = [r["text"] for r in store.q("SELECT text FROM events WHERE kind='error'")]
    assert any("restarted it" in t and g.name in t for t in texts)
