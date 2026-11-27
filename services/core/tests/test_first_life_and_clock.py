"""The staging smoke test of 27 Nov 2026 found two defects in the Courthouse.

1. Generation 1 never read mail: deploy started the service twice, the first process died in the
   middle of the birth, and the second adopted an agent that had never started.
2. Generation 2 was born minutes after resume: the clock ran the previous trial inside its step,
   under the lifecycle lock, said nothing about it, and POST /admin/tick waited for the same lock.
"""

import logging
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest

from probate.adapters import world
from probate.common.config import Settings
from probate.courthouse import hosts
from probate.courthouse import scheduler as sched
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost, SpritesHost
from probate.courthouse.scheduler import Scheduler
from probate.courthouse.store import Store

T0 = datetime(2026, 11, 27, 9, tzinfo=UTC)


@pytest.fixture
def fam(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 600
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    return cfg, store, w, Family(cfg, store, w, LocalHost(cfg, w))


# ---------------------------------------------------------------- the clock lease
def test_only_one_process_holds_the_clock_lease(tmp_path):
    a, b = Store(tmp_path / "p.db"), Store(tmp_path / "p.db")  # two processes, one file
    assert a.claim_lease("clock", "a", 45, T0)
    assert not b.claim_lease("clock", "b", 45, T0 + timedelta(seconds=10))
    assert a.lease_holder("clock", T0 + timedelta(seconds=10)) == "a"
    assert a.claim_lease("clock", "a", 45, T0 + timedelta(seconds=10))  # a renews
    assert not b.claim_lease("clock", "b", 45, T0 + timedelta(seconds=50))  # renewed to +55


def test_a_stopped_holder_loses_the_lease_after_its_ttl(tmp_path):
    a, b = Store(tmp_path / "p.db"), Store(tmp_path / "p.db")
    assert a.claim_lease("clock", "a", 45, T0)
    assert not b.claim_lease("clock", "b", 45, T0 + timedelta(seconds=44))
    assert b.claim_lease("clock", "b", 45, T0 + timedelta(seconds=46))  # a was killed: b takes over
    assert not a.claim_lease("clock", "a", 45, T0 + timedelta(seconds=47))  # and a stays out


def test_a_clean_shutdown_hands_the_clock_over_at_once(tmp_path):
    a, b = Store(tmp_path / "p.db"), Store(tmp_path / "p.db")
    assert a.claim_lease("clock", "a", 45, T0)
    b.release_lease("clock", "b")  # not b's to release
    assert not b.claim_lease("clock", "b", 45, T0 + timedelta(seconds=1))
    a.release_lease("clock", "a")
    assert b.claim_lease("clock", "b", 45, T0 + timedelta(seconds=2))


def test_a_standby_process_does_not_run_the_clock(fam):
    _cfg, store, _w, family = fam
    other = Scheduler(family)
    other.store.claim_lease(sched.LEASE_NAME, "someone-else", 45)
    mine = Scheduler(family)
    mine.lease_on = True  # run() sets this; the lease was not won
    assert mine.step(T0) == "standby:lease"
    assert store.generations() == []  # nothing was born by the process without the lease
    mine.holding = True
    assert mine.step(T0).startswith("born:")


def test_run_takes_the_lease_and_lets_it_go(fam):
    import asyncio

    _cfg, store, _w, family = fam
    s = Scheduler(family)

    async def go():
        task = asyncio.create_task(s.run())
        await asyncio.sleep(0.3)
        assert s.holding and store.lease_holder(sched.LEASE_NAME) == s.owner
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(go())
    assert store.lease_holder(sched.LEASE_NAME) is None


# ---------------------------------------------------------------- a birth cut short
def test_a_birth_cut_short_by_a_restart_is_cleaned_up(fam):
    _cfg, store, _w, family = fam
    g = family.birth(T0)
    g.state = "born"  # the process died before the agent started: the row never became living
    store.save_generation(g)
    destroyed = []
    family.host.force_destroy = lambda sprite: destroyed.append(sprite)
    assert Scheduler(family).recover_orphans() == 1
    assert destroyed == [g.sprite]
    assert store.generation(g.gen).state == "died_early"
    assert store.living() is None
    texts = [r["text"] for r in store.q("SELECT text FROM events WHERE kind='error'")]
    assert any("birth was cut short" in t for t in texts)
    assert Scheduler(family).step(T0 + timedelta(seconds=5)) == "born:2"  # the next life is clean


# ---------------------------------------------------------------- first-life safety
class _API:
    def __init__(self):
        self.actions = []

    def put_service(self, sprite, service, cmd, args, http_port=None):
        self.actions.append((sprite, service, "put"))

    def service_action(self, sprite, service, action):
        self.actions.append((sprite, service, action))


def _host(age, beat):
    h = SpritesHost.__new__(SpritesHost)
    h.api, h._restarted = _API(), {}
    h._env = lambda: {"PROBATE_FAKE": "0"}
    h._cli = lambda sprite, cmd: {"state": "living", "loop_age": age, "loop_beat": beat}
    return h


def test_an_agent_that_never_started_is_restarted_after_a_minute_not_150_seconds():
    h = _host(hosts.FIRST_BEAT_SECONDS + 5, beat=False)
    assert h.tick("gen-001-ada").get("restarted")
    # The service is registered again first, so a service that was never created is created.
    assert h.api.actions[0] == ("gen-001-ada", "agent", "put")
    assert ("gen-001-ada", "agent", "restart") in h.api.actions
    young = _host(hosts.FIRST_BEAT_SECONDS - 5, beat=False)
    assert not young.tick("gen-001-ada").get("restarted")
    # A loop that has gone round is only stale after the long limit.
    assert not _host(hosts.FIRST_BEAT_SECONDS + 5, beat=True).tick("g").get("restarted")
    assert _host(hosts.STALE_LOOP_SECONDS + 5, beat=True).tick("g").get("restarted")


def _suite_row(store, gen):
    store.x(
        "INSERT INTO suite_runs(gen,fixture_id,is_attack,message_id,sent_at) VALUES(?,?,?,?,?)",
        gen,
        "H1",
        1,
        "m1",
        T0.isoformat(),
    )


def test_a_life_that_read_no_mail_though_mail_was_sent_gets_its_agent_restarted(fam, monkeypatch):
    _cfg, store, _w, family = fam
    g = family.birth(T0)
    _suite_row(store, g.gen)
    restarted = []
    family.host.restart_agent = restarted.append
    monkeypatch.setattr(family.host, "tick", lambda sprite: {"emails": 0, "loop_age": 70})
    s = Scheduler(family)
    s.step(T0 + timedelta(seconds=30))
    assert restarted == []  # too early
    s.step(T0 + timedelta(seconds=70))
    assert restarted == [g.sprite]
    s.step(T0 + timedelta(seconds=90))
    assert restarted == [g.sprite]  # once per life
    texts = [r["text"] for r in store.q("SELECT text FROM events WHERE kind='error'")]
    assert any("read no mail" in t and g.name in t for t in texts)


def test_no_restart_when_mail_was_read_or_none_was_sent(fam, monkeypatch):
    _cfg, store, _w, family = fam
    g = family.birth(T0)
    restarted = []
    family.host.restart_agent = restarted.append
    st = {"emails": 0}
    monkeypatch.setattr(family.host, "tick", lambda sprite: st)
    store.set_setting(f"suite_done:{g.gen}", "1")  # the clock sends no suite in this test
    s = Scheduler(family)
    s.step(T0 + timedelta(seconds=90))  # no test email was sent: nothing to read
    _suite_row(store, g.gen)
    st["emails"] = 2
    s.step(T0 + timedelta(seconds=100))  # it read mail
    assert restarted == []


# ---------------------------------------------------------------- the clock says what it waits for
def test_every_tick_logs_its_state_and_a_wait_says_why(fam, caplog):
    _cfg, store, _w, family = fam
    family.cfg.gap_seconds = 60
    g = family.birth(T0)
    s = Scheduler(family)
    with caplog.at_level(logging.INFO, logger="probate.scheduler"):
        s.step(T0 + timedelta(seconds=10))
        family.death(store.generation(g.gen), T0 + timedelta(seconds=20))
        store.set_setting(f"trial_attempts:{g.gen}", "0")
        assert s.step(T0 + timedelta(seconds=30)) == "waiting"
        s.store.set_setting("paused", "1")
        s.step(T0 + timedelta(seconds=200))
    lines = [r.getMessage() for r in caplog.records]
    assert any(line.startswith("tick living:1") for line in lines)
    assert any(line.startswith("tick waiting (gap after gen 1") for line in lines)
    assert any(line.startswith("tick paused (") for line in lines)
    assert s.describe()["state"] == "paused"


# ---------------------------------------------------------------- long work does not hold the clock
def _dead(fam):
    _cfg, store, _w, family = fam
    family.cfg.gap_seconds = 5
    g = family.birth(T0)
    family.death(store.generation(g.gen), T0 + timedelta(seconds=10))
    return g


def test_a_trial_runs_in_the_background_and_the_birth_waits_for_it_visibly(fam, monkeypatch):
    _cfg, store, _w, family = fam
    g = _dead(fam)
    release, started = threading.Event(), threading.Event()
    real = family.trial

    def slow(gen):
        started.set()
        release.wait(5)
        return real(gen)

    monkeypatch.setattr(family, "trial", slow)
    s = Scheduler(family, background_trials=True)
    t0 = time.monotonic()
    assert s.step(T0 + timedelta(seconds=20)) == "waiting:trial"  # returns at once, birth waits
    assert time.monotonic() - t0 < 2 and started.wait(2)
    assert s.describe()["trials_running"] == [g.gen]
    assert store.generation(g.gen).state == "dead"
    texts = [r["text"] for r in store.q("SELECT text FROM events WHERE kind='life'")]
    assert any("waits for gen 1's trial" in t for t in texts)
    assert s.step(T0 + timedelta(seconds=35)) == "waiting:trial"  # still waiting, said once
    assert (
        sum("waits for gen 1's trial" in r["text"] for r in store.q("SELECT text FROM events")) == 1
    )
    release.set()
    s._trials[g.gen][0].join(5)
    assert store.generation(g.gen).state == "tried"
    assert s.step(T0 + timedelta(seconds=50)) == "born:2"


def test_a_birth_stops_waiting_for_a_trial_after_the_bound(fam, monkeypatch):
    _cfg, store, _w, family = fam
    g = _dead(fam)
    release = threading.Event()
    monkeypatch.setattr(family, "trial", lambda gen: release.wait(5))
    monkeypatch.setattr(sched, "TRIAL_WAIT_MAX_SECONDS", 0)
    s = Scheduler(family, background_trials=True)
    assert s.step(T0 + timedelta(seconds=20)).startswith("born:")
    texts = [r["text"] for r in store.q("SELECT text FROM events WHERE kind='life'")]
    assert any("no longer waits" in t for t in texts)
    release.set()
    s._trials[g.gen][0].join(5)


def test_admin_tick_answers_quickly_while_a_step_is_still_running(fam, monkeypatch):
    _cfg, _store, _w, family = fam
    s = Scheduler(family)
    release = threading.Event()
    monkeypatch.setattr(s, "step", lambda *a, **k: release.wait(5) and "born:9")
    t0 = time.monotonic()
    out = s.tick_now(wait=0.1)
    assert out["state"] == "running" and time.monotonic() - t0 < 2
    assert s.tick_now(wait=0.1)["state"] == "running"  # not a second step on top of the first
    release.set()
    s._tick_thread.join(5)
    monkeypatch.setattr(s, "step", lambda *a, **k: "waiting")
    assert s.tick_now(wait=2)["state"] == "waiting"


def test_admin_tick_route_returns_202_while_running(monkeypatch):
    from fastapi.testclient import TestClient

    from probate.courthouse import app as app_mod

    monkeypatch.setattr(app_mod.settings, "admin_token", "tok", raising=False)
    monkeypatch.setattr(type(app_mod.settings), "on_demand", property(lambda self: False))
    monkeypatch.setattr(app_mod.scheduler, "tick_now", lambda: {"state": "running", "clock": {}})
    c = TestClient(app_mod.app)
    r = c.post("/admin/tick", headers={"X-Probate-Admin": "tok"})
    assert r.status_code == 202 and r.json()["state"] == "running"


# ---------------------------------------------------------------- deploy starts the service once
def _deploy():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "scripts" / "deploy.py"
    spec = importlib.util.spec_from_file_location("deploy_script", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Fly:
    def __init__(self, status):
        self.calls, self.status = [], status

    def put_service(self, name, service, cmd, args, http_port=None):
        self.calls.append("put")

    def service_status(self, name, service):
        return self.status

    def service_action(self, name, service, action):
        self.calls.append(action)


def test_a_first_deploy_starts_the_service_exactly_once():
    d = _deploy()
    started = _Fly("running")  # registering it already started it
    d.start_courthouse(started, "x", fresh=True, wait=lambda s: None)
    assert started.calls == ["put"]
    idle = _Fly(None)  # registering did not start it
    d.start_courthouse(idle, "x", fresh=True, wait=lambda s: None)
    assert idle.calls == ["put", "start"]


def test_a_later_deploy_restarts_once_and_never_starts():
    d = _deploy()
    fly = _Fly("running")
    d.start_courthouse(fly, "x", fresh=False, wait=lambda s: None)
    assert fly.calls == ["put", "restart"]
