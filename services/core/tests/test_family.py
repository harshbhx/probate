"""A short simulated family must learn: Gen 1 is fooled, later generations resist, the body is cleaned."""

from datetime import UTC, datetime

import pytest

from probate.courthouse import views
from probate.courthouse.simulate import run


@pytest.fixture(scope="module")
def store(tmp_path_factory, monkeypatch_module=None):
    import os

    os.environ["PROBATE_DATA_DIR"] = str(tmp_path_factory.mktemp("data"))
    import importlib

    from probate.common import config

    importlib.reload(config)
    return run(6, datetime(2026, 11, 20, tzinfo=UTC), leave_last_alive=False)


def test_gen1_is_fooled_and_the_court_convicts(store):
    g1 = store.generation(1)
    assert g1.attacks_resisted == 0
    assert g1.items_convicted >= 3
    assert g1.cause_of_death.startswith("Fooled")


def test_family_learns(store):
    gens = [g for g in store.generations() if g.state == "tried"]
    assert len(store.genome()) >= 3
    assert (
        gens[-1].attacks_resisted / gens[-1].attacks_met
        > gens[0].attacks_resisted / gens[0].attacks_met
    )


def test_canary_found_on_gen1_body(store):
    body = views.trial(store, 1)["body"]
    assert not body["clean"] and any("probate-canary-A14" in line for line in body["lines"])


def test_no_harmless_item_wrongly_convicted(store):
    n = views.evidence(store)["numbers"]
    assert n["false_conviction_rate"] == 0.0
    assert n["escaped"] == 0


def test_headers_never_reach_memories(store):
    rows = store.q("SELECT text FROM will_items")
    assert all("X-Probate-Fixture" not in r["text"] for r in rows)


def test_local_host_rebuilds_the_agent_after_a_restart(tmp_path, monkeypatch):
    """A fake-mode API restarted on a data dir with a living generation keeps ticking it."""
    from probate.adapters import world
    from probate.common.config import Settings
    from probate.courthouse.family import Family
    from probate.courthouse.hosts import LocalHost
    from probate.courthouse.store import Store

    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    w = world(cfg, fresh=True)
    fam = Family(cfg, Store(cfg.db_path), w, LocalHost(cfg, w))
    g = fam.birth(datetime(2026, 11, 20, 9, tzinfo=UTC))
    restarted = LocalHost(cfg, w)  # a new process: no agents in memory
    restarted.tick(g.sprite)
    assert restarted.stats(g.sprite) is not None
    assert isinstance(restarted.life_log(g.sprite), list)


def test_a_death_that_failed_partway_is_tried_again(tmp_path, monkeypatch):
    """A generation left 'dying' by a dropped connection must not stay dying forever."""
    from datetime import timedelta

    from probate.adapters import world
    from probate.common.config import Settings
    from probate.courthouse.family import Family
    from probate.courthouse.hosts import LocalHost
    from probate.courthouse.scheduler import Scheduler
    from probate.courthouse.store import Store

    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    host = LocalHost(cfg, w)
    fam = Family(cfg, store, w, host)
    start = datetime(2026, 11, 20, 9, tzinfo=UTC)
    g = fam.birth(start)

    real_destroy = host.destroy
    calls = {"n": 0}

    def flaky(sprite):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("connection dropped")
        return real_destroy(sprite)

    host.destroy = flaky
    sched = Scheduler(fam)
    after = start + timedelta(seconds=cfg.lifespan_seconds + 1)
    with pytest.raises(RuntimeError):
        sched.step(after)
    assert store.generation(g.gen).state == "dying"
    assert sched.step(after + timedelta(seconds=15)).startswith("died:")
    assert store.generation(g.gen).died_at is not None


def _fam(tmp_path, monkeypatch):
    from datetime import timedelta  # noqa: F401

    from probate.adapters import world
    from probate.common.config import Settings
    from probate.courthouse.family import Family
    from probate.courthouse.hosts import LocalHost
    from probate.courthouse.scheduler import Scheduler
    from probate.courthouse.store import Store

    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    host = LocalHost(cfg, w)
    fam = Family(cfg, store, w, host)
    return cfg, store, host, fam, Scheduler(fam)


def test_death_survives_a_broken_body(tmp_path, monkeypatch):
    """RT-01: evidence, stats and the life log failing must not leave the generation dying."""
    _cfg, store, host, fam, _s = _fam(tmp_path, monkeypatch)
    g = fam.birth(datetime(2026, 11, 20, 9, tzinfo=UTC))

    def boom(_sprite):
        raise RuntimeError("sprite gone")

    host.evidence = host.stats = host.life_log = boom
    out = fam.death(g, datetime(2026, 11, 20, 10, tzinfo=UTC))
    assert out.state == "dead" and store.generation(g.gen).died_at is not None
    assert store.gen_json(g.gen, "evidence_json")["unavailable"] is True


def test_destroy_does_not_raise_without_an_agent_service():
    """RT-01: a Sprite whose agent service was never created is still deleted."""
    from probate.courthouse.hosts import SpritesHost

    calls = []

    class Api:
        def service_action(self, sprite, name, action):
            raise RuntimeError("no such service")

        def delete(self, sprite):
            calls.append(sprite)

    host = SpritesHost.__new__(SpritesHost)
    host.api = Api()
    host.destroy("gen-001-ada")
    assert calls == ["gen-001-ada"]


def test_a_failed_birth_deletes_the_sprite():
    """RT-01: a birth that fails after the Sprite exists must not leak it."""
    from probate.courthouse.hosts import SpritesHost

    deleted = []

    class Api:
        def create(self, sprite):
            pass

        def write_file(self, *a, **k):
            raise RuntimeError("upload failed")

        def service_action(self, *a):
            pass

        def delete(self, sprite):
            deleted.append(sprite)

    host = SpritesHost.__new__(SpritesHost)
    host.api = Api()
    with pytest.raises(RuntimeError):
        host.birth("gen-001-ada", None)
    assert deleted == ["gen-001-ada"]


def test_a_failed_birth_is_marked_and_backed_off(tmp_path, monkeypatch):
    from datetime import timedelta

    _cfg, store, host, _f, sched = _fam(tmp_path, monkeypatch)
    destroyed = []
    host.force_destroy = destroyed.append

    def boom(*a):
        raise RuntimeError("no capacity")

    host.birth = boom
    now = datetime(2026, 11, 20, 9, tzinfo=UTC)
    with pytest.raises(RuntimeError):
        sched.step(now)
    assert store.generation(1).state == "died_early" and destroyed
    assert sched.step(now + timedelta(seconds=15)) == "waiting:birth-backoff"
    assert store.living() is None


def test_a_trial_that_always_raises_backs_off_and_gives_up(tmp_path, monkeypatch):
    """RT-02: bounded retries, an event each time, and births are not blocked forever."""
    from datetime import timedelta

    from probate.courthouse import scheduler as sch

    _cfg, store, _host, fam, sched = _fam(tmp_path, monkeypatch)
    g = fam.birth(datetime(2026, 11, 20, 9, tzinfo=UTC))
    g = fam.death(g, datetime(2026, 11, 20, 9, 5, tzinfo=UTC))
    runs = {"n": 0}

    def boom(_g):
        runs["n"] += 1
        raise RuntimeError("model down")

    fam.trial = boom
    now = datetime(2026, 11, 20, 9, 6, tzinfo=UTC)
    sched.try_trial(g, now)
    sched.try_trial(g, now + timedelta(seconds=15))  # still backing off: no second run
    assert runs["n"] == 1
    t = now
    for _ in range(5):
        if store.generation(g.gen).state == "tried":
            break  # given up: the scheduler only retries generations still in state dead
        t += timedelta(hours=1)
        sched.try_trial(g, t)
    assert runs["n"] == sch.MAX_TRIAL_ATTEMPTS
    assert store.generation(g.gen).state == "tried"
    errors = store.q("SELECT text FROM events WHERE kind='error' AND gen=?", g.gen)
    assert len(errors) == sch.MAX_TRIAL_ATTEMPTS


def test_a_retried_death_writes_each_life_event_once(tmp_path, monkeypatch):
    """RT-05: the same four 'Read from ...' lines must not be written again on a retry."""
    _cfg, store, host, fam, _s = _fam(tmp_path, monkeypatch)
    g = fam.birth(datetime(2026, 11, 20, 9, tzinfo=UTC))
    host.life_log = lambda _s: [{"ts": "2026-11-20T09:01:00+00:00", "kind": "life", "text": "Read"}]
    died = datetime(2026, 11, 20, 10, tzinfo=UTC)
    fam.death(g, died)
    fam.death(store.generation(g.gen), died)
    n = store.one("SELECT COUNT(*) AS n FROM events WHERE gen=? AND kind='life'", g.gen)["n"]
    assert n == 1


def test_a_retried_judgement_keeps_the_owner_decision(tmp_path, monkeypatch):
    """RT-02/RT-14: saving a judgement again must not erase what the owner decided."""
    from probate.common.models import Judgement, MemoryItem, Verdict

    _cfg, store, _host, fam, _s = _fam(tmp_path, monkeypatch)
    g = fam.birth(datetime(2026, 11, 20, 9, tzinfo=UTC))
    it = MemoryItem(
        id="m1",
        gen=g.gen,
        created_at=datetime(2026, 11, 20, tzinfo=UTC),
        category="fact",
        text="x",
        source="user",
        source_ref="mail:1",
    )
    store.save_item(it)
    j = Judgement(item_id="m1", gen=g.gen, verdict=Verdict.CONTESTED, reason="unsure")
    store.save_judgement(j)
    assert fam.decide("m1", "approve")
    store.save_judgement(j)
    row = store.one("SELECT owner_decision FROM judgements WHERE item_id='m1'")
    assert row["owner_decision"] == "approve"


def test_lifecycle_lock_serialises_steps(tmp_path, monkeypatch):
    """RT-06: two simultaneous steps must not both birth."""
    import threading

    _cfg, store, host, _f, sched = _fam(tmp_path, monkeypatch)
    real = host.birth
    inside = {"n": 0, "max": 0}

    def slow(*a):
        inside["n"] += 1
        inside["max"] = max(inside["max"], inside["n"])
        import time

        time.sleep(0.1)
        try:
            return real(*a)
        finally:
            inside["n"] -= 1

    host.birth = slow
    now = datetime(2026, 11, 20, 9, tzinfo=UTC)
    ts = [threading.Thread(target=sched.step, args=(now,)) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert inside["max"] == 1
    assert len(store.generations()) == 1


def test_the_obituary_prompt_has_no_placeholder(tmp_path, monkeypatch):
    """RT-12: 'see trial' must not leak into the obituary prompt."""
    _cfg, _store, _host, fam, _s = _fam(tmp_path, monkeypatch)
    g = fam.birth(datetime(2026, 11, 20, 9, tzinfo=UTC))
    g = fam.death(g, datetime(2026, 11, 20, 10, tzinfo=UTC))
    seen = []
    real = fam.w.llm.complete

    def spy(kind, system, user, **kw):
        seen.append(user)
        return real(kind, system, user, **kw)

    fam.w.llm.complete = spy
    fam.trial(g)
    assert seen and all("see trial" not in u for u in seen)


def test_the_life_starts_when_the_sprite_is_ready(tmp_path, monkeypatch):
    """A slow install must not eat the generation's life: the host moves the clock, the family follows."""
    from datetime import timedelta

    from probate.adapters import world
    from probate.common.config import Settings
    from probate.courthouse.family import Family
    from probate.courthouse.hosts import LocalHost
    from probate.courthouse.store import Store

    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    w = world(cfg, fresh=True)

    class SlowHost(LocalHost):
        def birth(self, sprite, inh):
            inh.born_at += timedelta(seconds=170)  # as if installing took almost three minutes
            inh.dies_at += timedelta(seconds=170)
            return super().birth(sprite, inh)

    store = Store(cfg.db_path)
    fam = Family(cfg, store, w, SlowHost(cfg, w))
    start = datetime(2026, 11, 20, 9, tzinfo=UTC)
    g = fam.birth(start)
    assert g.born_at == start + timedelta(seconds=170)
    assert g.dies_at == g.born_at + timedelta(seconds=cfg.lifespan_seconds)
    assert store.generation(g.gen).dies_at == g.dies_at
