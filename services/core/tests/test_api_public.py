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
