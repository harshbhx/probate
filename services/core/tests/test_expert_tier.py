"""The opt-in expert attack tier (suite/expert.json, PROBATE_SUITE_TIER=expert)."""

import base64
import re
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from probate.suite import runner
from probate.suite.fixtures import LANGUAGE_NAMES, load, load_all, load_expert, load_hard, lookup

DOMAIN = re.compile(
    r"\b[\w-]+(?:\.[\w-]+)*\.(?:com|org|net|io|xyz|in|de|co|example)\b", re.IGNORECASE
)
REAL_ADDRESS = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")


def _cfg(tier="expert", expert=2, per_life=8, hard=2):
    return SimpleNamespace(
        suite_tier=tier,
        expert_per_life=expert,
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


def test_expert_fixtures_are_well_formed():
    expert = load_expert()
    attacks = [f for f in expert.values() if f.is_attack]
    harmless = [f for f in expert.values() if not f.is_attack]
    assert len(attacks) == 24 and len(harmless) == 12
    assert list(expert) == [f"E{i}" for i in range(1, 37)]
    assert [f.id for f in attacks] == [f"E{i}" for i in range(1, 25)]
    assert not set(expert) & (set(load()) | set(load_hard()))
    for f in expert.values():
        assert f.expert and f.body.strip() and f.subject.strip() and f.label
        assert f.language in LANGUAGE_NAMES, f.id
        assert f.sender_role in ("unknown_sender", "trusted_contact", "user")
        assert f.expected["verdict"] == ("convicted" if f.is_attack else "approved")
        texts = [f.body] + [a["content"] for a in f.attachments]
        for t in texts:
            assert all("example" in d.lower() for d in DOMAIN.findall(t)), f.id
            assert all(h.endswith(".example") for h in REAL_ADDRESS.findall(t)), f.id
        if f.language != "en":
            assert f.gloss, f"{f.id} needs an English gloss"
        if f.is_attack:
            assert f.expected["harm"] and f.expected["canary"] == f"PROBATE-CANARY-{f.id}"
        else:
            assert "canary" not in f.expected


def test_twins_are_paired_and_benign():
    expert = load_expert()
    uses = {}
    for f in expert.values():
        assert f.twin_id in expert, f.id
        other = expert[f.twin_id]
        assert other.is_attack != f.is_attack
        if f.is_attack:
            assert other.family != "" and f.sender_role == "unknown_sender"
            uses.setdefault(f.twin_id, []).append(f.id)
    # Every twin serves exactly two attacks of its own theme (same attachment kind or family).
    assert sorted(uses) == [f"E{i}" for i in range(25, 37)]
    assert all(len(v) == 2 for v in uses.values())
    for twin_id, ids in uses.items():
        assert expert[twin_id].twin_id == ids[0]
        assert not any(c in expert[twin_id].body for c in ("PROBATE-CANARY", "PR0B4T3"))


def test_ids_unique_and_payloads_inert():
    raw = [f.id for f in load_expert().values()]
    assert len(raw) == len(set(raw)) == 36
    for f in load_expert().values():
        for a in f.attachments:
            assert a["name"] and a["content"]
            assert not a["name"].endswith((".sh", ".exe", ".bat", ".js"))
        # Inert strings only: no shell hooks, scripts or URLs outside example domains.
        assert "<script" not in f.body.lower() and "crontab" not in f.body.lower()


def test_encoded_payloads_decode_to_inert_text():
    for fid in ("E6", "E18", "E30"):
        body = load_expert()[fid].body
        blob = re.search(r"\n> ([A-Za-z0-9+/=]{24,})", body).group(1)
        text = base64.b64decode(blob).decode()
        assert text.isascii() and ("CANARY" in text) == (fid != "E30")


def test_default_and_other_tiers_are_unchanged():
    expert_ids = set(load_expert())
    for tier in ("base", "hard", "both"):
        assert not expert_ids & set(load_all(tier))
    assert set(load_all("both")) == set(load_all("base")) | set(load_hard())
    assert set(load_all("expert")) == set(load_all("base")) | expert_ids
    assert expert_ids <= set(lookup())
    for tier in ("base", "both"):
        assert not any(i.startswith("E") for i in runner.planned(_cfg(tier), 3))
    assert runner.planned(_cfg("base"), 3) == runner.plan(3, 8)


def test_expert_plan_is_deterministic_and_rotation_covers_all_24_over_12_lives():
    assert runner.expert_plan(3, 2) == runner.expert_plan(3, 2)
    assert runner.expert_plan(1, 0) == []
    expert = load_expert()
    seen = set()
    for g in range(1, 13):
        p = runner.expert_plan(g, 2)
        assert len(set(p)) == len(p)
        attacks = [i for i in p if expert[i].is_attack]
        assert len(attacks) == 2
        for a in attacks:  # the matched twin is sent with its attack, and comes first
            assert expert[a].twin_id in p and p.index(expert[a].twin_id) < p.index(a)
        seen |= set(attacks)
    assert seen == {f"E{i}" for i in range(1, 25)}
    assert len(runner.expert_plan(500, 2)) == 4  # wraps, does not fail


def test_planned_expert_tier_is_expert_only_and_offset_shifts():
    ids = runner.planned(_cfg("expert"), 2)
    assert ids == runner.expert_plan(2, 2) and all(i.startswith("E") for i in ids)
    shifted = _cfg("expert")
    shifted.expert_offset = 1
    assert runner.planned(shifted, 3) == runner.expert_plan(2, 2)


def test_agentmail_sends_counts_every_expert_mail():
    for g in (1, 5, 12):
        ids = runner.planned(_cfg("expert"), g)
        assert runner.agentmail_sends(_cfg("expert"), g) == len(ids) == 4
    assert runner.agentmail_sends(_cfg("expert", expert=3), 1) == 6
    # Base accounting ignores the expert settings.
    assert runner.agentmail_sends(_cfg("base", expert=9), 1) == runner.agentmail_sends(
        _cfg("base"), 1
    )


def test_runner_sends_expert_mail_with_attachments():
    mail = _Mail()
    runner.send_all(mail, _cfg("expert", expert=3), 2, datetime(2026, 11, 20, tzinfo=UTC), 600)
    expert = load_expert()
    assert len(mail.sent) == 6
    for fid, subject, body in mail.sent:
        assert body == expert[fid].body and subject == expert[fid].subject


def test_settings_read_the_env(monkeypatch):
    from probate.common.config import Settings

    assert Settings().expert_per_life == 2 and Settings().suite_tier == "base"
    monkeypatch.setenv("PROBATE_SUITE_TIER", "Expert")
    monkeypatch.setenv("PROBATE_EXPERT_PER_LIFE", "3")
    s = Settings()
    assert (s.suite_tier, s.expert_per_life) == ("expert", 3)


@pytest.mark.parametrize("tier", ["base", "hard", "both"])
def test_other_tiers_send_no_expert_mail(tier):
    mail = _Mail()
    runner.send_all(mail, _cfg(tier), 1, datetime(2026, 11, 20, tzinfo=UTC), 600)
    assert not any(fid.startswith("E") for fid, _, _ in mail.sent)
