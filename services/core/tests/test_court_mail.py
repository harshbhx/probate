"""Harsh decides held items by replying to the court's email."""

from datetime import UTC, datetime

import pytest

from probate.adapters import world
from probate.common import court_mail
from probate.common.config import Settings
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost
from probate.courthouse.store import Store


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("Approve", "approve"),
        ("yes, keep it", "approve"),
        ("refuse", "refuse"),
        (
            "No.\n\nOn Tue, 24 Nov 2026 Probate wrote:\n> Reply with one word: approve or refuse.",
            "refuse",
        ),
        ("ok\n> approve or refuse", "approve"),
        ("approve or refuse?", None),
        ("what is this?", None),
        ("", None),
    ],
)
def test_reads_only_harshs_own_words(text, want):
    assert court_mail.decision(text) == want


def test_subject_round_trip():
    s = court_mail.subject("mem_gen003_0007")
    assert court_mail.item_of("Re: " + s) == "mem_gen003_0007"
    assert not court_mail.is_court_mail("Re: lunch on Friday?")


@pytest.fixture
def family(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 3600
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    fam = Family(cfg, store, w, LocalHost(cfg, w))
    fam.live_fast(datetime(2026, 11, 20, 9, tzinfo=UTC))
    row = store.one("SELECT item_id FROM judgements WHERE verdict='approved' LIMIT 1")
    store.x("UPDATE judgements SET verdict='contested' WHERE item_id=?", row["item_id"])
    return fam, row["item_id"]


def _reply(fam, item_id, sender, text):
    fam.w.mail.send(sender, fam.cfg.family_inbox, "Re: " + court_mail.subject(item_id), text)


def _decision(fam, item_id):
    return fam.store.one("SELECT owner_decision FROM judgements WHERE item_id=?", item_id)[
        "owner_decision"
    ]


def test_harshs_reply_approves_and_the_item_is_inherited(family):
    fam, item = family
    assert item not in {i.id for i in fam.inheritance_items()}
    _reply(fam, item, fam.owner_email, "approve\n\n> Reply with one word: approve or refuse.")
    assert fam.read_court_replies() == 1
    assert _decision(fam, item) == "approve"
    assert item in {i.id for i in fam.inheritance_items()}
    assert fam.read_court_replies() == 0  # handled once


def test_a_stranger_cannot_decide(family):
    fam, item = family
    _reply(fam, item, "probate-stranger@agentmail.example", "approve")
    assert fam.read_court_replies() == 0
    assert _decision(fam, item) is None


def test_the_living_generation_leaves_court_mail_alone(family):
    fam, item = family
    g = fam.birth(datetime(2026, 11, 21, 9, tzinfo=UTC))
    _reply(fam, item, fam.owner_email, "refuse")
    fam.host.tick(g.sprite)  # the generation reads its inbox
    assert fam.read_court_replies() == 1
    assert _decision(fam, item) == "refuse"
