"""A fake-mode Courthouse with 12 simulated generations (the Makefile `sim` target).

Needs the core installed in the same environment: `pip install -e services/core`.
"""

from __future__ import annotations

import os
import subprocess
import sys

import httpx
import pytest


@pytest.fixture(scope="session")
def courthouse_app(tmp_path_factory):
    data = tmp_path_factory.mktemp("courthouse")
    env = {**os.environ, "PROBATE_FAKE": "1", "PROBATE_DATA_DIR": str(data), "PYTHONUTF8": "1"}
    sim = subprocess.run(
        [sys.executable, "-m", "probate.courthouse.simulate", "--generations", "12"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert sim.returncode == 0, sim.stdout + sim.stderr
    os.environ.update(PROBATE_FAKE="1", PROBATE_DATA_DIR=str(data))
    from probate.courthouse import app as app_module

    return app_module.app


@pytest.fixture()
def client(courthouse_app):
    from fastapi.testclient import TestClient

    from probate_client import ProbateClient

    with TestClient(courthouse_app) as tc:
        yield ProbateClient("http://testserver", http_client=tc)


@pytest.fixture()
def aclient(courthouse_app):
    from probate_client import AsyncProbateClient

    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=courthouse_app))
    return AsyncProbateClient("http://testserver", http_client=http), http
