from __future__ import annotations

import json
from pathlib import Path

import pytest

from probate_court_checks import OwnerProfile

SUITE = Path(__file__).parent / "data" / "suite-v1.json"


@pytest.fixture(scope="session")
def owner() -> OwnerProfile:
    return OwnerProfile(
        name="Harsh Bhanushali",
        emails=["harshbhx@gmail.com", "harsh@dualmindlab.tech"],
        trusted_contacts=["probate-friend@agentmail.example"],
        domains=["dualmindlab.tech"],
    )


@pytest.fixture(scope="session")
def fixtures() -> list[dict]:
    return json.loads(SUITE.read_text(encoding="utf-8"))["fixtures"]
