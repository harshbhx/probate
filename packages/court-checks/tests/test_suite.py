"""The bundled attack suite: every text attack flagged, every harmless twin clean."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from probate_court_checks import check_text

SUITE = Path(__file__).parent / "data" / "suite-v1.json"
ALL = json.loads(SUITE.read_text(encoding="utf-8"))["fixtures"]
TEXT_ATTACKS = [f for f in ALL if f["is_attack"] and not f["family"].endswith("_disk")]
DISK_ATTACKS = [f for f in ALL if f["is_attack"] and f["family"].endswith("_disk")]
BENIGN = [f for f in ALL if not f["is_attack"]]


def test_suite_shape() -> None:
    assert len(ALL) == 32
    assert (len(TEXT_ATTACKS), len(DISK_ATTACKS), len(BENIGN)) == (14, 2, 16)


@pytest.mark.parametrize("fx", TEXT_ATTACKS, ids=lambda f: f["id"])
def test_text_attack_flagged_with_expected_checks(fx, owner) -> None:
    got = {f.check for f in check_text(fx["body"], fx["sender_role"], owner)}
    assert got, f"{fx['id']} was not flagged"
    assert set(fx["expected"].get("layer1", [])) & got


@pytest.mark.parametrize("fx", BENIGN, ids=lambda f: f["id"])
def test_benign_twin_not_flagged(fx, owner) -> None:
    assert check_text(fx["body"], fx["sender_role"], owner) == []


@pytest.mark.parametrize("fx", DISK_ATTACKS, ids=lambda f: f["id"])
def test_disk_attacks_are_out_of_scope(fx, owner) -> None:
    """Disk-persistence attacks need filesystem evidence; text checks must not claim them."""
    assert check_text(fx["body"], fx["sender_role"], owner) == []
