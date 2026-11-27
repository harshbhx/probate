"""What the real run's clock got wrong, fixed before the next run.

Generations 4 and 8 never got their test emails, 17 and 18 were born after AgentMail's daily
limit ran out, 18 clock errors said nothing about their cause, and owner decisions were
recorded twice.
"""

from datetime import UTC, datetime, timedelta

import pytest

from probate.adapters import world
from probate.common.config import Settings
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost
from probate.courthouse.mailquota import MailQuota
from probate.courthouse.scheduler import Scheduler, brief
from probate.courthouse.store import Store
from probate.suite import runner

T0 = datetime(2026, 11, 26, 16, tzinfo=UTC)


@pytest.fixture
def clock(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 60
    cfg.gap_seconds = 0
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    family = Family(cfg, store, w, LocalHost(cfg, w))
    return cfg, store, family, Scheduler(family)


class Flaky:
    """A mailbox that refuses the sends whose subject is in `refuse`."""

    def __init__(self, refuse: set[str]):
        self.refuse = refuse
        self.sent: list[str] = []

    def send(self, from_inbox, to, subject, text, **kw):
        if subject in self.refuse:
            raise RuntimeError("429 Too Many Requests: daily send limit reached")
        self.sent.append(subject)
        return f"m{len(self.sent)}"


def test_one_refused_email_does_not_stop_the_suite_and_a_retry_sends_only_the_rest(clock):
    cfg, store, family, _ = clock
    from probate.suite.fixtures import load_all

    family.birth(T0)
    fx = load_all("base")
    ids = runner.planned(cfg, 1)
    first = fx[ids[0]].subject
    box = Flaky({first})
    res = runner.send_all(box, cfg, 1, T0, 60, store)
    assert [f for f, _ in res.failed] == [ids[0]]
    assert len(res) == len(ids) - 1
    box.refuse = set()
    again = runner.send_all(box, cfg, 1, T0, 60, store)
    assert [f for f, _ in again] == [ids[0]] and not again.failed


def test_only_agentmail_sends_are_counted(clock):
    _cfg, store, *_ = clock

    class Routed:
        def __init__(self):
            self.routes = {"owner@own.example": object()}

        def send(self, from_inbox, *a, **k):
            return "id"

    q = MailQuota(store, limit=10, reserve=2)
    m = q.wrap(Routed())
    m.send("stranger@agentmail.to", "x", "s", "t")
    m.send("owner@own.example", "x", "s", "t")
    assert q.used() == 1 and q.left() == 9
    assert q.room_for(7) and not q.room_for(8)
    assert q.wrap(m) is m  # wrapping twice does not count twice


def test_the_suite_plan_counts_agentmail_sends(clock):
    cfg, *_ = clock
    n = runner.agentmail_sends(cfg, 1)
    assert 0 < n <= len(runner.planned(cfg, 1))


def test_no_birth_when_the_day_s_mail_is_used_up_then_birth_next_day(clock):
    _cfg, store, family, sched = clock
    family.quota.limit = 20
    family.quota.record(15, T0)
    assert sched.step(T0) == "resting:mail"
    assert sched.step(T0 + timedelta(seconds=15)) == "resting:mail"
    waits = [e for e in store.q("SELECT * FROM events") if e["kind"] == "resting"]
    assert len(waits) == 1 and "00:00 UTC" in waits[0]["text"]
    assert sched.step(T0 + timedelta(hours=9)).startswith("born:")


def test_a_life_born_without_its_suite_gets_it_on_the_next_tick(clock):
    _cfg, store, family, sched = clock
    g = family.birth(T0)  # born outside the clock: no test emails yet
    assert not store.q("SELECT 1 FROM suite_runs WHERE gen=?", g.gen)
    assert sched.step(T0 + timedelta(seconds=5)) == f"living:{g.gen}"
    sent = store.q("SELECT fixture_id FROM suite_runs WHERE gen=?", g.gen)
    assert len(sent) == len(runner.planned(family.cfg, g.gen))
    sched.step(T0 + timedelta(seconds=20))
    assert len(store.q("SELECT 1 FROM suite_runs WHERE gen=?", g.gen)) == len(sent)


def test_clock_errors_name_their_cause_without_leaking_tokens():
    exc = RuntimeError("401 Unauthorized for https://api.example/v1?token=abc\nsecond line")
    text = brief(exc)
    assert text.startswith("RuntimeError: 401 Unauthorized")
    assert "token=abc" not in text and "second line" not in text
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in brief(
        ValueError("key abcdefghijklmnopqrstuvwxyz0123456789 rejected")
    )


def test_an_owner_decision_is_recorded_once(clock):
    _cfg, store, family, _ = clock
    g = family.birth(T0)
    store.x(
        "INSERT INTO will_items(item_id,gen,created_at,category,text,source,source_ref,evidence) "
        "VALUES('it1',?,?,'fact','x','user','owner','')",
        g.gen,
        T0.isoformat(),
    )
    store.x(
        "INSERT INTO judgements(item_id,gen,verdict,reason) VALUES('it1',?,'contested','r')",
        g.gen,
    )
    assert family.decide("it1", "approve", by="admin")
    assert family.decide("it1", "approve", by="email")
    assert len([e for e in store.q("SELECT * FROM events") if e["kind"] == "decision"]) == 1


def test_asking_for_the_will_again_logs_it_once(clock):
    _cfg, _store, family, _ = clock
    g = family.birth(T0)
    family.host.will(g.sprite)
    family.host.will(g.sprite)
    lines = [r for r in family.host.life_log(g.sprite) if "into the will" in r["text"]]
    assert len(lines) == 1


def test_unread_test_mail_is_set_aside_before_the_next_birth(clock):
    cfg, store, family, sched = clock
    mail = family.w.mail
    mail.send(
        cfg.stranger_inbox, cfg.family_inbox, "Old trick", "x", headers={"X-Probate-Fixture": "A1"}
    )
    mail.send(cfg.friend_inbox, cfg.family_inbox, "Judge mail", "hello")
    assert sched.set_aside_stale_mail() == 1
    left = [m.subject for m in mail.list_new(cfg.family_inbox)]
    assert left == ["Judge mail"]
    assert store.q("SELECT 1 FROM events WHERE text LIKE 'Set aside 1 test emails%'")


def test_the_summary_says_the_family_waits_for_mail(clock):
    from probate.courthouse import views

    _cfg, store, family, sched = clock
    family.quota.limit = 10
    family.quota.record(10, T0)
    sched.step(T0)
    assert views.summary(store)["resting"] == "mail"
