"""Webhooks: signing, endpoints, the persisted queue, retries, circuit breaker, admin routes."""

import importlib
import json
import logging
import os

import pytest

from probate.common.config import Settings
from probate.courthouse.store import Store
from probate.webhooks import events, signing
from probate.webhooks.service import (
    BACKOFF_SECONDS,
    KEEP_DELIVERIES,
    WebhookError,
    Webhooks,
)
from probate.webhooks.transport import TransportError

PUBLIC = "93.184.216.34"
URL = "https://hooks.example.com/probate"


class FakeTransport:
    """Records every request; replies come from a script (status codes or exceptions)."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls: list[dict] = []

    def post(self, *, ip, target, headers, body, timeout, max_bytes):
        self.calls.append(
            {
                "ip": ip,
                "target": target,
                "headers": headers,
                "body": body,
                "timeout": timeout,
                "max_bytes": max_bytes,
            }
        )
        out = self.script.pop(0) if self.script else 200
        if isinstance(out, Exception):
            raise out
        return out


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def make(tmp_path, monkeypatch, *script, **env):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))
    for k, v in env.items():
        monkeypatch.setenv(k, str(v))
    cfg = Settings(fake=True)
    store = Store(cfg.db_path)
    clock = Clock()
    tr = FakeTransport(*script)
    hooks = Webhooks(
        store,
        cfg,
        transport=tr,
        resolver=lambda h, p: [PUBLIC],
        clock=clock,
        rng=lambda: 0.5,
        autorun=False,
    )
    return hooks, tr, clock, store, cfg


def ping_payload():
    return {"message": "hi"}


# ------------------------------------------------------------------------------- signing
def test_signature_format_and_value():
    body = b'{"a":1}'
    header = signing.sign("whsec_x", body, 1700000000)
    import hashlib
    import hmac

    want = hmac.new(b"whsec_x", b"1700000000." + body, hashlib.sha256).hexdigest()
    assert header == f"t=1700000000,v1={want}"


def test_verify_accepts_and_rejects():
    body = b'{"a":1}'
    h = signing.sign("s3cret", body, 1000)
    assert signing.verify("s3cret", h, body, now=1100)
    assert not signing.verify("other", h, body, now=1100)  # wrong secret
    assert not signing.verify("s3cret", h, body + b" ", now=1100)  # tampered body
    assert not signing.verify("s3cret", h, body, now=1000 + 301)  # outside the replay window
    assert not signing.verify("s3cret", h, body, now=1000 - 301)
    for junk in ("", "v1=abc", "t=abc,v1=1", "garbage", "t=1000", None):
        assert not signing.verify("s3cret", junk, body, now=1000)


def test_secrets_are_long_and_unique():
    a, b = signing.new_secret(), signing.new_secret()
    assert a != b and a.startswith("whsec_") and len(a) >= 40


# ------------------------------------------------------------------------------- events
def test_event_schema_is_enforced():
    ev = events.build("ping", {"message": "x"})
    assert ev["type"] == "ping" and ev["id"].startswith("evt_") and ev["api_version"]
    with pytest.raises(ValueError):
        events.build("ping", {"message": "x", "email": "a@b.c"})  # extra field
    with pytest.raises(ValueError):
        events.build("life.died", {"gen": 1})  # missing fields
    with pytest.raises(ValueError):
        events.build("nope", {})


def test_event_ids_are_deterministic_only_with_dedupe():
    a = events.build("ping", {"message": "x"}, dedupe="k")
    b = events.build("ping", {"message": "x"}, dedupe="k")
    c = events.build("ping", {"message": "x"})
    d = events.build("ping", {"message": "x"})
    assert a["id"] == b["id"] and c["id"] != d["id"]


def test_new_types_register_in_one_place():
    events.register("demo.thing", "x", {"n": "a number"})
    try:
        assert "demo.thing" in events.event_names()
        assert events.build("demo.thing", {"n": 1})["data"] == {"n": 1}
    finally:
        del events.EVENT_TYPES["demo.thing"]


# ------------------------------------------------------------------------------- endpoints
def test_create_endpoint_returns_secret_once(tmp_path, monkeypatch):
    hooks, *_ = make(tmp_path, monkeypatch)
    ep, secret = hooks.create_endpoint(URL, ["life.died"], "my bridge")
    assert secret.startswith("whsec_")
    assert "secret" not in ep and secret not in json.dumps(hooks.list_endpoints())
    assert ep["events"] == ["life.died"] and ep["enabled"] and ep["source"] == "admin"


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.example.com/x",
        "https://127.0.0.1/x",
        "https://u:p@hooks.example.com/",
        "https://hooks.example.com:8443/x",
    ],
)
def test_create_endpoint_applies_the_guard(tmp_path, monkeypatch, url):
    hooks, *_ = make(tmp_path, monkeypatch)
    with pytest.raises(WebhookError):
        hooks.create_endpoint(url)
    assert hooks.list_endpoints() == []


def test_create_endpoint_rejects_names_that_resolve_privately(tmp_path, monkeypatch):
    hooks, *_ = make(tmp_path, monkeypatch)
    hooks.resolver = lambda h, p: ["10.0.0.1"]
    with pytest.raises(WebhookError, match="private"):
        hooks.create_endpoint(URL)


def test_create_endpoint_rejects_unknown_events_and_caps_count(tmp_path, monkeypatch):
    hooks, *_ = make(tmp_path, monkeypatch, PROBATE_WEBHOOK_MAX_ENDPOINTS=2)
    with pytest.raises(WebhookError, match="unknown"):
        hooks.create_endpoint(URL, ["life.nope"])
    with pytest.raises(WebhookError):
        hooks.create_endpoint(URL, ["ping"])  # ping is not subscribable
    hooks.create_endpoint(URL)
    hooks.create_endpoint(URL + "2")
    with pytest.raises(WebhookError) as e:
        hooks.create_endpoint(URL + "3")
    assert e.value.status == 409


def test_env_endpoints_need_a_secret_and_cannot_be_deleted(tmp_path, monkeypatch):
    hooks, *_ = make(tmp_path, monkeypatch, PROBATE_WEBHOOK_URLS=URL)
    hooks.sync_env()
    assert hooks.list_endpoints() == []  # no secret, nothing loaded
    hooks, tr, clock, _store, _cfg = make(
        tmp_path,
        monkeypatch,
        PROBATE_WEBHOOK_URLS=URL + "," + "http://bad.example.com/",
        PROBATE_WEBHOOK_SECRET="whsec_env",
    )
    hooks.sync_env()
    hooks.sync_env()  # idempotent
    [ep] = hooks.list_endpoints()  # the http:// one is skipped
    assert ep["source"] == "env" and "whsec_env" not in json.dumps(ep)
    with pytest.raises(WebhookError) as e:
        hooks.delete_endpoint(ep["id"])
    assert e.value.status == 409
    hooks.emit("ping", ping_payload())
    hooks.process_due()
    assert signing.verify(
        "whsec_env", tr.calls[0]["headers"]["X-Probate-Signature"], tr.calls[0]["body"], now=clock.t
    )
    # removing it from the env removes the row
    hooks.cfg.webhook_urls = []
    hooks.sync_env()
    assert hooks.list_endpoints() == []


# ------------------------------------------------------------------------------- delivery
def test_delivery_headers_body_and_signature(tmp_path, monkeypatch):
    hooks, tr, clock, *_ = make(tmp_path, monkeypatch)
    ep, secret = hooks.create_endpoint(URL)
    hooks.emit("ping", ping_payload())
    assert hooks.process_due() == 1
    [c] = tr.calls
    h = c["headers"]
    assert c["ip"] == PUBLIC and c["target"].host == "hooks.example.com"
    assert c["timeout"] == 5.0 and c["max_bytes"] <= 8192
    body = json.loads(c["body"])
    assert body["type"] == "ping" and body["id"] == h["X-Probate-Event-Id"]
    assert h["X-Probate-Event"] == "ping" and h["X-Probate-Delivery"].startswith("dlv_")
    assert h["Content-Type"] == "application/json"
    assert signing.verify(secret, h["X-Probate-Signature"], c["body"], now=clock.t)
    [d] = hooks.deliveries(ep["id"])
    assert d["status"] == "succeeded" and d["attempts"] == 1 and d["last_status_code"] == 200
    assert hooks.endpoint(ep["id"])["last_success_at"]


def test_event_filter(tmp_path, monkeypatch):
    hooks, _tr, *_ = make(tmp_path, monkeypatch)
    only_died, _ = hooks.create_endpoint(URL, ["life.died"])
    everything, _ = hooks.create_endpoint(URL + "-all")
    died = {k: None for k in events.EVENT_TYPES["life.died"].fields}
    hooks.emit("life.died", died)
    started = {k: None for k in events.EVENT_TYPES["life.started"].fields}
    hooks.emit("life.started", started)
    assert hooks.process_due() == 3
    assert len(hooks.deliveries(only_died["id"])) == 1
    assert len(hooks.deliveries(everything["id"])) == 2


def test_retry_schedule_with_a_fake_clock(tmp_path, monkeypatch):
    hooks, tr, clock, *_ = make(
        tmp_path,
        monkeypatch,
        500,
        502,
        TransportError("timed out"),
        200,
        PROBATE_WEBHOOK_MAX_FAILURES=99,
    )
    ep, _ = hooks.create_endpoint(URL)
    hooks.emit("ping", ping_payload())
    t0 = clock.t
    delivery_ids = set()
    for i, delay in enumerate(BACKOFF_SECONDS):
        assert hooks.process_due(clock.t) == 1, f"attempt {i + 1}"
        [d] = hooks.deliveries(ep["id"])
        assert d["status"] == "pending" and d["attempts"] == i + 1
        delivery_ids.add(d["id"])
        # nothing is due before the delay (rng=0.5 means no jitter)
        assert hooks.process_due(clock.t + delay - 1) == 0
        clock.t += delay
    assert hooks.process_due(clock.t) == 1
    [d] = hooks.deliveries(ep["id"])
    assert d["status"] == "succeeded" and d["attempts"] == 4
    assert clock.t - t0 == sum(BACKOFF_SECONDS)
    # one event id, one delivery id and one body across every attempt
    assert len({c["headers"]["X-Probate-Delivery"] for c in tr.calls}) == 1
    assert len({c["headers"]["X-Probate-Event-Id"] for c in tr.calls}) == 1
    assert len({c["body"] for c in tr.calls}) == 1
    assert [c["headers"]["X-Probate-Attempt"] for c in tr.calls] == ["1", "2", "3", "4"]
    # each attempt is freshly signed
    sigs = [c["headers"]["X-Probate-Signature"] for c in tr.calls]
    assert len(set(sigs)) == 4


def test_gives_up_after_the_last_backoff(tmp_path, monkeypatch):
    hooks, tr, clock, *_ = make(
        tmp_path, monkeypatch, *([503] * 10), PROBATE_WEBHOOK_MAX_FAILURES=99
    )
    ep, _ = hooks.create_endpoint(URL)
    hooks.emit("ping", ping_payload())
    for _ in range(len(BACKOFF_SECONDS) + 1):
        hooks.process_due(clock.t)
        clock.t += 1900
    assert len(tr.calls) == 4
    [d] = hooks.deliveries(ep["id"])
    assert d["status"] == "failed" and d["attempts"] == 4 and d["last_error"] == "HTTP 503"
    assert hooks.process_due(clock.t) == 0  # finished; no more attempts


def test_jitter_stays_within_twenty_percent(tmp_path, monkeypatch):
    for r, factor in ((0.0, 0.8), (1.0, 1.2)):
        hooks, _tr, clock, store, _ = make(tmp_path / str(r), monkeypatch, 500)
        hooks.rng = lambda r=r: r
        _ep, _ = hooks.create_endpoint(URL)
        hooks.emit("ping", ping_payload())
        hooks.process_due(clock.t)
        row = store.one("SELECT next_attempt_at FROM webhook_deliveries")
        assert row["next_attempt_at"] == pytest.approx(clock.t + BACKOFF_SECONDS[0] * factor)


def test_circuit_breaker_disables_and_can_be_reset(tmp_path, monkeypatch):
    hooks, tr, clock, *_ = make(
        tmp_path, monkeypatch, *([500] * 20), PROBATE_WEBHOOK_MAX_FAILURES=3
    )
    ep, _ = hooks.create_endpoint(URL)
    for _ in range(3):
        hooks.emit("ping", ping_payload())
    hooks.process_due(clock.t)  # three deliveries fail once each: the third trips the breaker
    shown = hooks.endpoint(ep["id"])
    assert not shown["enabled"] and shown["consecutive_failures"] == 3
    assert "Disabled after 3" in shown["disabled_reason"]
    assert {d["status"] for d in hooks.deliveries(ep["id"])} <= {"skipped", "pending"}
    n = len(tr.calls)
    hooks.emit("ping", ping_payload())  # disabled endpoints get nothing queued
    clock.t += 10_000
    assert hooks.process_due(clock.t) == 0 and len(tr.calls) == n
    back = hooks.set_enabled(ep["id"], True)
    assert back["enabled"] and back["consecutive_failures"] == 0 and back["disabled_reason"] is None


def test_success_resets_the_failure_streak(tmp_path, monkeypatch):
    hooks, _tr, clock, *_ = make(
        tmp_path, monkeypatch, 500, 500, 200, PROBATE_WEBHOOK_MAX_FAILURES=3
    )
    ep, _ = hooks.create_endpoint(URL)
    for _ in range(3):
        hooks.emit("ping", ping_payload())
    hooks.process_due(clock.t)
    assert hooks.endpoint(ep["id"])["consecutive_failures"] == 0
    assert hooks.endpoint(ep["id"])["enabled"]


def test_redirects_and_non_2xx_are_failures(tmp_path, monkeypatch):
    hooks, _tr, clock, *_ = make(tmp_path, monkeypatch, 301, 404, 204)
    ep, _ = hooks.create_endpoint(URL)
    for _ in range(3):
        hooks.emit("ping", ping_payload())
    hooks.process_due(clock.t)
    got = {d["last_status_code"]: d["status"] for d in hooks.deliveries(ep["id"])}
    assert got == {301: "pending", 404: "pending", 204: "succeeded"}


def test_guard_is_rechecked_at_delivery_time(tmp_path, monkeypatch):
    """DNS rebinding: the name was public when added, loopback by the time we connect."""
    hooks, tr, clock, *_ = make(tmp_path, monkeypatch)
    ep, _ = hooks.create_endpoint(URL)
    hooks.resolver = lambda h, p: ["127.0.0.1"]
    hooks.emit("ping", ping_payload())
    hooks.process_due(clock.t)
    assert tr.calls == []  # never connected
    [d] = hooks.deliveries(ep["id"])
    assert "private or reserved" in d["last_error"]


def test_connect_uses_the_resolved_ip_not_a_second_lookup(tmp_path, monkeypatch):
    hooks, tr, clock, *_ = make(tmp_path, monkeypatch)
    hooks.create_endpoint(URL)
    lookups = []
    hooks.resolver = lambda h, p: lookups.append(h) or [PUBLIC]
    hooks.emit("ping", ping_payload())
    hooks.process_due(clock.t)
    assert lookups == ["hooks.example.com"] and tr.calls[0]["ip"] == PUBLIC


def test_stale_pending_deliveries_expire(tmp_path, monkeypatch):
    hooks, _tr, clock, *_ = make(tmp_path, monkeypatch, 500)
    ep, _ = hooks.create_endpoint(URL)
    hooks.emit("ping", ping_payload())
    hooks.process_due(clock.t)
    clock.t += 7 * 3600
    assert hooks.process_due(clock.t) == 0
    [d] = hooks.deliveries(ep["id"])
    assert d["status"] == "failed" and "expired" in d["last_error"]


# ------------------------------------------------------------------------------- persistence
def test_queue_survives_a_restart(tmp_path, monkeypatch):
    hooks, tr, clock, store, cfg = make(tmp_path, monkeypatch, 500)
    ep, secret = hooks.create_endpoint(URL)
    hooks.emit("ping", ping_payload())
    hooks.process_due(clock.t)  # attempt 1 fails; attempt 2 is queued for +60 s
    [first] = tr.calls
    del hooks, store  # the Courthouse process goes away

    store2 = Store(cfg.db_path)
    tr2 = FakeTransport(200)
    hooks2 = Webhooks(
        store2,
        cfg,
        transport=tr2,
        resolver=lambda h, p: [PUBLIC],
        clock=clock,
        rng=lambda: 0.5,
        autorun=False,
    )
    assert hooks2.process_due(clock.t) == 0  # not due yet
    clock.t += 61
    assert hooks2.process_due(clock.t) == 1
    [second] = tr2.calls
    assert second["headers"]["X-Probate-Delivery"] == first["headers"]["X-Probate-Delivery"]
    assert second["body"] == first["body"]
    assert signing.verify(
        secret, second["headers"]["X-Probate-Signature"], second["body"], now=clock.t
    )
    assert hooks2.deliveries(ep["id"])[0]["status"] == "succeeded"


def test_dedupe_makes_emission_idempotent(tmp_path, monkeypatch):
    hooks, _tr, clock, *_ = make(tmp_path, monkeypatch)
    ep, _ = hooks.create_endpoint(URL)
    data = {k: None for k in events.EVENT_TYPES["life.died"].fields}
    a = hooks.emit("life.died", data, dedupe="gen:1")
    b = hooks.emit("life.died", data, dedupe="gen:1")
    assert a == b
    assert hooks.process_due(clock.t) == 1
    assert len(hooks.deliveries(ep["id"])) == 1


def test_retention_is_capped(tmp_path, monkeypatch):
    hooks, _tr, clock, store, _ = make(tmp_path, monkeypatch)
    _ep, _ = hooks.create_endpoint(URL)
    for i in range(KEEP_DELIVERIES + 30):
        hooks.emit("ping", ping_payload())
        clock.t += 1
    hooks.process_due(clock.t)
    n = store.one("SELECT COUNT(*) AS n FROM webhook_deliveries")["n"]
    assert n == KEEP_DELIVERIES
    clock.t += 7200
    hooks.process_due(clock.t)
    assert store.one("SELECT COUNT(*) AS n FROM webhook_events")["n"] == KEEP_DELIVERIES


def test_emit_never_raises(tmp_path, monkeypatch):
    hooks, *_ = make(tmp_path, monkeypatch)
    assert hooks.emit("not.a.type", {}) is None
    assert hooks.emit("ping", {"wrong": 1}) is None


# ------------------------------------------------------------------------------- no secrets
def test_no_secrets_in_logs_deliveries_or_listings(tmp_path, monkeypatch, caplog):
    secret_url = "https://hooks.example.com/services/T000/B000/tokentokentoken"
    hooks, _tr, clock, store, _ = make(
        tmp_path,
        monkeypatch,
        TransportError("boom talking to " + secret_url),
        500,
        PROBATE_WEBHOOK_MAX_FAILURES=2,
    )
    with caplog.at_level(logging.DEBUG):
        ep, secret = hooks.create_endpoint(secret_url)
        hooks.emit("ping", ping_payload())
        hooks.emit("ping", ping_payload())
        hooks.process_due(clock.t)
    blob = json.dumps(hooks.deliveries(ep["id"])) + json.dumps(hooks.list_endpoints())
    assert secret not in blob and "tokentokentoken" not in json.dumps(hooks.deliveries(ep["id"]))
    assert secret not in caplog.text and "tokentokentoken" not in caplog.text
    # the secret exists in exactly one table column and nowhere else in the database
    for table in ("webhook_events", "webhook_deliveries"):
        for row in store.q(f"SELECT * FROM {table}"):
            assert secret not in json.dumps(dict(zip(row.keys(), tuple(row))), default=str)


def test_payload_fields_are_public_only(tmp_path, monkeypatch):
    """Every declared field is something the public API already exposes."""
    allowed = {
        "gen",
        "name",
        "born_at",
        "dies_at",
        "died_at",
        "genome_size",
        "emails_handled",
        "items_willed",
        "verdicts",
        "attacks_met",
        "attacks_resisted",
        "cause_of_death",
        "epitaph",
        "new_instincts",
        "question",
        "lore",
        "reason",
        "links",
        "message",
    }
    for et in events.EVENT_TYPES.values():
        assert set(et.fields) <= allowed, et.name
    assert not {"email", "token", "secret", "owner", "admin"} & {
        f for et in events.EVENT_TYPES.values() for f in et.fields
    }


# ------------------------------------------------------------------------------- admin routes
@pytest.fixture
def api(tmp_path):
    os.environ["PROBATE_DATA_DIR"] = str(tmp_path)
    os.environ["PROBATE_ADMIN_TOKEN"] = "test-admin-token"
    from probate.common import config

    importlib.reload(config)
    from fastapi.testclient import TestClient

    from probate.courthouse import app as app_module

    importlib.reload(app_module)
    tr = FakeTransport()
    app_module.hooks.transport = tr
    app_module.hooks.resolver = lambda h, p: [PUBLIC]
    app_module.hooks.autorun = False
    yield TestClient(app_module.app), app_module, tr
    os.environ.pop("PROBATE_ADMIN_TOKEN", None)
    os.environ.pop("PROBATE_DATA_DIR", None)
    importlib.reload(config)
    importlib.reload(app_module)


ADMIN = {"x-probate-admin": "test-admin-token"}


def test_admin_routes_require_the_admin_token(api):
    client, *_ = api
    calls = [
        ("post", "/admin/webhooks", {"json": {"url": URL}}),
        ("get", "/admin/webhooks", {}),
        ("patch", "/admin/webhooks/we_x", {"json": {"enabled": True}}),
        ("delete", "/admin/webhooks/we_x", {}),
        ("get", "/admin/webhooks/we_x/deliveries", {}),
        ("post", "/admin/webhooks/we_x/test", {}),
    ]
    for method, path, kw in calls:
        assert getattr(client, method)(path, **kw).status_code == 403, path
        bad = getattr(client, method)(path, headers={"x-probate-admin": "nope"}, **kw)
        assert bad.status_code == 403, path
    assert client.get("/admin/webhooks", headers=ADMIN).status_code == 200


def test_admin_lifecycle_and_secret_shown_once(api):
    client, app_module, tr = api
    r = client.post("/admin/webhooks", json={"url": URL, "events": ["life.died"]}, headers=ADMIN)
    assert r.status_code == 201
    made = r.json()
    secret = made["secret"]
    assert secret.startswith("whsec_")

    listed = client.get("/admin/webhooks", headers=ADMIN)
    assert [e["id"] for e in listed.json()] == [made["id"]]
    assert secret not in listed.text and "secret" not in listed.json()[0]

    t = client.post(f"/admin/webhooks/{made['id']}/test", headers=ADMIN)
    assert t.status_code == 202
    app_module.hooks.process_due()
    d = client.get(f"/admin/webhooks/{made['id']}/deliveries", headers=ADMIN).json()
    assert d[0]["event_type"] == "ping" and d[0]["status"] == "succeeded"
    assert secret not in json.dumps(d)
    assert tr.calls[0]["headers"]["X-Probate-Event"] == "ping"  # ping bypasses the event filter

    assert (
        client.patch(
            f"/admin/webhooks/{made['id']}", json={"enabled": False}, headers=ADMIN
        ).json()["enabled"]
        is False
    )
    assert client.post(f"/admin/webhooks/{made['id']}/test", headers=ADMIN).status_code == 409
    assert client.delete(f"/admin/webhooks/{made['id']}", headers=ADMIN).status_code == 200
    assert client.delete(f"/admin/webhooks/{made['id']}", headers=ADMIN).status_code == 404
    assert client.get(f"/admin/webhooks/{made['id']}/deliveries", headers=ADMIN).status_code == 404


def test_admin_create_rejects_bad_urls_with_400(api):
    client, *_ = api
    for url in ("http://example.com/", "https://10.0.0.1/", "https://user:pw@example.com/"):
        r = client.post("/admin/webhooks", json={"url": url}, headers=ADMIN)
        assert r.status_code == 400, url
    assert client.get("/admin/webhooks", headers=ADMIN).json() == []


def test_there_is_no_public_way_to_subscribe(api):
    client, *_ = api
    routes = {(m, r.path) for r in client.app.routes for m in getattr(r, "methods", ())}
    hook_routes = {p for _, p in routes if "webhook" in p}
    assert hook_routes and all(p.startswith("/admin/") for p in hook_routes)


def test_store_survives_concurrent_writers_and_readers(tmp_path, monkeypatch):
    """The webhook worker shares the store with the life thread; statements must not interleave."""
    import threading

    _hooks, _tr, _clock, store, _ = make(tmp_path, monkeypatch)
    errors = []

    def hammer(n):
        try:
            for i in range(300):
                store.set_setting(f"k{n}", str(i))
                store.q("SELECT * FROM settings")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=hammer, args=(n,)) for n in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
