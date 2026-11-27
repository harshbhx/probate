"""Operations and lifecycle fixes from the blue-team review: stray Sprites, hard-tier rotation by
ordinal, deploy guards, mark_read, a trial re-run, and the cheap minor findings."""

import importlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from probate.adapters import world
from probate.adapters.mail import RealMailbox
from probate.common.config import Settings, parse_flag
from probate.common.models import Mail
from probate.courthouse import family as family_mod
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost
from probate.courthouse.scheduler import Scheduler
from probate.courthouse.store import Store
from probate.suite import runner

T0 = datetime(2026, 11, 27, 9, tzinfo=UTC)
SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


@pytest.fixture
def fam(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 60
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    return store, Family(cfg, store, w, LocalHost(cfg, w)), cfg


def _script(name):
    sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module(name)


def _raise(exc):
    def f(*a, **k):
        raise exc

    return f


# --- M1: sprites left billing ---------------------------------------------------------------
def test_sweep_deletes_a_stray_and_never_the_living_or_foreign_names(fam):
    store, family, _ = fam
    sched = Scheduler(family)
    g = family.birth(T0)
    host = family.host
    stray, foreign = "gen-009-oldie", "my-other-sprite"
    host.list_sprites = lambda: [g.sprite, stray, foreign, "gen-xx-bad"]
    destroyed = []
    host.force_destroy = lambda n: destroyed.append(n) or {}
    assert sched.reconcile_sprites() == 1
    assert destroyed == [stray]  # not the living one, not a name that is not gen-NNN-*
    assert any(e["kind"] == "error" and stray in e["text"] for e in store.q("SELECT * FROM events"))


def test_sweep_keeps_going_when_one_delete_fails(fam):
    _, family, _ = fam
    sched = Scheduler(family)
    family.host.list_sprites = lambda: ["gen-001-a", "gen-002-b"]
    seen = []

    def destroy(n):
        seen.append(n)
        if n == "gen-001-a":
            raise RuntimeError("api down")
        return {}

    family.host.force_destroy = destroy
    assert sched.reconcile_sprites() == 1 and seen == ["gen-001-a", "gen-002-b"]


def test_step_runs_the_sweep_on_the_first_tick_then_only_now_and_then(fam):
    _, family, _ = fam
    sched = Scheduler(family)
    calls = []
    sched.reconcile_sprites = lambda: calls.append(1) or 0
    sched.step(T0)
    sched.step(T0 + timedelta(seconds=15))
    assert calls == [1]


def test_a_short_sprites_outage_does_not_close_the_death(fam):
    store, family, _ = fam
    g = family.birth(T0)
    family.host.destroy = _raise(RuntimeError("502"))
    for _ in range(family_mod.MAX_DEATH_ATTEMPTS + 3):  # far more than five ticks
        with pytest.raises(RuntimeError):
            family.death(store.generation(g.gen), T0 + timedelta(seconds=60))
    assert store.generation(g.gen).state == "dying"  # still open, so it is retried


def test_a_delete_that_never_works_is_closed_after_the_window(fam, monkeypatch):
    store, family, _ = fam
    g = family.birth(T0)
    family.host.destroy = _raise(RuntimeError("502"))
    monkeypatch.setattr(family_mod, "DEATH_GIVE_UP_SECONDS", 0)
    for _ in range(family_mod.MAX_DEATH_ATTEMPTS):
        try:
            family.death(store.generation(g.gen), T0 + timedelta(seconds=60))
        except RuntimeError:
            pass
    assert store.generation(g.gen).state == "dead"


def test_recover_orphans_keeps_the_row_open_when_the_delete_failed(fam):
    store, family, _ = fam
    g = family.birth(T0)
    row = store.generation(g.gen)
    row.state = "born"
    store.save_generation(row)
    family.host.force_destroy = _raise(RuntimeError("down"))
    assert Scheduler(family).recover_orphans() == 0
    assert store.generation(g.gen).state == "born"


# --- M3: hard-tier rotation by ordinal -------------------------------------------------------
def _cfg(**kw):
    base = {
        "suite_tier": "both",
        "hard_per_life": 2,
        "suite_per_life": 8,
        "hard_offset": 0,
        "read_links": False,
        "stranger_inbox": "s@x.example",
        "friend_inbox": "f@x.example",
        "owner_sender": "o@x.example",
        "family_inbox": "fam@x.example",
        "pages_base": "",
    }
    return SimpleNamespace(**{**base, **kw})


def test_ordinal_equals_the_number_when_no_birth_failed(fam):
    store, family, _ = fam
    for n in (1, 2, 3):
        g = family.birth(T0 + timedelta(minutes=n))
        assert runner.ordinal(store, g.gen) == g.gen
        assert runner.planned(_cfg(), g.gen, store) == runner.planned(_cfg(), g.gen)
        row = store.generation(g.gen)
        row.state = "tried"
        store.save_generation(row)


def test_a_failed_birth_does_not_shift_the_next_lifes_mix(fam):
    store, family, _ = fam
    g1 = family.birth(T0)
    row = store.generation(g1.gen)
    row.state = "tried"
    store.save_generation(row)
    real = family.host.birth
    family.host.birth = _raise(RuntimeError("no"))
    with pytest.raises(RuntimeError):
        family.birth(T0 + timedelta(minutes=5))  # gen 2 dies early
    family.host.birth = real
    g3 = family.birth(T0 + timedelta(minutes=10))
    assert g3.gen == 3 and runner.ordinal(store, 3) == 2
    # the life after the failure meets what generation 2 would have met
    assert runner.planned(_cfg(), 3, store) == runner.planned(_cfg(), 2)
    assert runner.agentmail_sends(_cfg(), 3, store) == runner.agentmail_sends(_cfg(), 2)


def test_the_next_birth_is_planned_with_its_future_ordinal(fam):
    store, _, _ = fam
    store.set_setting("birth_skipped", "1")
    assert runner.ordinal(store, 5) == 4  # not born yet
    assert runner.planned(_cfg(), 5, store) == runner.planned(_cfg(), 4)


# --- M4: deploy guards -----------------------------------------------------------------------
@pytest.mark.parametrize("raw", ["1", "true", "YES", "on", " On "])
def test_flag_true_values(raw):
    assert parse_flag("X", raw, False) is True


@pytest.mark.parametrize("raw", ["0", "false", "No", "off"])
def test_flag_false_values_turn_learning_off(raw):
    assert parse_flag("X", raw, True) is False


def test_flag_unknown_value_is_rejected_and_empty_is_the_default(monkeypatch):
    with pytest.raises(ValueError):
        parse_flag("PROBATE_DISTILL", "of", True)
    assert parse_flag("X", "", True) is True
    monkeypatch.setenv("PROBATE_DISTILL", "false")
    assert Settings(fake=True).distill is False
    monkeypatch.setenv("PROBATE_DISTILL", "maybe")
    with pytest.raises(ValueError):
        Settings(fake=True)
    monkeypatch.delenv("PROBATE_DISTILL")
    monkeypatch.setenv("PROBATE_CONTEST_EMAILS", "off")
    assert Settings(fake=True).contest_emails is False


def test_deploy_refuses_unknown_flag_values():
    envs = _script("envs")
    assert envs.bad_flags({"PROBATE_DISTILL": "disabled"})
    assert envs.bad_flags({"PROBATE_CONTEST_EMAILS": "'nope'"})
    assert envs.bad_flags({"PROBATE_DISTILL": "false", "PROBATE_CONTEST_EMAILS": "0"}) == []


def test_only_a_404_means_no_database():
    from probate.adapters.sprites import SpritesAPI

    api = SpritesAPI("t", base="https://sprites.test")
    for status, expect in ((200, True), (404, False)):
        api.http = httpx.Client(
            transport=httpx.MockTransport(lambda r, s=status: httpx.Response(s))
        )
        assert api.file_exists("c", "data/probate.db") is expect
    api.http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(httpx.HTTPStatusError):  # a busy Courthouse is not "no database"
        api.file_exists("c", "data/probate.db")


def test_deploy_refuses_a_sprite_running_another_environment_or_branch():
    envs = _script("envs")
    live = {"environment": "production-v2", "branch": "v2-main"}
    assert envs.replaces_other_run(live, "judges-demo", "")
    assert envs.replaces_other_run(live, None, "")  # no --env onto a named run
    assert envs.replaces_other_run(live, "production-v2", "v2-b")
    assert envs.replaces_other_run(live, "judges-demo", "", force=True) is None
    assert envs.replaces_other_run(live, "production-v2", "v2-main") is None
    assert envs.replaces_other_run(live, "production-v2", "") is None  # renamed at run time
    assert envs.replaces_other_run(None, "production-v2", "x") is None


def test_deploy_lists_knobs_that_differ_from_the_running_sprite():
    envs = _script("envs")
    running = {"distill": False, "hard_offset": 26, "suite_tier": "hard", "lifespan_seconds": 600}
    text = "\n".join(envs.differing_knobs(running, {"PROBATE_SUITE_TIER": "hard"}))
    assert "PROBATE_DISTILL" in text and "PROBATE_HARD_OFFSET" in text
    assert "PROBATE_SUITE_TIER" not in text and "LIFESPAN" not in text
    same = {"PROBATE_DISTILL": "0", "PROBATE_HARD_OFFSET": "26", "PROBATE_SUITE_TIER": "hard"}
    assert envs.differing_knobs(running, same) == []


def test_deploy_stops_the_service_before_removing_the_app_dir():
    src = (SCRIPTS / "deploy.py").read_text(encoding="utf-8")
    assert src.index('"courthouse", "stop"') < src.index("rm -rf app &&")


# --- M5: mark_read ---------------------------------------------------------------------------
def _box(statuses):
    box = RealMailbox("https://mail.test")
    calls = []

    def handler(req):
        calls.append(req.method)
        return httpx.Response(statuses[min(len(calls), len(statuses)) - 1])

    box.http = httpx.Client(transport=httpx.MockTransport(handler))
    return box, calls


def test_mark_read_retries_a_failed_label_and_reports_success(monkeypatch):
    monkeypatch.setattr("probate.adapters.mail.time.sleep", lambda s: None)
    box, calls = _box([500, 200])
    assert box.mark_read("i", "m1") is True and len(calls) == 2 and "m1" in box.read


def test_mark_read_reports_a_label_that_never_stuck(monkeypatch):
    monkeypatch.setattr("probate.adapters.mail.time.sleep", lambda s: None)
    box, calls = _box([503])
    assert box.mark_read("i", "m1") is False and len(calls) == 3
    assert "m1" not in box.read  # so it shows up again, not hidden


class _StuckMail:
    """list_new keeps returning the test mail because the label never sticks."""

    def __init__(self):
        self.m = Mail(
            id="m1",
            inbox="fam",
            sender="a@x",
            subject="s",
            text="t",
            received_at=T0,
            headers={"X-Probate-Fixture": "A1"},
        )

    def list_new(self, inbox):
        return [self.m]

    def mark_read(self, inbox, mid):
        return False


def test_set_aside_reports_mail_that_is_still_unlabeled(fam):
    store, family, _ = fam
    family.w.mail = _StuckMail()
    assert Scheduler(family).set_aside_stale_mail() == 0
    assert any("could not be marked read" in e["text"] for e in store.q("SELECT * FROM events"))


# --- M6: trial re-run ------------------------------------------------------------------------
def test_a_trial_rerun_keeps_the_instinct_it_already_learned(fam):
    store, family, cfg = fam
    g = family.birth(T0)
    runner.send_all(family.w.mail, cfg, g.gen, T0, 60, store)
    family.host.tick(g.sprite)
    g = family.death(g, T0 + timedelta(seconds=58))
    family.trial(g)
    first = [i.name for i in store.genome() if i.added_in_gen == g.gen + 1]
    assert first
    row = store.generation(g.gen)
    row.state = "dead"  # the process died before 'tried' was saved
    store.save_generation(row)
    calls = []
    real = family_mod.distill
    family_mod.distill = lambda **k: calls.append(1) or real(**k)
    try:
        family.trial(store.generation(g.gen))
    finally:
        family_mod.distill = real
    assert calls == []  # not asked again
    assert [i.name for i in store.genome() if i.added_in_gen == g.gen + 1] == first
    rows = store.q("SELECT new_instinct FROM judgements WHERE new_instinct IS NOT NULL")
    assert rows and {r["new_instinct"] for r in rows} <= set(first)  # the link is kept


# --- minors ----------------------------------------------------------------------------------
def test_death_rerun_does_not_charge_the_life_twice(fam):
    store, family, _ = fam
    g = family.birth(T0)
    family.host.tick(g.sprite)
    family.death(g, T0 + timedelta(seconds=58))
    spent = family.budget.spent()
    row = store.generation(g.gen)
    row.state = "dying"
    store.save_generation(row)
    family.death(store.generation(g.gen), T0 + timedelta(seconds=90))
    assert family.budget.spent() == spent


def test_sent_at_is_when_the_mail_went_out_not_the_plan(fam):
    store, family, cfg = fam
    g = family.birth(T0)
    before = datetime.now(UTC)
    runner.send_all(family.w.mail, cfg, g.gen, T0, 600, store)
    rows = store.q("SELECT sent_at FROM suite_runs WHERE gen=?", g.gen)
    assert rows
    for r in rows:
        assert datetime.fromisoformat(r["sent_at"]) >= before


def test_a_crash_between_send_and_record_does_not_send_the_fixture_twice(fam):
    store, family, cfg = fam
    g = family.birth(T0)
    mail = family.w.mail
    first = runner.planned(cfg, g.gen, store)[0]
    real_x = store.x
    state = {"boom": True}

    def crash_on_record(sql, *a):
        if state["boom"] and sql.startswith("INSERT OR REPLACE") and a[-2] is not None:
            state["boom"] = False
            raise RuntimeError("process died")
        return real_x(sql, *a)

    store.x = crash_on_record
    with pytest.raises(RuntimeError):
        runner.send_all(mail, cfg, g.gen, T0, 60, store)
    store.x = real_x
    runner.send_all(mail, cfg, g.gen, T0, 60, store)
    sent = [m for m in mail.all(cfg.family_inbox) if m.headers.get("X-Probate-Fixture") == first]
    assert len(sent) == 1
    row = store.one("SELECT message_id FROM suite_runs WHERE gen=? AND fixture_id=?", g.gen, first)
    assert row["message_id"] == sent[0].id


def test_a_suite_with_no_matching_ids_raises_an_error_event(fam):
    store, family, cfg = fam
    g = family.birth(T0)
    runner.send_all(family.w.mail, cfg, g.gen, T0, 60, store)
    family._score(g, [], [], {"handled": {"other-id": {}}}, {})
    assert any("none has the id" in e["text"] for e in store.q("SELECT * FROM events"))


def test_a_retried_mail_is_counted_once(fam):
    _store, family, _cfg = fam
    g = family.birth(T0)
    agent = family.host._agent(g.sprite)
    real = agent.w.llm

    class Flaky:
        n = 0

        def complete(self, *a, **k):
            Flaky.n += 1
            if Flaky.n == 1:
                raise RuntimeError("model timed out")
            return real.complete(*a, **k)

        def __getattr__(self, name):
            return getattr(real, name)

    agent.w.llm = Flaky()
    agent.w.mail.send("x@example.com", agent.inh.family_inbox, "Lunch", "Noon tomorrow?")
    assert agent.tick() == 0  # fails once, will be retried
    assert agent.tick() == 1
    assert agent.stats["emails"] == 1
