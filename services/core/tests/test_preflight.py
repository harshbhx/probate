"""The operator's status route and the laptop preflight script."""

import importlib
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import courthouse

TOKEN = "test-admin-token-long-enough"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PROBATE_ADMIN_TOKEN", TOKEN)
    from probate.common import config

    importlib.reload(config)
    from probate.courthouse import app as app_mod

    importlib.reload(app_mod)
    yield TestClient(app_mod.app), app_mod
    monkeypatch.delenv("PROBATE_ADMIN_TOKEN")
    importlib.reload(config)


def test_status_needs_the_admin_token(client):
    c, _ = client
    assert c.get("/admin/status").status_code == 403


def test_status_reports_what_a_run_depends_on(client):
    c, app_mod = client
    app_mod.store.set_setting("paused", "1")
    d = c.get("/admin/status", headers={"X-Probate-Admin": TOKEN}).json()
    assert d["paused"] is True and d["living"] is None and d["next_gen"] == 1
    assert d["mail"]["next_life_needs"] > 0
    assert set(d["budget"]) == {"spent_usd", "limit_usd"}
    assert isinstance(d["recent_errors"], list) and d["judge"]


def test_a_sprites_sign_in_redirect_means_private():
    private = httpx.Response(
        302, headers={"location": "https://sprites.dev/auth/sprite?return_url=x"}
    )
    assert courthouse.is_private(private)
    assert not courthouse.is_private(httpx.Response(200))
    assert not courthouse.is_private(
        httpx.Response(302, headers={"location": "https://example.com/elsewhere"})
    )
