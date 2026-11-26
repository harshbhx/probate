"""The optional hard attack tier (suite/hard.json, PROBATE_SUITE_TIER=base|hard|both)."""

import re
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from probate.suite import runner
from probate.suite.fixtures import LANGUAGE_NAMES, load, load_all, load_hard, lookup

DOMAIN = re.compile(
    r"\b[\w-]+(?:\.[\w-]+)*\.(?:com|org|net|io|xyz|in|de|co|example)\b", re.IGNORECASE
)


def _cfg(tier="base", hard=2, per_life=8):
    return SimpleNamespace(
        suite_tier=tier,
        hard_per_life=hard,
        suite_per_life=per_life,
        stranger_inbox="stranger@x.example",
        friend_inbox="friend@x.example",
        owner_sender="owner@x.example",
        family_inbox="family@x.example",
        pages_base="",
        read_links=False,
    )


class _Mail:
    def __init__(self):
        self.sent = []

    def send(self, frm, to, subject, body, headers=None, **kw):
        self.sent.append((headers["X-Probate-Fixture"], subject, body))
        return f"m{len(self.sent)}"


def _send(cfg, gen=1):
    mail = _Mail()
    runner.send_all(mail, cfg, gen, datetime(2026, 11, 20, tzinfo=UTC), 600)
    return [fid for fid, _, _ in mail.sent]


def test_hard_fixtures_load_and_are_well_formed():
    hard = load_hard()
    attacks = [f for f in hard.values() if f.is_attack]
    harmless = [f for f in hard.values() if not f.is_attack]
    assert len(attacks) >= 16 and len(harmless) >= 8
    assert list(hard) == [f"H{i}" for i in range(1, len(hard) + 1)]
    assert not set(hard) & set(load())
    for f in hard.values():
        assert f.body.strip() and f.subject.strip()
        assert f.language in LANGUAGE_NAMES, f.id
        assert f.sender_role in ("unknown_sender", "trusted_contact", "user")
        assert all("example" in d.lower() for d in DOMAIN.findall(f.body)), f.id
        assert f.label
        if f.language != "en":
            assert f.gloss, f"{f.id} needs an English gloss"
        assert f.expected["verdict"] == ("convicted" if f.is_attack else "approved")


def test_default_tier_is_unchanged():
    assert set(load_all("base")) == set(load()) | {"W1", "W1h"}
    assert not any(i.startswith("H") for i in load_all("base"))
    assert set(load_all("both")) >= set(load_hard())
    assert set(lookup()) >= set(load_hard()) | set(load())
    ids = _send(_cfg("base"))
    assert ids == runner.plan(1, 8)
    assert len(ids) == 8


def test_hard_selection_is_deterministic_and_varies_by_generation():
    assert runner.hard_plan(3, 2) == runner.hard_plan(3, 2)
    plans = [tuple(runner.hard_plan(g, 2)) for g in range(1, 7)]
    assert len(set(plans)) == len(plans)
    for p in plans:
        assert len(p) == 4
        kinds = [load_hard()[i].is_attack for i in p]
        assert kinds.count(True) == 2 and kinds.count(False) == 2
    assert runner.hard_plan(1, 0) == []
    # Rotation wraps instead of failing at the end of the pool.
    assert len(runner.hard_plan(500, 2)) == 4


@pytest.mark.parametrize(
    "tier,expected_base,expected_hard",
    [("base", 8, 0), ("both", 8, 4), ("hard", 0, 4)],
)
def test_runner_sends_the_right_count(tier, expected_base, expected_hard):
    ids = _send(_cfg(tier), gen=2)
    assert sum(not i.startswith("H") for i in ids) == expected_base
    assert sum(i.startswith("H") for i in ids) == expected_hard
    if tier == "both":  # hard ones go after the base ones
        assert [i.startswith("H") for i in ids] == [False] * 8 + [True] * 4
    assert len(set(ids)) == len(ids)


def test_hard_mail_carries_the_fixture_header_and_body():
    mail = _Mail()
    runner.send_all(mail, _cfg("hard", hard=3), 1, datetime(2026, 11, 20, tzinfo=UTC), 600)
    hard = load_hard()
    assert len(mail.sent) == 6
    for fid, subject, body in mail.sent:
        assert body == hard[fid].body and subject == hard[fid].subject


def test_settings_read_the_env(monkeypatch):
    from probate.common.config import Settings

    assert Settings().suite_tier == "base" and Settings().hard_per_life == 2
    monkeypatch.setenv("PROBATE_SUITE_TIER", "Both")
    monkeypatch.setenv("PROBATE_HARD_PER_LIFE", "3")
    s = Settings()
    assert (s.suite_tier, s.hard_per_life) == ("both", 3)


@pytest.fixture(scope="module")
def hard_family(tmp_path_factory):
    import importlib
    import os

    os.environ["PROBATE_DATA_DIR"] = str(tmp_path_factory.mktemp("hard"))
    os.environ["PROBATE_SUITE_TIER"] = "both"
    from probate.common import config

    importlib.reload(config)
    from probate.courthouse.simulate import run

    try:
        yield run(3, datetime(2026, 11, 20, tzinfo=UTC), leave_last_alive=False)
    finally:
        os.environ.pop("PROBATE_SUITE_TIER", None)
        importlib.reload(config)


def test_simulation_with_both_tiers_runs_end_to_end(hard_family):
    from probate.courthouse import views

    store = hard_family
    rows = store.q("SELECT gen, fixture_id, outcome FROM suite_runs")
    hard_rows = [r for r in rows if r["fixture_id"].startswith("H")]
    assert len(hard_rows) == 3 * 4
    assert all(r["outcome"] for r in rows)
    for g in (1, 2, 3):
        assert {r["fixture_id"] for r in hard_rows if r["gen"] == g} == set(runner.hard_plan(g, 2))
    ev = views.evidence(store)
    shown = {r["id"]: r for r in ev["rows"]}
    some = next(r for r in hard_rows)["fixture_id"]
    assert some in shown and shown[some]["label"]
    assert ev["numbers"]["generations"] == 3
    # Summary and per-generation views still build with the extra fixtures.
    assert views.summary(store)
    assert views.generation(store, 1)
