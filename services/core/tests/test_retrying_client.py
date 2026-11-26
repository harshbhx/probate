"""Dropped reads are retried for safe requests and for the Sprites API, not for vendor POSTs."""

import httpx
import pytest

import probate.common.http as h
from probate.adapters.sprites import SpritesAPI


class Flaky:
    def __init__(self, fail: int) -> None:
        self.fail = fail
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self.calls <= self.fail:
            raise httpx.ReadError("SSL: UNEXPECTED_EOF_WHILE_READING", request=request)
        return httpx.Response(200, json={"ok": True})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(h.time, "sleep", lambda s: None)


def _client(flaky: Flaky, **kw) -> httpx.Client:
    return h.gateway_client(transport=httpx.MockTransport(flaky), **kw)


def test_a_get_is_retried():
    flaky = Flaky(2)
    assert _client(flaky).get("http://x/y").json() == {"ok": True}
    assert flaky.calls == 3


def test_a_post_to_a_vendor_is_not_repeated():
    flaky = Flaky(1)
    with pytest.raises(httpx.ReadError):
        _client(flaky).post("http://x/send", json={})
    assert flaky.calls == 1


def test_retry_all_repeats_a_post():
    flaky = Flaky(2)
    assert _client(flaky, retry_all=True).post("http://x/exec").status_code == 200
    assert flaky.calls == 3


def test_it_gives_up_after_the_attempts():
    flaky = Flaky(99)
    with pytest.raises(httpx.ReadError):
        _client(flaky).get("http://x/y")
    assert flaky.calls == 4


def test_the_sprites_api_retries_its_calls():
    flaky = Flaky(1)
    api = SpritesAPI("t")
    api.http = h.gateway_client(retry_all=True, transport=httpx.MockTransport(flaky))
    assert api.http.post(api.base + "/sprites/s/exec").status_code == 200
    assert flaky.calls == 2
