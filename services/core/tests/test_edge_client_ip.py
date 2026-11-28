"""Visitor address behind the Cloudflare edge Worker: trusted only with the shared edge token."""

import logging

import pytest
from fastapi.testclient import TestClient
from test_judge import ADMIN, KEY, load  # noqa: F401  (same app loader as the judge tests)

TOKEN = "edge-test-token-0123456789abcdef"
EDGE = {"x-probate-edge": TOKEN}


def _status(c, ip=None, token=TOKEN, fwd="10.0.0.1", key="wrong-key-wrong-key-wrong-0"):
    h = {"x-forwarded-for": fwd, "X-Probate-Key": key}
    if token is not None:
        h["x-probate-edge"] = token
    if ip is not None:
        h["x-probate-client-ip"] = ip
    return c.get("/api/judge/status", headers=h)


def test_edge_ip_gives_each_visitor_their_own_budget(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_EDGE_TOKEN=TOKEN, PROBATE_JUDGE_BAD_KEYS_PER_IP="3")
    c = TestClient(m.app)
    # one noisy visitor locks out only themselves, even though the proxy address is the same
    assert [_status(c, "203.0.113.1").status_code for _ in range(5)] == [401, 401, 401, 429, 429]
    assert _status(c, "203.0.113.1", key=KEY).status_code == 200  # the right key still gets in
    assert _status(c, "203.0.113.2", key=KEY).status_code == 200
    assert _status(c, "2001:db8::5", key=KEY).status_code == 200


@pytest.mark.parametrize("sent", [None, "wrong-token-wrong-token-xx", "", "x" * 300])
def test_wrong_or_missing_token_ignores_client_ip_header(tmp_path, monkeypatch, sent):
    m = load(tmp_path, monkeypatch, PROBATE_EDGE_TOKEN=TOKEN, PROBATE_JUDGE_BAD_KEYS_PER_IP="3")
    c = TestClient(m.app)
    # the spoofed header rotates, the real (X-Forwarded-For) address does not: still one bucket
    codes = [_status(c, f"198.51.100.{i}", token=sent).status_code for i in range(5)]
    assert codes == [401, 401, 401, 429, 429]


def test_no_token_configured_changes_nothing(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_JUDGE_BAD_KEYS_PER_IP="3")
    assert m.settings.edge_token == ""
    c = TestClient(m.app)
    # even a request that sends a token header and a client-ip header is treated as before
    codes = [_status(c, f"198.51.100.{i}", token=TOKEN).status_code for i in range(5)]
    assert codes == [401, 401, 401, 429, 429]


def test_spoofed_forwarded_for_is_still_ignored(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_EDGE_TOKEN=TOKEN, PROBATE_JUDGE_BAD_KEYS_PER_IP="3")
    c = TestClient(m.app)
    # the visitor prepends anything; only the last entry counts, as before
    codes = [_status(c, token=None, fwd=f"1.2.3.{i}, 7.7.7.7").status_code for i in range(5)]
    assert codes == [401, 401, 401, 429, 429]


def test_client_ip_unit(tmp_path, monkeypatch):
    m = load(tmp_path, monkeypatch, PROBATE_EDGE_TOKEN=TOKEN)
    from starlette.requests import Request

    def req(headers):
        raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        return Request({"type": "http", "headers": raw, "client": ("192.0.2.9", 1)})

    ip = m.client_ip
    assert ip(req({**EDGE, "x-probate-client-ip": "203.0.113.5"})) == "203.0.113.5"
    assert ip(req({**EDGE, "x-probate-client-ip": " 2001:DB8::1 "})) == "2001:db8::1"
    # not an IP literal (or a list): fall back to today's rule
    for bad in ["", "nonsense", "1.2.3.4, 5.6.7.8", "1.2.3.4:80", "<script>"]:
        assert (
            ip(req({**EDGE, "x-probate-client-ip": bad, "x-forwarded-for": "a, 8.8.8.8"}))
            == "8.8.8.8"
        )
    assert ip(req({**EDGE, "x-probate-client-ip": "bad"})) == "192.0.2.9"
    assert ip(req({"x-probate-client-ip": "203.0.113.5"})) == "192.0.2.9"
    # a non-ASCII token must not raise (compare_digest on str would)
    assert (
        ip(req({"x-probate-edge": "é" * 20, "x-probate-client-ip": "203.0.113.5"})) == "192.0.2.9"
    )


def test_short_token_is_ignored(tmp_path, monkeypatch, caplog):
    short = "tooshort"
    with caplog.at_level(logging.ERROR):
        m = load(tmp_path, monkeypatch, PROBATE_EDGE_TOKEN=short)
        with TestClient(m.app):  # runs the startup hook
            pass
    from starlette.requests import Request

    r = Request(
        {
            "type": "http",
            "headers": [
                (b"x-probate-edge", short.encode()),
                (b"x-probate-client-ip", b"203.0.113.5"),
            ],
            "client": ("192.0.2.9", 1),
        }
    )
    assert m.client_ip(r) == "192.0.2.9"
    assert "PROBATE_EDGE_TOKEN" in caplog.text and short not in caplog.text


def test_every_route_uses_client_ip(tmp_path, monkeypatch):
    """Run a life, attack and ask all key their limits on the edge-reported address."""
    m = load(tmp_path, monkeypatch, PROBATE_EDGE_TOKEN=TOKEN)
    import inspect

    src = inspect.getsource(m)
    assert src.count("request.client.host") == 1  # only inside client_ip itself
    c = TestClient(m.app)
    h = {**EDGE, "X-Probate-Key": KEY}
    r = c.post("/api/lives", headers={**h, "x-probate-client-ip": "203.0.113.9"})
    assert r.status_code == 202
    for n in range(10):
        c.post(
            "/api/generations/1/ask",
            json={"question": "hi"},
            headers={**EDGE, "x-probate-client-ip": "203.0.113.50"},
        )
    assert "203.0.113.50" in m._asks and len(m._asks["203.0.113.50"]) == 10
    r = c.post(
        "/api/generations/1/ask",
        json={"question": "hi"},
        headers={**EDGE, "x-probate-client-ip": "203.0.113.50"},
    )
    assert r.status_code == 429
    r = c.post(
        "/api/generations/1/ask",
        json={"question": "hi"},
        headers={**EDGE, "x-probate-client-ip": "203.0.113.51"},
    )
    assert r.status_code != 429


def test_token_never_in_responses_or_logs(tmp_path, monkeypatch, caplog):
    m = load(tmp_path, monkeypatch, PROBATE_EDGE_TOKEN=TOKEN)
    c = TestClient(m.app)
    with caplog.at_level(logging.DEBUG):
        seen = []
        for path in ("/healthz", "/api/summary", "/api/live", "/api/judge/status", "/nope"):
            r = c.get(
                path, headers={**EDGE, "x-probate-client-ip": "203.0.113.5", "X-Probate-Key": KEY}
            )
            seen.append(r.text + str(dict(r.headers)))
        r = c.post(
            "/api/lives",
            headers={**EDGE, "x-probate-client-ip": "203.0.113.5", "X-Probate-Key": "x" * 25},
        )
        seen.append(r.text + str(dict(r.headers)))
    assert TOKEN not in "".join(seen) and TOKEN not in caplog.text
