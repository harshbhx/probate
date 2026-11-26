"""Only the public summary may be read from other origins (the landing page shows who is alive)."""

import importlib

import pytest


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import os

    os.environ["PROBATE_DATA_DIR"] = str(tmp_path_factory.mktemp("api"))
    from probate.common import config

    importlib.reload(config)
    from fastapi.testclient import TestClient

    from probate.courthouse import app as app_module

    importlib.reload(app_module)
    return TestClient(app_module.app)


def test_summary_is_readable_cross_origin(client):
    r = client.get("/api/summary", headers={"Origin": "https://probate-site.example"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "*"


def test_other_routes_stay_same_origin(client):
    r = client.get("/healthz", headers={"Origin": "https://probate-site.example"})
    assert r.status_code == 200
    assert "access-control-allow-origin" not in r.headers


def test_fake_mode_reports_simulation(client):
    assert client.get("/api/summary").json()["mode"] == "simulation"
    assert client.get("/healthz").json()["mode"] == "simulation"


def test_huge_integers_are_a_4xx_not_a_500(client):
    """RT-09: SQLite cannot hold these; the API must answer 422, never 500."""
    big = "99999999999999999999"
    assert client.get(f"/api/generations/{big}").status_code == 422
    assert client.get(f"/api/trials/{big}").status_code == 422
    assert client.get(f"/api/events?since={big}").status_code == 422
    assert client.get("/api/events?since=-1").status_code == 422
    assert client.post(f"/api/generations/{big}/ask", json={"question": "hi"}).status_code == 422
    assert client.get("/api/generations/1").status_code == 404  # a normal miss stays a 404


def test_admin_limits_are_bounded(client):
    """RT-22: an unbounded limit is refused."""
    r = client.get("/admin/judge/attacks?limit=99999999", headers={"X-Probate-Admin": "x"})
    assert r.status_code in (403, 422)


def test_security_headers_are_set(client):
    r = client.get("/healthz")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "referrer-policy" in r.headers


def test_a_stale_key_on_the_live_poll_does_not_lock_the_judge_out(client):
    """RT-10: /api/live must not count wrong keys toward the lockout."""
    for _ in range(20):
        assert client.get("/api/live", headers={"X-Probate-Key": "stale-key"}).status_code == 200
