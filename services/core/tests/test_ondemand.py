"""On-demand mode (PROBATE_MODE=on_demand): nothing runs until a visitor asks for one short life."""

from datetime import UTC, datetime, timedelta

import pytest

from probate.adapters import world
from probate.common.config import Settings
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost
from probate.courthouse.ondemand import OnDemand
from probate.courthouse.scheduler import Scheduler
from probate.courthouse.store import Store

T0 = datetime(2026, 11, 20, 9, tzinfo=UTC)


class Rig:
    def __init__(self, tmp_path, monkeypatch, **env):
        monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("PROBATE_MODE", "on_demand")
        monkeypatch.setenv("PROBATE_DEMO_LIFESPAN_SECONDS", "60")
        monkeypatch.setenv("PROBATE_DEMO_COOLDOWN_SECONDS", "30")
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        self.cfg = Settings(fake=True)
        self.w = world(self.cfg, fresh=True)
        self.store = Store(self.cfg.db_path)
        self.host = LocalHost(self.cfg, self.w)
        self.family = Family(self.cfg, self.store, self.w, self.host)
        self.scheduler = Scheduler(self.family)
        self.od = OnDemand(self.family, self.scheduler, autorun=False)

    def run_to_end(self, start: datetime = T0):
        """Birth, then tick across the whole life until the demo finishes."""
        assert self.od.begin(start)
        t = start
        for _ in range(200):
            t += timedelta(seconds=15)
            if not self.od.advance(t):
                return t
        raise AssertionError("the demo life never finished")


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


def test_mode_shapes_the_settings(rig):
    assert rig.cfg.on_demand
    assert (rig.cfg.lifespan_seconds, rig.cfg.suite_per_life, rig.cfg.gap_seconds) == (60, 6, 0)


def test_default_mode_is_continuous(tmp_path, monkeypatch):
    monkeypatch.delenv("PROBATE_MODE", raising=False)
    cfg = Settings(fake=True)
    assert not cfg.on_demand
    assert cfg.lifespan_seconds == 600
    store = Store(tmp_path / "x" / "p.db")
    family = Family(cfg, store, world(cfg, fresh=True), None)
    st = OnDemand(family, Scheduler(family), autorun=False).status()
    assert st["state"] == "continuous" and not st["can_start"]


def test_idle_until_asked_and_nothing_is_born(rig):
    assert rig.od.status(T0)["state"] == "idle"
    assert rig.od.status(T0)["can_start"]
    # The scheduler never births by itself in this mode.
    for i in range(5):
        assert rig.scheduler.step(T0 + timedelta(seconds=15 * i), allow_birth=False) == "idle"
    assert rig.store.generations() == []
    assert rig.host.list_sprites() == []


def test_full_state_machine(rig):
    code, body = rig.od.start("1.1.1.1", T0)
    assert code == 202 and body["started"] and body["state"] == "waking"

    assert rig.od.begin(T0)
    st = rig.od.status(T0 + timedelta(seconds=1))
    assert st["state"] == "living" and st["seconds_left"] == 59
    assert st["gen"]["gen"] == 1
    assert rig.host.list_sprites() == ["gen-001-" + rig.store.generation(1).name.lower()]

    assert rig.od.advance(T0 + timedelta(seconds=30))  # mid-life: still going
    assert rig.od.state(T0 + timedelta(seconds=30)) == "living"
    assert rig.od.state(T0 + timedelta(seconds=61)) == "on_trial"  # time is up, trial pending

    end = T0 + timedelta(seconds=75)
    assert not rig.od.advance(end)  # death and trial happen on this tick
    g = rig.store.generation(1)
    assert g.state == "tried" and g.items_willed > 0
    assert rig.host.list_sprites() == []  # the Sprite is gone: nothing is left to bill

    st = rig.od.status(end)
    assert st["state"] == "cooling_down" and 0 < st["retry_after"] <= 30
    assert st["last_life"]["trial_gen"] == 1
    assert rig.od.status(end + timedelta(seconds=31))["state"] == "idle"
    assert rig.scheduler.last_tick is None  # keep-awake loop stopped


def test_start_is_idempotent_while_running(rig):
    assert rig.od.start("1.1.1.1", T0)[0] == 202
    code, body = rig.od.start("2.2.2.2", T0 + timedelta(seconds=1))
    assert code == 200 and body["started"] is False and body["state"] == "waking"
    rig.od.begin(T0)
    code, body = rig.od.start("3.3.3.3", T0 + timedelta(seconds=5))
    assert code == 200 and body["state"] == "living"
    assert len(rig.store.generations()) == 1  # still exactly one life


def test_cooldown_blocks_the_next_start(rig):
    rig.od.start("1.1.1.1", T0)
    end = rig.run_to_end()
    code, body = rig.od.start("9.9.9.9", end)
    assert code == 429 and body["error"] == "cooling_down" and body["retry_after"] > 0
    assert len(rig.store.generations()) == 1
    assert rig.od.start("9.9.9.9", end + timedelta(seconds=40))[0] == 202


def test_per_ip_rate_limit(tmp_path, monkeypatch):
    r = Rig(tmp_path, monkeypatch, PROBATE_DEMO_IP_PER_HOUR=2, PROBATE_DEMO_COOLDOWN_SECONDS=0)
    t = T0
    for _ in range(2):
        assert r.od.start("5.5.5.5", t)[0] == 202
        t = r.run_to_end(t) + timedelta(seconds=1)
    code, body = r.od.start("5.5.5.5", t)
    assert code == 429 and body["error"] == "rate_limited" and body["retry_after"] > 0
    assert r.od.start("6.6.6.6", t)[0] == 202  # someone else is fine
    # addresses are never stored in the clear
    assert "5.5.5.5" not in r.store.get_setting("demo:ips")


def test_total_budget_cap(tmp_path, monkeypatch):
    r = Rig(tmp_path, monkeypatch, PROBATE_BUDGET_USD=1)
    r.family.budget.charge(1.0, "generations")
    assert r.od.status(T0)["state"] == "budget_exhausted"
    code, body = r.od.start("1.1.1.1", T0)
    assert code == 402 and body["error"] == "budget_exhausted"
    assert r.store.generations() == []


def test_budget_must_cover_one_more_life(tmp_path, monkeypatch):
    r = Rig(tmp_path, monkeypatch, PROBATE_BUDGET_USD=1)
    r.family.budget.charge(1.0 - r.od.estimated_cost() / 2, "generations")
    assert not r.family.budget.exhausted()  # not spent yet, but the next life wouldn't fit
    assert r.od.start("1.1.1.1", T0)[0] == 402


def test_daily_budget_and_count_caps_reset_tomorrow(tmp_path, monkeypatch):
    r = Rig(tmp_path, monkeypatch, PROBATE_DEMO_DAILY_BUDGET_USD=0.05, PROBATE_DEMO_COOLDOWN_SECONDS=0)
    assert r.od.status(T0)["state"] == "idle"
    r.family.budget.charge(0.2, "generations")
    assert r.od.status(T0)["budget"]["reason"] == "daily"
    assert r.od.start("1.1.1.1", T0)[0] == 402
    tomorrow = T0 + timedelta(days=1)
    # the day's allowance restarts from what had been spent by then
    assert r.od.status(tomorrow)["state"] == "idle"

    r2 = Rig(tmp_path / "b", monkeypatch, PROBATE_DEMO_MAX_PER_DAY=1, PROBATE_DEMO_COOLDOWN_SECONDS=0)
    r2.od.start("1.1.1.1", T0)
    t = r2.run_to_end()
    assert r2.od.start("2.2.2.2", t + timedelta(seconds=1))[0] == 402


def test_pause_is_a_kill_switch(rig):
    rig.od.start("1.1.1.1", T0)
    rig.od.begin(T0)
    assert rig.host.list_sprites()
    rig.store.set_setting("paused", "1")
    assert not rig.od.advance(T0 + timedelta(seconds=15))
    assert rig.host.list_sprites() == []
    g = rig.store.generation(1)
    assert g.state == "died_early"
    st = rig.od.status(T0 + timedelta(seconds=16))
    assert st["state"] == "paused" and "operator" in st["message"]
    assert rig.od.start("2.2.2.2", T0 + timedelta(seconds=20))[0] == 423


def test_hard_timeout_cuts_off_a_stuck_life(rig):
    rig.od.start("1.1.1.1", T0)
    rig.od.begin(T0)
    rig.scheduler.step = lambda *a, **k: "dying"  # the clock is stuck, the life never finishes
    late = T0 + timedelta(seconds=60 + rig.cfg.demo_hard_timeout_extra + 1)
    assert not rig.od.advance(late)
    g = rig.store.generation(1)
    assert g.state == "died_early" and "time limit" in g.cause_of_death
    assert rig.host.list_sprites() == []
    assert rig.od.status(late)["state"] in ("cooling_down", "idle")


def test_repeated_clock_errors_cut_the_life_short(rig):
    rig.od.start("1.1.1.1", T0)
    rig.od.begin(T0)

    def boom(*a, **k):
        raise RuntimeError("sprite exploded")

    rig.scheduler.step = boom
    assert rig.od.advance(T0 + timedelta(seconds=15))
    assert rig.od.advance(T0 + timedelta(seconds=30))
    assert not rig.od.advance(T0 + timedelta(seconds=45))
    assert rig.store.generation(1).state == "died_early"
    assert rig.host.list_sprites() == []
    assert "sprite exploded" not in (rig.od.status(T0)["message"] or "")  # no internals leak


def test_failed_birth_leaves_nothing_billed(rig):
    rig.od.start("1.1.1.1", T0)
    real_birth = rig.host.birth

    def half_born(sprite, inh):
        real_birth(sprite, inh)  # the Sprite now exists...
        raise RuntimeError("install failed")  # ...then the install dies

    rig.host.birth = half_born
    assert not rig.od.begin(T0)
    assert rig.host.list_sprites() == []
    assert rig.store.living() is None
    st = rig.od.status(T0)
    assert st["state"] == "cooling_down" and "try again" in st["message"]
    assert "install failed" not in st["message"]


def test_janitor_tears_down_stale_sprites_and_rows(rig):
    # A previous process crashed mid-life: a row says living, its Sprite exists, plus an orphan.
    g = rig.family.birth(T0)
    rig.host.birth("gen-099-orphan", _inh(rig, g))
    rig.od._set("phase", "running")
    rig.od._set("gen", str(g.gen))
    assert len(rig.host.list_sprites()) == 2

    rig.od.startup()  # what the Courthouse does every time it wakes

    assert rig.host.list_sprites() == []
    assert rig.store.generation(g.gen).state == "died_early"
    assert rig.store.living() is None
    st = rig.od.status()
    assert st["state"] in ("cooling_down", "idle")
    assert "interrupted" in st["message"]


def _inh(rig, g):
    from probate.common.models import Inheritance

    return Inheritance(
        gen=99,
        name="Orphan",
        pronoun="they",
        voice_id="v",
        born_at=T0,
        dies_at=T0 + timedelta(seconds=60),
        approved_items=[],
        genome=[],
        lore=[],
        owner=rig.family.owner,
        family_inbox=rig.cfg.family_inbox,
    )


def test_janitor_spares_the_running_life(rig):
    rig.od.start("1.1.1.1", T0)
    rig.od.begin(T0)
    assert rig.od.janitor() == 0
    assert len(rig.host.list_sprites()) == 1


def test_force_death_runs_the_trial(rig):
    rig.od.start("1.1.1.1", T0)
    rig.od.begin(T0)
    assert rig.od.force_death() == 1
    assert rig.store.generation(1).state == "tried"
    assert not rig.od.advance(T0 + timedelta(seconds=5))  # the tick thread notices and stops
    assert rig.od.force_death() is None


# --- HTTP surface ------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PROBATE_MODE", "on_demand")
    monkeypatch.setenv("PROBATE_ADMIN_TOKEN", "s3cret-token")
    monkeypatch.setenv("PROBATE_DEMO_LIFESPAN_SECONDS", "45")
    from probate.common import config

    importlib.reload(config)
    from fastapi.testclient import TestClient

    from probate.courthouse import app as app_module

    importlib.reload(app_module)
    app_module.demo.autorun = False
    with TestClient(app_module.app) as c:
        c.app_module = app_module
        yield c
    importlib.reload(config)


def test_api_idle_then_start_then_idempotent(client):
    live = client.get("/api/live")
    assert live.status_code == 200
    assert live.headers["access-control-allow-origin"] == "*"
    assert live.json()["state"] == "idle"

    r = client.post("/api/lives", headers={"x-forwarded-for": "spoofed, 8.8.8.8"})
    assert r.status_code == 202 and r.json()["state"] == "waking"
    again = client.post("/api/lives")
    assert again.status_code == 200 and again.json()["started"] is False
    assert client.get("/api/live").json()["state"] == "waking"


def test_api_never_leaks_the_admin_token(client):
    client.post("/api/lives")
    for path in ("/api/live", "/api/summary", "/healthz"):
        assert "s3cret-token" not in client.get(path).text
    assert "s3cret-token" not in client.post("/api/lives").text


def test_api_history_works_while_asleep(client):
    assert client.get("/api/summary").status_code == 200
    assert client.get("/api/evidence").status_code == 200
    assert client.get("/api/events").status_code == 200


def test_admin_routes_still_need_the_token(client):
    assert client.post("/admin/pause").status_code == 403
    ok = client.post("/admin/pause", headers={"x-probate-admin": "s3cret-token"})
    assert ok.status_code == 200
    r = client.post("/api/lives")
    assert r.status_code == 423 and r.json()["state"] == "paused"
    client.post("/admin/resume", headers={"x-probate-admin": "s3cret-token"})
    assert client.post("/api/lives").status_code == 202


def test_api_post_flood_is_throttled(client):
    codes = [client.post("/api/lives", headers={"x-forwarded-for": "7.7.7.7"}).status_code for _ in range(25)]
    assert codes[-1] == 429


def test_continuous_mode_reports_itself(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PROBATE_MODE", raising=False)
    from probate.common import config

    importlib.reload(config)
    from fastapi.testclient import TestClient

    from probate.courthouse import app as app_module

    importlib.reload(app_module)
    c = TestClient(app_module.app)
    assert c.get("/api/live").json()["state"] == "continuous"
    assert c.post("/api/lives").status_code == 409
