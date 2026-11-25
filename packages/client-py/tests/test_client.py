"""Client behaviour with a mock transport (no Courthouse needed)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from probate_client import ApiError, AsyncProbateClient, ProbateClient


def make(handler, **kw) -> ProbateClient:
    return ProbateClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)), **kw)


def test_defaults_and_trailing_slash():
    assert ProbateClient().base_url == "http://localhost:8080"
    assert ProbateClient("https://x.test//").base_url == "https://x.test"


def test_api_key_header_only_when_set():
    seen = []

    def handler(req):
        seen.append(req.headers.get("x-probate-key"))
        return httpx.Response(200, json={"ok": True})

    make(handler).health()
    make(handler, api_key="k").health()
    assert seen == [None, "k"]


def test_ask_posts_json():
    def handler(req):
        assert req.method == "POST"
        assert req.url.path == "/api/generations/4/ask"
        assert req.read() == b'{"question":"why?"}'
        return httpx.Response(200, json={"answer": "a", "audio_url": None, "name": "n"})

    assert make(handler).ask(4, "why?")["answer"] == "a"


@pytest.mark.parametrize(
    ("status", "body", "message"),
    [
        (429, {"error": "rate_limited"}, "rate_limited"),
        (404, {"detail": "Not in the register"}, "Not in the register"),
        (502, "<html>", "Bad Gateway"),
    ],
)
def test_error_mapping(status, body, message):
    def handler(req):
        if isinstance(body, str):
            return httpx.Response(status, text=body)
        return httpx.Response(status, json=body)

    with pytest.raises(ApiError) as e:
        make(handler).summary()
    assert e.value.status == status
    assert e.value.message == message


def test_no_retry():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(500, json={"error": "x"})

    with pytest.raises(ApiError):
        make(handler).summary()
    assert len(calls) == 1


def test_timeout_is_passed_to_httpx():
    def handler(req):
        assert req.extensions["timeout"]["read"] == 1.5
        return httpx.Response(200, json={"ok": True})

    make(handler, timeout=1.5).health()


def test_transport_timeouts_propagate():
    def handler(req):
        raise httpx.ReadTimeout("slow", request=req)

    with pytest.raises(httpx.ReadTimeout):
        make(handler).health()


def test_events_polls_with_since_and_dedupes():
    pages = [
        [
            {"id": 2, "ts": "t", "gen": 1, "kind": "k", "text": "b"},
            {"id": 1, "ts": "t", "gen": 1, "kind": "k", "text": "a"},
        ],
        [],
        [{"id": 3, "ts": "t", "gen": None, "kind": "k", "text": "c"}],
    ]
    urls = []

    def handler(req):
        urls.append(str(req.url))
        return httpx.Response(200, json=pages.pop(0) if pages else [])

    ids = []
    for ev in make(handler).events(interval=0):
        ids.append(ev["id"])
        if ev["id"] == 3:
            break
    assert ids == [1, 2, 3]
    assert urls[0].endswith("/api/events?since=0")
    assert urls[1].endswith("/api/events?since=2")


def test_async_error_mapping():
    def handler(req):
        return httpx.Response(404, json={"detail": "Not in the register"})

    async def main():
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        async with AsyncProbateClient(http_client=http) as c:
            with pytest.raises(ApiError) as e:
                await c.trial(9)
        await http.aclose()
        return e.value

    err = asyncio.run(main())
    assert err.status == 404
