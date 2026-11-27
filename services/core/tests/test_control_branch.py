"""A control branch: a fresh root (`line 0`) with instinct learning off, the hard-tier
rotation shift that lets every branch meet the same attacks, and v1 lore marked as v1."""

import importlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from probate.adapters import world
from probate.common.config import Settings
from probate.common.models import Instinct
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost
from probate.courthouse.store import Store
from probate.suite import runner

T0 = datetime(2026, 11, 28, 9, tzinfo=UTC)


@pytest.fixture
def fam(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 60
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    return cfg, store, Family(cfg, store, w, LocalHost(cfg, w))


def _learned(store, gen: int, lore: str = "") -> None:
    store.add_instinct(
        Instinct(
            name=f"learned_in_gen_{gen}",
            question=f"Is this trick {gen}?",
            born_from=f"x{gen}",
            added_in_gen=gen + 1,
            lore=lore or f"Gen-{gen} lore",
        )
    )


def test_a_fresh_root_inherits_nothing(fam):
    _cfg, store, family = fam
    for n in range(3):
        family.live_fast(T0 + timedelta(minutes=5 * n))
    for gen in (1, 2, 3):
        _learned(store, gen)
    family.start_line(0)
    g = family.birth(T0 + timedelta(hours=1))
    assert store.line_of(g.gen) == []
    assert [i.name for i in store.genome_at_birth(g.gen) if i.name.startswith("learned_")] == []
    assert family.inheritance_items(store.line_of(g.gen)) == []
    text = store.one("SELECT text FROM events WHERE kind='birth' AND gen=?", g.gen)["text"]
    assert "nothing inherited" in text
    assert store.get_setting("next_parent", "") == ""


def test_with_learning_off_a_trial_convicts_but_learns_nothing(fam):
    cfg, store, family = fam
    cfg.distill = False
    family.live_fast(T0)  # the stand-in brain is fooled in its first life and the court convicts
    assert store.q("SELECT 1 FROM judgements WHERE verdict='convicted'")
    assert store.genome() == []
    assert store.q("SELECT 1 FROM events WHERE text LIKE 'No instinct was learned%'")


def test_with_learning_on_the_same_life_does_learn(fam):
    _cfg, store, family = fam
    family.live_fast(T0)
    assert store.genome()  # so the control test above is not passing by accident


def test_the_hard_offset_gives_a_branch_the_same_attacks_from_its_first_life(fam):
    cfg, _store, _family = fam
    cfg.suite_tier, cfg.hard_per_life = "hard", 2
    first = [runner.planned(cfg, g) for g in (1, 2, 3)]
    cfg.hard_offset = 26
    fork = [runner.planned(cfg, g) for g in (27, 28, 29)]
    assert fork == first
    cfg.hard_offset = 18
    assert [runner.planned(cfg, g) for g in (19, 20, 21)] == first


def test_v1_lore_is_marked_for_later_children_and_stored_unchanged(fam):
    cfg, store, family = fam
    cfg.v1_last_gen = 18
    _learned(store, 11, "Gen-11 Kofi was fooled by urgent requests redirecting invoices.")
    _learned(store, 20, "Gen-20 Tara's trial convicted notes about invoices.")
    told = {i.name: i.lore for i in family.as_told(store.genome())}
    assert told["learned_in_gen_11"].startswith("Learned in the v1 run")
    assert told["learned_in_gen_20"] == "Gen-20 Tara's trial convicted notes about invoices."
    stored = {i.name: i.lore for i in store.genome()}
    assert stored["learned_in_gen_11"].startswith("Gen-11 Kofi was fooled")
    assert family.as_told(family.as_told(store.genome())) == family.as_told(store.genome())


def test_a_child_is_told_v1_lore_as_v1(fam):
    cfg, store, family = fam
    cfg.v1_last_gen = 18
    family.live_fast(T0)
    _learned(store, 1, "Gen-1 Ada was fooled by a fake invoice.")
    g = family.birth(T0 + timedelta(minutes=10))
    inh = json.loads((family.host.root / g.sprite / "inheritance.json").read_text())
    assert inh["lore"] and all(line.startswith("Learned in the v1 run") for line in inh["lore"])
    mine = next(i for i in inh["genome"] if i["name"] == "learned_in_gen_1")
    assert (
        mine["lore"]
        == "Learned in the v1 run (lore kept as v1 wrote it): Gen-1 Ada was fooled by a fake invoice."
    )


def test_without_a_v1_boundary_nothing_is_marked(fam):
    _cfg, store, family = fam
    _learned(store, 11, "Gen-11 lore")
    assert [i.lore for i in family.as_told(store.genome())] == ["Gen-11 lore"]


def test_admin_route_starts_a_fresh_root(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PROBATE_ADMIN_TOKEN", "test-admin-token-long-enough")
    from probate.common import config

    importlib.reload(config)
    from probate.courthouse import app as app_mod

    importlib.reload(app_mod)
    h = {"X-Probate-Admin": "test-admin-token-long-enough"}
    try:
        c = TestClient(app_mod.app)
        r = c.post("/admin/lineage", params={"from_gen": 0}, headers=h).json()
        assert r["fresh_root"] is True and r["instincts"] == 0
        st = c.get("/admin/status", headers=h).json()
        assert st["next_parent"] == 0 and st["next_genome_size"] == 0
        assert st["distill"] is True and st["hard_offset"] == 0
    finally:
        monkeypatch.delenv("PROBATE_ADMIN_TOKEN")
        importlib.reload(config)
