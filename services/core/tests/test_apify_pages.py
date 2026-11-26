"""Reading a page through the Sprites Apify connector: start a run, poll it, read its dataset."""

import httpx
import pytest

from probate.adapters.pages import ApifyPages, PageUnavailable


def _pages(handler) -> ApifyPages:
    p = ApifyPages("https://gw/apify/ID", actor="apify~rag-web-browser")
    p.client = httpx.Client(transport=httpx.MockTransport(handler))
    p.poll_seconds = 0
    return p


def test_start_poll_and_read_dataset():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        path = request.url.path
        if request.method == "POST" and path.endswith("/v2/actors/apify~rag-web-browser/runs"):
            return httpx.Response(201, json={"data": {"id": "r1", "status": "RUNNING"}})
        if path.endswith("/v2/actor-runs/r1"):
            n = sum(1 for c in calls if c.endswith("/v2/actor-runs/r1"))
            status = "SUCCEEDED" if n >= 2 else "RUNNING"
            return httpx.Response(
                200, json={"data": {"id": "r1", "status": status, "defaultDatasetId": "d1"}}
            )
        if path.endswith("/v2/datasets/d1/items"):
            return httpx.Response(
                200, json=[{"markdown": "Hello page", "metadata": {"title": "T"}}]
            )
        return httpx.Response(404)

    page = _pages(handler).read("https://x.test/p.html")
    assert page.title == "T" and page.text == "Hello page"
    assert not any("run-sync" in c for c in calls)  # the connector does not forward run-sync


def test_a_failed_run_is_page_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"data": {"id": "r1", "status": "FAILED"}})
        return httpx.Response(200, json={"data": {"id": "r1", "status": "FAILED"}})

    with pytest.raises(PageUnavailable):
        _pages(handler).read("https://x.test/p.html")


def test_a_refused_start_is_page_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"error": "endpoint is not supported by the Apify connector"}
        )

    with pytest.raises(PageUnavailable):
        _pages(handler).read("https://x.test/p.html")
