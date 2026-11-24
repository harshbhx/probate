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
