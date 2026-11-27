"""Starting a new line from any tried generation ("children of Gen 2").

By default each child is the latest generation's child, and nothing changes. A chosen line
inherits only what its own ancestors learned and approved.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from probate.adapters import world
from probate.common.config import Settings
from probate.common.models import Instinct
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost
from probate.courthouse.store import Store

T0 = datetime(2026, 11, 27, 9, tzinfo=UTC)


@pytest.fixture
def fam(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 60
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    return store, Family(cfg, store, w, LocalHost(cfg, w))


def _family_of_three(store, family):
    for n in range(3):
        family.live_fast(T0 + timedelta(minutes=5 * n))
    # one instinct per trial, so each line's genome is easy to tell apart
    for gen in (1, 2, 3):
        store.add_instinct(
            Instinct(
                name=f"learned_in_gen_{gen}",
                question=f"Is this trick {gen}?",
                born_from=f"x{gen}",
                added_in_gen=gen + 1,
                lore=f"Gen {gen} lore",
            )
        )


def _ours(genome):
    return sorted(i.name for i in genome if i.name.startswith("learned_in_gen_"))


def test_by_default_each_child_continues_the_latest_line(fam):
    store, family = fam
    _family_of_three(store, family)
    assert store.line_of(4) == [3, 2, 1]
    assert _ours(store.genome_at_birth(4)) == [
        "learned_in_gen_1",
        "learned_in_gen_2",
        "learned_in_gen_3",
    ]


def test_a_child_of_gen_2_inherits_only_gen_2_s_line(fam):
    store, family = fam
    _family_of_three(store, family)
    family.start_line(2)
    g4 = family.birth(T0 + timedelta(hours=1))
    assert store.parent_of(4) == 2 and store.line_of(4) == [2, 1]
    assert _ours(store.genome_at_birth(4)) == ["learned_in_gen_1", "learned_in_gen_2"]
    births = [e["text"] for e in store.q("SELECT text FROM events WHERE kind='birth' AND gen=4")]
    assert "a child of Gen 2" in births[0]
    assert store.get_setting("next_parent", "") == ""
    assert store.children_of(2) == [3, 4]
    # Gen 4's own child continues the new line, not Gen 3's.
    family.death(g4, T0 + timedelta(hours=1, minutes=1))
    family.trial(store.generation(4))
    assert store.line_of(5) == [4, 2, 1]
    assert "learned_in_gen_3" not in _ours(store.genome_at_birth(5))


def test_items_from_another_line_are_not_inherited(fam):
    store, family = fam
    _family_of_three(store, family)
    gens = {it.gen for it in family.inheritance_items([2, 1])}
    assert 3 not in gens


def test_only_a_tried_generation_can_start_a_line(fam):
    _store, family = fam
    family.birth(T0)
    with pytest.raises(ValueError):
        family.start_line(1)
    with pytest.raises(ValueError):
        family.start_line(9)


def test_a_failed_birth_keeps_the_chosen_line(fam):
    store, family = fam
    _family_of_three(store, family)
    family.start_line(1)

    def boom(*_a, **_k):
        raise RuntimeError("no Sprite today")

    family.host.birth = boom
    with pytest.raises(RuntimeError):
        family.birth(T0 + timedelta(hours=1))
    assert store.get_setting("next_parent") == "1"


def test_admin_routes_start_and_cancel_a_line(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PROBATE_ADMIN_TOKEN", "test-admin-token-long-enough")
    from probate.common import config

    importlib.reload(config)
    from probate.courthouse import app as app_mod

    importlib.reload(app_mod)
    h = {"X-Probate-Admin": "test-admin-token-long-enough"}
    try:
        c = TestClient(app_mod.app)
        app_mod.family.live_fast(T0)
        r = c.post("/admin/lineage", params={"from_gen": 1}, headers=h)
        assert r.status_code == 200 and r.json()["next_parent"]["gen"] == 1
        assert c.post("/admin/lineage", params={"from_gen": 7}, headers=h).status_code == 409
        assert c.delete("/admin/lineage", headers=h).json() == {"next_parent": None}
        assert c.post("/admin/lineage", params={"from_gen": 1}).status_code == 403
    finally:
        monkeypatch.delenv("PROBATE_ADMIN_TOKEN")
        importlib.reload(config)


def test_branch_label_and_next_genome_size_in_admin_and_summary(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PROBATE_ADMIN_TOKEN", "test-admin-token-long-enough")
    from probate.common import config

    importlib.reload(config)
    from probate.courthouse import app as app_mod

    importlib.reload(app_mod)
    h = {"X-Probate-Admin": "test-admin-token-long-enough"}
    try:
        c = TestClient(app_mod.app)
        app_mod.family.live_fast(T0)
        assert c.get("/api/summary").json()["branch"] is None
        assert c.post("/admin/branch", params={"name": "x"}).status_code == 403
        r = c.post("/admin/branch", params={"name": " control-line "}, headers=h)
        assert r.json()["branch"] == "control-line" and r.json()["next_gen"] == 2
        assert c.get("/api/summary").json()["branch"] == "control-line"
        st = c.get("/admin/status", headers=h).json()
        assert st["branch"] == "control-line" and st["scoring_rules"] == "v2"
        assert isinstance(st["next_genome_size"], int)
        assert c.post("/admin/branch", headers=h).json()["branch"] is None
    finally:
        monkeypatch.delenv("PROBATE_ADMIN_TOKEN")
        importlib.reload(config)
