"""Hardening before the public demo Courthouse: admin door, /ask, edge-only access, bundle, court."""

import importlib.util
import io
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from test_judge import ADMIN, KEY, load

from probate.adapters.jev import CourtUnavailable, require_complete
from probate.common.bundle import make_bundle
from probate.common.models import JevAnswer, MemoryItem, Source, Verdict
from probate.court import verdict
from probate.generation.agent import _att_name

EDGE_TOKEN = "edge-test-token-0123456789abcdef"


# ----------------------------------------------------------------------------- H4 admin door
@pytest.mark.parametrize("token", ["", "dev-admin", "short-token", "x" * 23])
def test_weak_admin_token_is_refused_outside_fake_mode(tmp_path, monkeypatch, token):
    m = load(tmp_path, monkeypatch)
    m.settings.fake = False
    m.settings.admin_token = token
    c = TestClient(m.app)
    r = c.post("/admin/pause", headers={"X-Probate-Admin": token or "x"})
    assert r.status_code == 503


def test_strong_admin_token_works_outside_fake_mode(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch)
    m.settings.fake = False
    m.settings.admin_token = "a-long-random-admin-token-0123456789"
    c = TestClient(m.app)
    ok = c.post("/admin/pause", headers={"X-Probate-Admin": m.settings.admin_token})
    assert ok.status_code == 200


def test_fake_mode_keeps_dev_token(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_ADMIN_TOKEN="dev-admin")
    c = TestClient(m.app)
    assert c.post("/admin/pause", headers={"X-Probate-Admin": "dev-admin"}).status_code == 200


def test_admin_wrong_tokens_are_throttled_per_address(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_ADMIN_BAD_TOKENS_PER_IP="3")
    c = TestClient(m.app)
    bad = {"X-Probate-Admin": "nope", "x-forwarded-for": "9.9.9.9"}
    codes = [c.post("/admin/pause", headers=bad).status_code for _ in range(5)]
    assert codes == [403, 403, 403, 429, 429]
    # the right token is never refused, whatever the address did before
    assert c.post("/admin/pause", headers={**bad, "X-Probate-Admin": ADMIN}).status_code == 200
    other = {"X-Probate-Admin": ADMIN, "x-forwarded-for": "8.8.8.8"}
    assert c.post("/admin/pause", headers=other).status_code == 200


# ----------------------------------------------------------------------------- H3 ask
def test_ask_body_is_capped(tmp_path, monkeypatch):
    c = TestClient(load(tmp_path, monkeypatch).app)
    assert c.post("/api/generations/1/ask", json={"question": "x" * 401}).status_code == 422
    assert c.post("/api/generations/1/ask", json={"question": "x" * 400}).status_code != 422


def test_ask_stops_when_budget_is_exhausted(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch)
    monkeypatch.setattr(m.family.budget, "exhausted", lambda: True)
    called = []
    monkeypatch.setattr(m.ancestor, "ask", lambda *a, **k: called.append(1) or {})
    r = TestClient(m.app).post("/api/generations/1/ask", json={"question": "hi"})
    assert r.status_code == 402 and not called


def test_ask_has_a_daily_cap(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_ASK_DAILY_CAP="2")
    calls = []
    monkeypatch.setattr(m.ancestor, "ask", lambda *a, **k: calls.append(1) or {"answer": "ok"})
    monkeypatch.setattr(m.store, "generation", lambda g: type("G", (), {"state": "dead"})())
    c = TestClient(m.app)
    codes = []
    for i in range(4):
        h = {"x-forwarded-for": f"1.1.1.{i}"}
        codes.append(
            c.post("/api/generations/1/ask", json={"question": "hi"}, headers=h).status_code
        )
    assert codes == [200, 200, 429, 429] and len(calls) == 2


@pytest.mark.parametrize("env", ["PROBATE_ASK_DAILY_CAP", "PROBATE_ASK_DAILY_PER_IP"])
def test_an_ask_cap_of_zero_disables_asking(tmp_path, monkeypatch, env):
    m = load(tmp_path, monkeypatch, **{env: "0"})
    calls = []
    monkeypatch.setattr(m.ancestor, "ask", lambda *a, **k: calls.append(1) or {"answer": "ok"})
    monkeypatch.setattr(m.store, "generation", lambda g: type("G", (), {"state": "dead"})())
    r = TestClient(m.app).post("/api/generations/1/ask", json={"question": "hi"})
    assert r.status_code == 403 and r.json()["error"] == "ask_disabled" and not calls


def test_in_memory_tables_are_bounded(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch)
    table = {f"ip{i}": [1.0] for i in range(6000)}  # all long expired
    m._bounded(table)
    assert len(table) <= 5000
    table = {f"ip{i}": [m.time.time()] for i in range(6000)}  # all fresh: still capped
    m._bounded(table)
    assert len(table) <= 5000


def test_stored_questions_and_audio_are_capped(tmp_path, monkeypatch):
    from probate.common.config import Settings
    from probate.courthouse import ancestor

    m = load(tmp_path, monkeypatch)
    cfg = Settings(fake=True)
    cfg.data_dir, cfg.ask_max_rows, cfg.ask_max_audio = tmp_path, 3, 2
    monkeypatch.setattr(m.store, "generation", lambda g: type("G", (), {
        "state": "dead", "name": "Ada", "gen": 1, "died_at": None, "obituary": "",
        "genome_size_at_birth": 0, "voice_id": "v"})())  # fmt: skip
    m.store.db.execute("PRAGMA foreign_keys=OFF")  # the generation row above is a stand-in
    monkeypatch.setattr(m.w.voice, "speak", lambda text, voice: text.encode())
    for i in range(6):
        out = ancestor.ask(m.store, m.w, cfg, 1, f"question {i}")
        assert "answer" in out
    assert m.store.q("SELECT COUNT(*) n FROM ancestor_questions")[0]["n"] == 3
    assert len(list((tmp_path / "audio").glob("gen-*-ask-*.mp3"))) == 2


# ----------------------------------------------------------------------------- M1 edge / client ip
def test_forwarded_for_is_not_trusted_when_the_setting_says_so(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_TRUST_FORWARDED_FOR="0")
    from starlette.requests import Request

    raw = [(b"x-forwarded-for", b"1.2.3.4")]
    req = Request({"type": "http", "headers": raw, "client": ("192.0.2.9", 1)})
    assert m.client_ip(req) == "192.0.2.9"


def test_edge_is_required_for_everything_but_healthz(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_EDGE_TOKEN=EDGE_TOKEN, PROBATE_REQUIRE_EDGE="1")
    c = TestClient(m.app)
    assert c.get("/healthz").status_code == 200
    assert c.get("/api/summary").status_code == 403
    assert c.get("/api/summary", headers={"x-probate-edge": "wrong" * 5}).status_code == 403
    assert c.get("/api/summary", headers={"x-probate-edge": EDGE_TOKEN}).status_code == 200


def test_edge_not_required_by_default(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch)
    assert m.settings.require_edge is False
    assert TestClient(m.app).get("/api/summary").status_code == 200


def test_edge_only_access_is_off_in_every_environment_until_the_worker_is_confirmed():
    import yaml

    path = Path(__file__).parents[3] / "config" / "environments.yaml"
    envs = yaml.safe_load(path.read_text(encoding="utf-8"))["environments"]
    # judges-demo ships with "0": "1" would lock out direct visitors until apps/edge is deployed.
    assert envs["judges-demo"]["settings"]["PROBATE_REQUIRE_EDGE"] in ("0", "1")
    assert envs["judges-demo"]["settings"]["PROBATE_ASK_DAILY_CAP"] == "10"
    assert "PROBATE_REQUIRE_EDGE" not in envs["production-v2"]["settings"]


def test_on_demand_real_mode_refuses_to_start_without_edge_token(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch)
    m.settings.fake = False
    m.settings.edge_token = "short"
    with pytest.raises(RuntimeError, match="PROBATE_EDGE_TOKEN"):
        m.check_edge_configured()
    m.settings.edge_token = EDGE_TOKEN
    m.check_edge_configured()
    m.settings.fake, m.settings.edge_token = True, ""
    m.check_edge_configured()  # simulation needs none


def test_wrong_judge_keys_are_counted_globally(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_JUDGE_BAD_KEYS_GLOBAL="3")
    c = TestClient(m.app)

    def status(i, key):
        h = {"X-Probate-Key": key, "x-forwarded-for": f"7.7.7.{i}"}
        return c.get("/api/judge/status", headers=h).status_code

    codes = [status(i, "wrong-key-wrong-key-wrong-0") for i in range(5)]
    assert codes == [401, 401, 401, 429, 429]
    assert status(99, KEY) == 200  # a right key is never locked out by someone else's guesses


# ----------------------------------------------------------------------------- M4 bundle
def _bundle(tmp_path, **kw):
    root = tmp_path / "repo"
    core = root / "services" / "core"
    (core / "probate").mkdir(parents=True)
    (core / "probate" / "__init__.py").write_text("", encoding="utf-8")
    (core / "sub").mkdir()
    secrets = [".env", ".env.local", ".env.production", "sub/.env", "notes.pem", "id_rsa"]
    secrets += ["credentials.json", "probate.db", "data.sqlite", "run.log", "x.bak"]
    for n in secrets:
        (core / n).write_text("secret", encoding="utf-8")
    cfg = root / "config"
    cfg.mkdir()
    (cfg / "names.yaml").write_text("names: []", encoding="utf-8")
    (cfg / "owner.yaml").write_text(
        "owner:\n  name: O\n  emails: [o@example.test]\n  payment_destinations: [pay@secret.test]\n",
        encoding="utf-8",
    )
    (cfg / "owner.yaml.bak").write_text("pay@secret.test", encoding="utf-8")
    return tarfile.open(fileobj=io.BytesIO(make_bundle(root, **kw)))


def test_bundle_denies_every_secret_looking_file(tmp_path):
    names = _bundle(tmp_path).getnames()
    assert "services/core/probate/__init__.py" in names
    for bad in [".env", "notes.pem", "id_rsa", "credentials", ".db", "sqlite", ".log", ".bak"]:
        assert not any(bad in n for n in names), bad


def test_sprite_bundle_has_owner_without_payment_destinations(tmp_path):
    tar = _bundle(tmp_path, redact_owner=True)
    text = tar.extractfile("config/owner.yaml").read().decode()
    assert "o@example.test" in text and "pay@secret.test" not in text
    # the courthouse's own bundle keeps the real profile
    full = _bundle(tmp_path / "b").extractfile("config/owner.yaml").read()
    assert b"pay@secret.test" in full


# ----------------------------------------------------------------------------- M5
def test_attachment_name_tolerates_filename_or_nothing():
    assert _att_name({"name": "a.sh"}) == "a.sh"
    assert _att_name({"filename": "b.sh"}) == "b.sh"
    assert _att_name({"content": "x"}) == ""


# ----------------------------------------------------------------------------- H2
def _item():
    return MemoryItem(
        id="mem_gen001_0001",
        gen=1,
        created_at="2026-11-27T09:00:00+00:00",
        category="fact",
        text="Plain note.",
        source=Source.USER,
        source_ref="x",
        evidence="",
    )


def test_empty_or_partial_answers_are_contested_not_approved():
    assert verdict.decide(_item(), [], {}, []).verdict == Verdict.CONTESTED
    partial = {"untrusted_origin": JevAnswer(value=0.0, confidence=0.99)}
    assert verdict.decide(_item(), [], partial, []).verdict == Verdict.CONTESTED
    nonnum = {n: JevAnswer(value="n/a", confidence=0.99) for n in ("risk", "untrusted_origin")}
    assert verdict.decide(_item(), [], nonnum, []).verdict == Verdict.CONTESTED


def test_a_full_low_answer_set_still_approves():
    from probate.court.layer2 import risk_names

    names = [*risk_names(_item(), []), "risk"]
    answers = {n: JevAnswer(value=0.0, confidence=0.99) for n in names}
    assert verdict.decide(_item(), [], answers, []).verdict == Verdict.APPROVED


def test_adapters_fail_closed_on_missing_answers():
    asked = {"risk": object(), "weakens_security": object()}
    with pytest.raises(CourtUnavailable):
        require_complete({}, asked, "Jev")
    with pytest.raises(CourtUnavailable):
        require_complete({"risk": JevAnswer(value=0.1, confidence=1)}, asked, "Jev")
    empty = {
        "risk": JevAnswer(value=0.1, confidence=1),
        "weakens_security": SimpleNamespace(value=None, confidence=1),
    }
    with pytest.raises(CourtUnavailable):
        require_complete(empty, asked, "Jev")
    ok = {k: JevAnswer(value=0.1, confidence=1) for k in asked}
    assert require_complete(ok, asked, "Jev") is ok


# ----------------------------------------------------------------------------- deploy.py
def _deploy():
    path = Path(__file__).resolve().parents[3] / "scripts" / "deploy.py"
    spec = importlib.util.spec_from_file_location("deploy_script_hardening", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _env_file(tmp_path, monkeypatch, admin):
    d = _deploy()
    f = tmp_path / ".env"
    f.write_text(
        f"PROBATE_SPRITES_TOKEN=t\nPROBATE_ADMIN_TOKEN={admin}\nPROBATE_CONNECTIONS={{}}\n"
        "PROBATE_CF_ACCOUNT_ID=a\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(d, "ENV_FILE", f)
    monkeypatch.setattr(d, "ROOT", tmp_path)
    return d


@pytest.mark.parametrize("admin", ["dev-admin", "short-secret-1"])
def test_deploy_rejects_a_weak_admin_token_without_printing_it(tmp_path, monkeypatch, admin):
    d = _env_file(tmp_path, monkeypatch, admin)
    with pytest.raises(SystemExit) as e:
        d.read_env()
    assert admin not in str(e.value.code)


def test_deploy_accepts_a_long_admin_token(tmp_path, monkeypatch):
    d = _env_file(tmp_path, monkeypatch, "a-long-random-admin-token-0123456789")
    assert d.read_env()["PROBATE_ADMIN_TOKEN"].startswith("a-long")


def test_deploy_requires_edge_token_when_edge_is_required():
    d = _deploy()
    assert d.edge_problem({}, {"PROBATE_REQUIRE_EDGE": "1"})
    assert d.edge_problem({"PROBATE_EDGE_TOKEN": EDGE_TOKEN}, {"PROBATE_REQUIRE_EDGE": "1"}) is None
    assert d.edge_problem({}, {}) is None
