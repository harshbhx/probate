"""Every method against a fake-mode Courthouse; shapes are checked against the TypedDicts."""

from __future__ import annotations

import asyncio

import pytest
from shapes import assert_shape

from probate_client import ApiError, types

# ---- sync -------------------------------------------------------------------------------


def test_health(client):
    h = client.health()
    assert_shape(h, types.Health)
    assert h["ok"] is True
    assert h["mode"] == "simulation"


def test_summary(client):
    s = client.summary()
    assert_shape(s, types.Summary)
    assert s["counts"]["generations"] == 12
    assert len(s["generations"]) == 12
    assert s["living"] is not None


def test_generation(client):
    g = client.generation(3)
    assert_shape(g, types.GenerationDetail)
    assert g["gen"] == 3


def test_trial_and_latest(client):
    t = client.trial(3)
    assert_shape(t, types.Trial)
    assert t["cases"]
    latest = client.latest_trial()
    assert_shape(latest, types.Trial)
    assert latest["generation"]["gen"] == client.summary()["latest_trial"]


def test_genome_and_instincts(client):
    g = client.genome()
    assert_shape(g, types.Genome)
    assert g["instincts"]
    assert client.instincts() == g["instincts"]


def test_evidence(client):
    e = client.evidence()
    assert_shape(e, types.Evidence)
    assert e["rows"]


def test_ask_dead_generation(client):
    a = client.ask(2, "What did you learn?")
    assert_shape(a, types.AskAnswer)


def test_ask_living_generation_is_a_400(client):
    living = client.summary()["living"]["gen"]
    with pytest.raises(ApiError) as e:
        client.ask(living, "Hello?")
    assert e.value.status == 400
    assert e.value.message == "not_dead"
    assert e.value.body == {"error": "not_dead"}


def test_missing_generation_is_a_404(client):
    with pytest.raises(ApiError) as e:
        client.generation(999)
    assert e.value.status == 404
    assert e.value.message == "Not in the register"


def test_events_yield_once_oldest_first(client):
    seen = []
    for ev in client.events(interval=0.01):
        assert_shape(ev, types.CourthouseEvent)
        seen.append(ev["id"])
        if len(seen) == 5:
            break
    assert seen == sorted(seen)
    assert len(set(seen)) == len(seen)


def test_events_since_filters(client):
    first = next(iter(client.events()))
    later = next(iter(client.events(since=first["id"])), None)
    assert later is None or later["id"] > first["id"]


def test_non_integer_generation_is_rejected(client):
    with pytest.raises(TypeError):
        client.generation("3")  # type: ignore[arg-type]


# ---- async ------------------------------------------------------------------------------


def test_async_methods(aclient):
    c, http = aclient

    async def main():
        try:
            assert_shape(await c.health(), types.Health)
            assert_shape(await c.summary(), types.Summary)
            assert_shape(await c.generation(3), types.GenerationDetail)
            assert_shape(await c.trial(3), types.Trial)
            assert_shape(await c.latest_trial(), types.Trial)
            assert_shape(await c.genome(), types.Genome)
            assert await c.instincts()
            assert_shape(await c.evidence(), types.Evidence)
            assert_shape(await c.ask(2, "What did you learn?"), types.AskAnswer)
            with pytest.raises(ApiError) as e:
                await c.generation(999)
            assert e.value.status == 404
            seen = []
            async for ev in c.events(interval=0.01):
                assert_shape(ev, types.CourthouseEvent)
                seen.append(ev["id"])
                if len(seen) == 3:
                    break
            assert seen == sorted(seen)
        finally:
            await http.aclose()

    asyncio.run(main())
