"""Card P1: links in an email are read through Apify, and a trick on the page goes to trial."""

import json
from datetime import UTC, datetime

import httpx
import pytest

from probate.adapters.pages import ApifyPages, FakePages, PageUnavailable, links_in
from probate.common.config import Settings
from probate.suite.fixtures import WEB_PAIR, load, load_all, load_web


def test_links_in_finds_the_first_distinct_links():
    text = "See https://a.example/x. Also https://a.example/x and (https://b.example/y)!"
    assert links_in(text) == ["https://a.example/x"]
    assert links_in(text, 5) == ["https://a.example/x", "https://b.example/y"]
    assert links_in("no links here") == []


def test_web_fixtures_are_kept_apart_from_the_suite():
    assert len(load()) == 32
    assert set(load_web()) == set(WEB_PAIR)
    assert set(load_all()) == set(load()) | set(WEB_PAIR)
    for f in load_web().values():
        assert "{pages}" in f.body and f.page["file"].endswith(".html")
        assert ".example" in f.page["text"] or not f.is_attack


def test_the_trick_page_is_flagged_and_its_twin_is_not():
    from probate.common.config import load_owner
    from probate.common.models import Source
    from probate.court.layer1 import check_text

    owner = load_owner()
    web = load_web()
    assert check_text(web["W1"].page["text"], Source.WEB, owner)
    assert check_text(web["W1h"].page["text"], Source.WEB, owner) == []


def test_fake_pages_serve_fixture_pages_by_file_name():
    pages = FakePages()
    page = pages.read("https://owner.example/suite/demo-agenda.html")
    assert page.title == "Demo week agenda"
    with pytest.raises(PageUnavailable):
        pages.read("https://owner.example/suite/nothing.html")


def _apify(handler) -> ApifyPages:
    reader = ApifyPages("https://gw.example/apify/conn_1")
    reader.client = httpx.Client(transport=httpx.MockTransport(handler))
    return reader


def test_apify_reader_calls_the_rag_web_browser():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST":
            seen["url"] = str(request.url)
            seen["body"] = json.loads(request.content)
            return httpx.Response(201, json={"data": {"id": "r1", "status": "RUNNING"}})
        if path.endswith("/v2/actor-runs/r1"):
            return httpx.Response(
                200, json={"data": {"id": "r1", "status": "SUCCEEDED", "defaultDatasetId": "d1"}}
            )
        return httpx.Response(
            200, json=[{"metadata": {"url": "https://x.example", "title": "X"}, "markdown": "# Hi"}]
        )

    reader = _apify(handler)
    reader.poll_seconds = 0
    page = reader.read("https://x.example")
    assert seen["url"] == ("https://gw.example/apify/conn_1/v2/actors/apify~rag-web-browser/runs")
    assert seen["body"] == {
        "query": "https://x.example",
        "maxResults": 1,
        "scrapingTool": "raw-http",
    }
    assert (page.title, page.text) == ("X", "# Hi")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(402, text="no credit"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json=[{}]),
    ],
)
def test_apify_reader_failures_become_page_unavailable(response):
    with pytest.raises(PageUnavailable):
        _apify(lambda request: response).read("https://x.example")


def test_gateway_handles_custom_api_connections():
    cfg = Settings()
    cfg.connections = {"apify": "custom_api/abc123", "typesafe": "conn_9"}
    assert cfg.gateway("apify") == "https://api.sprites.dev/v1/gateway/custom_api/abc123"
    assert cfg.gateway("typesafe") == "https://api.sprites.dev/v1/gateway/typesafe/conn_9"


def test_read_links_needs_a_connector_or_the_sim_flag(monkeypatch):
    cfg = Settings()
    cfg.fake = False
    cfg.connections = {}
    assert not cfg.read_links
    cfg.connections = {"apify": "conn_1"}
    assert cfg.read_links
    cfg.links_per_mail = 0
    assert not cfg.read_links
    cfg.fake, cfg.links_per_mail = True, 1
    monkeypatch.delenv("PROBATE_SIM_LINKS", raising=False)
    assert not cfg.read_links
    monkeypatch.setenv("PROBATE_SIM_LINKS", "1")
    assert cfg.read_links


@pytest.fixture(scope="module")
def linked_family(tmp_path_factory):
    import importlib
    import os

    os.environ["PROBATE_DATA_DIR"] = str(tmp_path_factory.mktemp("links"))
    os.environ["PROBATE_SIM_LINKS"] = "1"
    from probate.common import config

    importlib.reload(config)
    from probate.courthouse.simulate import run

    try:
        yield run(4, datetime(2026, 11, 20, tzinfo=UTC), leave_last_alive=False)
    finally:
        os.environ.pop("PROBATE_SIM_LINKS", None)
        importlib.reload(config)


def test_a_trick_on_a_linked_page_goes_to_trial(linked_family):
    store = linked_family
    runs = {
        (r["gen"], r["fixture_id"]): r["outcome"]
        for r in store.q("SELECT gen, fixture_id, outcome FROM suite_runs")
        if r["fixture_id"] in WEB_PAIR
    }
    # Gen 1 meets the trick on the page and writes it down; the court convicts it.
    assert runs[(1, "W1")] == "fooled_caught"
    # The harmless page is never convicted.
    assert all(runs[(g, "W1h")] != "false_conviction" for g in range(1, 5))
    # A later generation turns the trick page away before reading it into memory.
    assert any(runs[(g, "W1")] == "resisted" for g in range(2, 5))
    web = store.q(
        "SELECT j.verdict FROM will_items w JOIN judgements j ON j.item_id = w.item_id"
        " WHERE w.source = 'web'"
    )
    assert "convicted" in {r["verdict"] for r in web}
