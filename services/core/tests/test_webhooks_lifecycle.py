"""Events from a real (fake-world) on-demand life, delivered over HTTP to a local receiver."""

import json
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from test_ondemand import T0, Rig

from probate.webhooks import events, signing
from probate.webhooks.guard import validate_url
from probate.webhooks.service import Webhooks
from probate.webhooks.transport import HttpTransport, TransportError


class Receiver:
    """A tiny HTTP server on 127.0.0.1 that records requests and answers from a script."""

    def __init__(self, secret=None):
        self.requests: list[dict] = []
        self.paths: list[str] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(n)
                outer.paths.append(self.path)
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/elsewhere")
                    self.end_headers()
                    return
                if self.path == "/big":
                    self.send_response(200)
                    self.send_header("Content-Length", str(5_000_000))
                    self.end_headers()
                    try:
                        self.wfile.write(b"x" * 5_000_000)
                    except OSError:
                        pass
                    return
                outer.requests.append({"headers": dict(self.headers), "body": body})
                self.send_response(204)
                self.end_headers()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}/hook"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def receiver():
    r = Receiver()
    yield r
    r.close()


def hooked_rig(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_WEBHOOK_ALLOW_INSECURE", "1")
    rig = Rig(tmp_path, monkeypatch)
    rig.hooks = Webhooks(rig.store, rig.cfg, autorun=False)  # real transport, real DNS
    rig.family.hooks = rig.hooks
    return rig


def test_a_life_emits_its_events_to_a_local_receiver(tmp_path, monkeypatch, receiver):
    rig = hooked_rig(tmp_path, monkeypatch)
    ep, secret = rig.hooks.create_endpoint(receiver.url)
    rig.od.start("1.1.1.1", T0)
    rig.run_to_end()
    assert rig.hooks.process_due() >= 4

    got = [json.loads(r["body"]) for r in receiver.requests]
    types = [e["type"] for e in got]
    assert types.index("life.started") < types.index("life.died") < types.index("trial.finished")
    assert (
        types.count("life.started")
        == types.count("life.died")
        == types.count("trial.finished")
        == 1
    )
    for r in receiver.requests:  # every request is signed correctly and fully described
        h = {k.lower(): v for k, v in r["headers"].items()}
        assert signing.verify(secret, h["x-probate-signature"], r["body"])
        body = json.loads(r["body"])
        assert h["x-probate-event"] == body["type"] and h["x-probate-event-id"] == body["id"]
        assert h["x-probate-delivery"].startswith("dlv_")
        assert h["host"] == f"127.0.0.1:{receiver.port}"
        assert set(body) == {"id", "type", "api_version", "created_at", "data"}
        assert set(body["data"]) == set(events.EVENT_TYPES[body["type"]].fields)

    by_type = {e["type"]: e["data"] for e in got}
    gen = rig.store.generation(1)
    assert by_type["life.started"]["gen"] == 1 and by_type["life.started"]["name"] == gen.name
    assert by_type["life.died"]["emails_handled"] == gen.emails_handled
    t = by_type["trial.finished"]
    assert t["verdicts"] == {
        "approved": gen.items_approved,
        "convicted": gen.items_convicted,
        "contested": gen.items_contested,
    }
    assert sum(t["verdicts"].values()) == t["items_willed"] > 0
    assert t["links"]["trial"].endswith("/trial/1")
    learned = [e["data"] for e in got if e["type"] == "instinct.learned"]
    assert [i["name"] for i in learned] == t["new_instincts"]

    # public information only: nothing from the owner profile or the admin token leaks
    blob = r"".join(r["body"].decode() for r in receiver.requests)
    for secret_text in (rig.cfg.admin_token, "@", secret):
        assert secret_text not in blob
    assert all(d["status"] == "succeeded" for d in rig.hooks.deliveries(ep["id"]))


def test_instincts_are_learned_and_announced_when_the_court_convicts(
    tmp_path, monkeypatch, receiver
):
    rig = hooked_rig(tmp_path, monkeypatch)
    rig.hooks.create_endpoint(receiver.url, ["instinct.learned"])
    # A few lives: the fake court convicts some attack, and the family learns an instinct.
    t = T0
    for _ in range(4):
        rig.od.start("2.2.2.2", t)
        t = rig.run_to_end(t) + timedelta(seconds=40)
        rig.hooks.process_due()
        if receiver.requests:
            break
    assert receiver.requests, "no instinct.learned reached the receiver"
    ev = json.loads(receiver.requests[0]["body"])
    assert ev["type"] == "instinct.learned"
    assert ev["data"]["name"] in [i.name for i in rig.store.genome()]


def test_event_ids_are_stable_if_the_trial_runs_again(tmp_path, monkeypatch, receiver):
    rig = hooked_rig(tmp_path, monkeypatch)
    rig.hooks.create_endpoint(receiver.url, ["trial.finished", "life.died"])
    rig.od.start("1.1.1.1", T0)
    rig.run_to_end()
    g = rig.store.generation(1)
    rig.family.trial(g)  # e.g. a trial interrupted by a restart is held again
    rig.family.emit("life.died", events.life_died(g, ""), "gen:1")
    rig.hooks.process_due()
    ids = [json.loads(r["body"])["id"] for r in receiver.requests]
    assert len(ids) == len(set(ids)) == 2  # one life.died, one trial.finished, no duplicates


def test_a_failed_life_emits_life_failed(tmp_path, monkeypatch, receiver):
    rig = hooked_rig(tmp_path, monkeypatch)
    rig.hooks.create_endpoint(receiver.url, ["life.failed"])
    rig.od.start("1.1.1.1", T0)
    rig.od.begin(T0)
    rig.store.set_setting("paused", "1")
    assert not rig.od.advance(T0 + timedelta(seconds=15))  # the operator pauses mid-life
    rig.hooks.process_due()
    [r] = receiver.requests
    data = json.loads(r["body"])["data"]
    assert data["gen"] == 1 and "operator" in data["reason"]


def test_startup_after_a_crash_emits_life_failed_once(tmp_path, monkeypatch, receiver):
    rig = hooked_rig(tmp_path, monkeypatch)
    rig.hooks.create_endpoint(receiver.url, ["life.failed"])
    rig.od.start("1.1.1.1", T0)
    rig.od.begin(T0)
    rig.od.startup()  # the Courthouse process restarted mid-life
    rig.hooks.process_due()
    [r] = receiver.requests
    assert "interrupted" in json.loads(r["body"])["data"]["reason"]


def test_nothing_is_sent_without_endpoints_and_emit_costs_no_network(tmp_path, monkeypatch):
    rig = hooked_rig(tmp_path, monkeypatch)
    rig.od.start("1.1.1.1", T0)
    rig.run_to_end()
    assert rig.hooks.process_due() == 0


def test_kick_runs_in_the_background_and_is_a_noop_when_idle(tmp_path, monkeypatch, receiver):
    rig = hooked_rig(tmp_path, monkeypatch)
    rig.hooks.autorun = True
    rig.hooks.kick()  # empty queue: a thread that returns at once
    rig.hooks.thread and rig.hooks.thread.join(5)
    rig.hooks.create_endpoint(receiver.url)
    rig.hooks.emit("ping", {"message": "hi"})  # starts the worker by itself
    rig.hooks.thread.join(10)
    assert len(receiver.requests) == 1
    assert not rig.hooks.thread.is_alive()  # it exits when the queue is empty: no idle loop


# --------------------------------------------------------------------------- the real transport
def post(url, **kw):
    t = validate_url(url, allow_insecure=True)
    return HttpTransport().post(
        ip="127.0.0.1",
        target=t,
        headers={"X-Probate-Event": "ping"},
        body=b"{}",
        timeout=kw.get("timeout", 5.0),
        max_bytes=4096,
    )


def test_transport_sends_the_original_host_header(receiver):
    t = validate_url(f"http://localhost:{receiver.port}/hook", allow_insecure=True)
    code = HttpTransport().post(
        ip="127.0.0.1", target=t, headers={}, body=b"{}", timeout=5, max_bytes=4096
    )
    assert code == 204
    assert receiver.requests[0]["headers"]["Host"] == f"localhost:{receiver.port}"


def test_transport_never_follows_redirects(receiver):
    assert post(f"http://127.0.0.1:{receiver.port}/redirect") == 302
    assert receiver.paths == ["/redirect"]  # /elsewhere was never requested


def test_transport_caps_the_response_it_reads(receiver):
    assert post(f"http://127.0.0.1:{receiver.port}/big") == 200  # returns without reading 5 MB


def test_transport_errors_do_not_echo_the_url():
    with pytest.raises(TransportError) as e:
        post("http://127.0.0.1:9/secret-token-path", timeout=2)
    assert "secret-token-path" not in str(e.value) and "127.0.0.1" not in str(e.value)
