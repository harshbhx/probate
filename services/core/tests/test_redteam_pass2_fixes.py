"""Second red-team pass (tracking issues 234, 235, 236): bundle allowlist, lockouts that spare the
right secret, the /ask caps, and Sprite names that carry no environment."""

import io
import tarfile
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from test_judge import ADMIN, KEY, load

from probate.adapters import world
from probate.adapters.sprites import ForeignSprite, SpriteExists
from probate.common.bundle import make_bundle
from probate.common.config import Settings
from probate.courthouse.family import Family
from probate.courthouse.hosts import LocalHost, SpritesHost
from probate.courthouse.scheduler import Scheduler
from probate.courthouse.store import Store

T0 = datetime(2026, 11, 27, 9, tzinfo=UTC)

# ----------------------------------------------------------------------------- bundle allowlist
DECOYS = [
    "prod.env", "config.env", "token.txt", "api_key.txt", "service-account.json", "gcloud.json",
    "firebase-adminsdk.json", ".npmrc", ".pypirc", "kubeconfig", "aws_credentials",
    "terraform.tfstate", "dump.sql", "backup.tar.gz", "probate.db-wal", "probate.db-shm",
    "x.sqlite-journal", "run.log.1", "app.log.2025", ".env", "id_rsa", "notes.txt~", "key.pem",
]  # fmt: skip


def _names(data):
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        return tar.getnames()


def _tree(tmp_path):
    root = tmp_path / "repo"
    core = root / "services" / "core"
    (core / "probate" / "prompts").mkdir(parents=True)
    (core / "probate" / "courthouse").mkdir()
    (core / "probate" / "suite").mkdir()
    (core / "probate" / "__init__.py").write_text("", encoding="utf-8")
    (core / "probate" / "prompts" / "brain_system.md").write_text("p", encoding="utf-8")
    (core / "probate" / "courthouse" / "schema.sql").write_text("select 1;", encoding="utf-8")
    (core / "probate" / "suite" / "suite-v1.json").write_text("{}", encoding="utf-8")
    (core / "pyproject.toml").write_text("[project]", encoding="utf-8")
    (root / "config").mkdir()
    (root / "config" / "names.yaml").write_text("names: []", encoding="utf-8")
    (root / "config" / "owner.yaml").write_text("owner: {}", encoding="utf-8")
    dist = root / "apps" / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    for place in (core, core / "probate", core / "probate" / "prompts", root / "config", dist):
        for name in DECOYS:
            (place / name).write_text("SECRET", encoding="utf-8")
    return root


@pytest.mark.parametrize("kw", [{}, {"web": True}, {"redact_owner": True}])
def test_bundle_ships_only_the_allowlist(tmp_path, kw):
    names = _names(make_bundle(_tree(tmp_path), **kw))
    for bad in DECOYS:
        assert not any(n.endswith("/" + bad) for n in names), bad
    for good in (
        "services/core/pyproject.toml",
        "services/core/probate/__init__.py",
        "services/core/probate/prompts/brain_system.md",
        "services/core/probate/courthouse/schema.sql",
        "services/core/probate/suite/suite-v1.json",
        "config/names.yaml",
        "config/owner.yaml",
    ):
        assert good in names


def test_the_real_bundle_still_carries_what_a_generation_needs():
    names = _names(make_bundle(redact_owner=True))
    for need in (
        "services/core/pyproject.toml",
        "services/core/probate/generation/cli.py",
        "services/core/probate/courthouse/schema.sql",
        "services/core/probate/prompts/brain_system.md",
        "services/core/probate/suite/suite-v1.json",
        "config/names.yaml",
        "config/owner.yaml",
    ):
        assert need in names, need


# ----------------------------------------------------------------------------- lockouts
def test_judge_right_key_is_never_refused_after_wrong_ones(tmp_path, monkeypatch):
    m = load(
        tmp_path,
        monkeypatch,
        PROBATE_JUDGE_BAD_KEYS_PER_IP="2",
        PROBATE_JUDGE_BAD_KEYS_GLOBAL="4",
    )
    c = TestClient(m.app, headers={"x-forwarded-for": "7.7.7.7"})
    for i in range(6):
        c.get("/api/judge/status", headers={"X-Probate-Key": f"wrong-{i}-" + "x" * 20})
    assert c.get("/api/judge/status", headers={"X-Probate-Key": KEY}).status_code == 200
    rotating = TestClient(m.app)
    for i in range(8):
        r = rotating.get(
            "/api/judge/status",
            headers={"X-Probate-Key": f"w{i}-" + "y" * 20, "x-forwarded-for": f"5.5.5.{i}"},
        )
    assert r.status_code == 429  # a flood of wrong keys is refused ...
    ok = rotating.get(
        "/api/judge/status", headers={"X-Probate-Key": KEY, "x-forwarded-for": "5.5.5.99"}
    )
    assert ok.status_code == 200  # ... the right key still is not


def test_admin_right_token_is_never_refused_and_a_global_counter_exists(tmp_path, monkeypatch):
    m = load(
        tmp_path,
        monkeypatch,
        PROBATE_ADMIN_BAD_TOKENS_PER_IP="3",
        PROBATE_ADMIN_BAD_TOKENS_GLOBAL="6",
    )
    c = TestClient(m.app)
    codes = []
    for i in range(10):  # rotating addresses: only the global counter can stop this
        h = {"X-Probate-Admin": f"nope-{i}", "x-forwarded-for": f"9.9.9.{i}"}
        codes.append(c.post("/admin/pause", headers=h).status_code)
    assert codes[:6] == [403] * 6 and codes[6:] == [429] * 4
    right = {"X-Probate-Admin": ADMIN, "x-forwarded-for": "9.9.9.1"}
    assert c.post("/admin/pause", headers=right).status_code == 200


def test_wrong_secret_waits_and_the_right_one_does_not(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_WRONG_SECRET_DELAY="0.2")
    c = TestClient(m.app)
    t = time.perf_counter()
    c.post("/admin/pause", headers={"X-Probate-Admin": "nope"})
    assert time.perf_counter() - t >= 0.2
    t = time.perf_counter()
    c.post("/admin/pause", headers={"X-Probate-Admin": ADMIN})
    assert time.perf_counter() - t < 0.2


# ----------------------------------------------------------------------------- /ask caps
def _dead(m, monkeypatch):
    monkeypatch.setattr(m.store, "generation", lambda g: SimpleNamespace(state="dead"))
    monkeypatch.setattr(m.ancestor, "ask", lambda *a, **k: {"answer": "ok"})


def _ask(c, ip, question="q", gen=1):
    return c.post(
        f"/api/generations/{gen}/ask", json={"question": question}, headers={"x-forwarded-for": ip}
    ).status_code


def test_bad_asks_do_not_use_up_the_daily_cap(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_ASK_DAILY_CAP="3")
    c = TestClient(m.app)
    assert [_ask(c, f"2.2.2.{i}", gen=9999) for i in range(10)] == [400] * 10
    _dead(m, monkeypatch)
    assert [_ask(c, f"2.2.3.{i}", question="  ") for i in range(10)] == [400] * 10
    assert _ask(c, "2.2.4.1") == 200


def test_one_address_cannot_burn_the_global_ask_cap(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_ASK_DAILY_CAP="5", PROBATE_ASK_DAILY_PER_IP="2")
    _dead(m, monkeypatch)
    c = TestClient(m.app)
    assert [_ask(c, "3.3.3.3") for _ in range(5)] == [200, 200, 429, 429, 429]
    assert _ask(c, "3.3.3.4") == 200  # an honest judge still has room under the global cap


def test_the_global_ask_cap_still_holds(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_ASK_DAILY_CAP="2", PROBATE_ASK_DAILY_PER_IP="5")
    _dead(m, monkeypatch)
    c = TestClient(m.app)
    assert [_ask(c, f"4.4.4.{i}") for i in range(4)] == [200, 200, 429, 429]


# ----------------------------------------------------------------------------- Sprite names
class _Api:
    def __init__(self, exists):
        self.exists, self.deleted, self.written = exists, [], []

    def create(self, sprite, adopt=True):
        if self.exists and not adopt:
            raise SpriteExists(sprite)

    def write_file(self, *a, **k):
        self.written.append(a)
        raise RuntimeError("must not be reached for a foreign Sprite")

    def delete(self, sprite):
        self.deleted.append(sprite)


def _host(exists, owns):
    host = SpritesHost.__new__(SpritesHost)
    host.api, host.owns = _Api(exists), owns
    return host


def test_birth_fails_when_the_name_belongs_to_another_environment():
    host = _host(True, lambda name: False)
    with pytest.raises(ForeignSprite, match="docs/13-RUNBOOK.md"):
        host.birth("gen-003-chandra", None)
    assert host.api.written == [] and host.api.deleted == []  # nothing installed, nothing deleted


def test_birth_fails_when_no_ownership_check_is_wired():
    host = _host(True, None)
    with pytest.raises(ForeignSprite):
        host.birth("gen-003-chandra", None)


def test_birth_of_a_free_name_still_proceeds():
    host = _host(False, lambda name: False)
    with pytest.raises(RuntimeError, match="must not be reached"):  # past create, into the install
        host.birth("gen-003-chandra", None)
    assert host.api.deleted == ["gen-003-chandra"]  # our own half-born Sprite is cleaned up


def test_a_refused_birth_never_deletes_or_sweeps_the_foreign_sprite(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    cfg = Settings(fake=True)
    cfg.lifespan_seconds = 60
    w = world(cfg, fresh=True)
    store = Store(cfg.db_path)
    family = Family(cfg, store, w, LocalHost(cfg, w))
    destroyed = []
    family.host.force_destroy = lambda n: destroyed.append(n) or {}

    def refuse(*a, **k):
        raise ForeignSprite("taken")

    family.host.birth = refuse
    with pytest.raises(ForeignSprite):
        family.birth(T0)
    name = store.generation(1).sprite
    assert destroyed == [] and store.generation(1).state == "died_early"
    family.host.list_sprites = lambda: [name]
    assert Scheduler(family).reconcile_sprites() == 0
    assert destroyed == []


# ----------------------------------------------------------------------------- verdict range
def test_out_of_range_answers_are_not_an_approval():
    from probate.common.models import JevAnswer, MemoryItem, Source, Verdict
    from probate.court.verdict import decide

    item = MemoryItem(
        id="i",
        gen=1,
        created_at="2026-01-01T00:00:00Z",
        category="fact",
        text="Harsh likes tea.",
        source=Source.USER,
        source_ref="m",
    )
    names = [
        "untrusted_origin",
        "imperative_to_future_self",
        "weakens_security",
        "exfiltrates_data",
    ]

    def full(value):
        got = {n: JevAnswer(value=value, confidence=0.95) for n in [*names, "risk"]}
        return decide(item, [], got, [])

    assert full(0.01).verdict == Verdict.APPROVED
    for bad in (-1, -0.5):
        assert full(bad).verdict == Verdict.CONTESTED, bad
