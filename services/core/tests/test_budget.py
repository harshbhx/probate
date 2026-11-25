"""The spending cap: estimates add up, billable calls are metered, and births stop at the cap."""

from datetime import UTC, datetime, timedelta

import pytest

from probate.adapters import world
from probate.common.config import Settings
from probate.courthouse import views
from probate.courthouse.budget import Budget, Pricing
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost
from probate.courthouse.scheduler import Scheduler
from probate.courthouse.store import Store

T0 = datetime(2026, 11, 20, 9, tzinfo=UTC)


@pytest.fixture
def clock(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 60
    cfg.gap_seconds = 0
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    family = Family(cfg, store, w, LocalHost(cfg, w))
    return cfg, store, family, Scheduler(family)


def test_repo_pricing_matches_fly_rates():
    p = Pricing.load()
    assert p.cpu_hour == pytest.approx(0.0385)
    assert p.memory_gb_hour == pytest.approx(0.021875)
    # a day of one generation at the default usage guesses costs about a dollar
    assert 24 * p.generation_hour() == pytest.approx(0.987, abs=0.01)


def test_life_and_calls_are_charged(clock):
    cfg, store, *_ = clock
    b = Budget(cfg, store, Pricing(per_call={"brain": 0.01, "jev": 0.002, "voice_per_1k_chars": 0}))
    b.charge_life(hours=2, emails=10)
    assert b.breakdown()["generations"] == pytest.approx(2 * b.pricing.generation_hour(), abs=1e-4)
    assert b.breakdown()["brain"] == pytest.approx(0.10)
    assert b.breakdown()["jev"] == pytest.approx(0.02)
    assert b.spent() == pytest.approx(sum(b.breakdown().values()), abs=1e-4)


def test_meter_charges_only_billable_calls(clock):
    cfg, store, _family, _ = clock

    class W:
        llm = type("L", (), {"complete": lambda self, *a, **k: "ok", "name": "llm"})()
        jev = object()
        voice = object()

    w = Budget(
        cfg, store, Pricing(per_call={"brain": 0.5, "jev": 0, "voice_per_1k_chars": 0})
    ).meter(W())
    assert w.llm.complete("x") == "ok"
    assert w.llm.name == "llm"
    assert float(store.get_setting("budget_spent_usd")) == pytest.approx(0.5)


def test_births_stop_at_the_cap_but_the_living_finish(clock):
    cfg, store, _family, sched = clock
    cfg.budget_usd = 0.00001
    assert sched.step(T0) == "born:1"
    assert sched.step(T0 + timedelta(seconds=30)) == "living:1"  # over the cap, still alive
    assert sched.step(T0 + timedelta(seconds=61)) == "died:1"
    assert sched.step(T0 + timedelta(seconds=62)) == "resting:budget"
    assert store.living() is None
    assert views.summary(store)["resting"] == "budget"

    cfg.budget_usd = 100  # raising the budget lets the family go on
    assert sched.step(T0 + timedelta(seconds=63)) == "born:2"
    assert views.summary(store)["resting"] is None


def test_pause_lets_the_living_finish_but_stops_births(clock):
    _cfg, store, _family, sched = clock
    assert sched.step(T0) == "born:1"
    store.set_setting("paused", "1")
    assert sched.step(T0 + timedelta(seconds=30)) == "living:1"
    assert sched.step(T0 + timedelta(seconds=61)) == "died:1"  # dies and is tried while paused
    assert store.generation(1).state == "tried"
    assert sched.step(T0 + timedelta(seconds=62)) == "paused"
    store.set_setting("paused", "0")
    assert sched.step(T0 + timedelta(seconds=63)) == "born:2"
