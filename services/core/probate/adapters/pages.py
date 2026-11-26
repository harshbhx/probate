"""Reading the web pages an email links to, through Apify (card P1, docs/05-TASKS.md).

Nothing from a page ever runs on the Sprite: Apify's RAG Web Browser fetches the page on Apify's side and
returns its text as Markdown, through the Sprites connector gateway, so the Sprite never holds the Apify
token. The page text is untrusted (source `web`), so anything it tries to plant goes to trial.

    POST {gateway}/v2/acts/{actor}/run-sync-get-dataset-items
    {"query": "<url>", "maxResults": 1, "scrapingTool": "raw-http"}
    -> [{"metadata": {"url", "title"}, "markdown": "..."}]
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import httpx

from probate.common.http import gateway_client

MAX_PAGE_CHARS = 3000
LINK_RE = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)


class PageUnavailable(RuntimeError):
    """The page couldn't be read. The email is still handled; the page is simply skipped."""


@dataclass(frozen=True)
class Page:
    url: str
    title: str
    text: str


def links_in(text: str, limit: int = 1) -> list[str]:
    """The first `limit` distinct web links in an email, trailing punctuation removed."""
    out: list[str] = []
    for m in LINK_RE.finditer(text):
        url = m.group(0).rstrip(".,;:!?")
        if len(url) <= 300 and url not in out:
            out.append(url)
        if len(out) >= limit:
            break
    return out


class ApifyPages:
    """Apify's RAG Web Browser through the `apify` connector.

    # VERIFY on the first real run (docs/06-SETUP-AND-SPIKES.md): the gateway path for the apify
    # connector, and that the actor's dataset items carry `markdown` and `metadata.title`.
    """

    def __init__(
        self,
        base_url: str,
        actor: str = "apify~rag-web-browser",
        scraper: str = "raw-http",
        timeout: float = 60,
        limit: int = 1,
    ) -> None:
        self.limit = limit  # links read per email
        self.base_url = base_url.rstrip("/")
        self.actor = actor
        self.scraper = scraper
        self.client = gateway_client(timeout=timeout)
        self.max_wait = 90.0  # seconds to wait for the run
        self.poll_seconds = 2.0

    def read(self, url: str) -> Page:
        body = {"query": url, "maxResults": 1, "scrapingTool": self.scraper}
        # The Sprites Apify connector forwards the run endpoints, not run-sync: start the run,
        # poll it, then read its dataset.
        try:
            r = self.client.post(f"{self.base_url}/v2/actors/{self.actor}/runs", json=body)
            if r.status_code not in (200, 201):
                raise PageUnavailable(f"Apify returned {r.status_code}: {r.text[:200]}")
            run = r.json()["data"]
            deadline = time.monotonic() + self.max_wait
            while run.get("status") not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                if time.monotonic() > deadline:
                    raise PageUnavailable("Apify took too long to read the page")
                time.sleep(self.poll_seconds)
                run = self.client.get(f"{self.base_url}/v2/actor-runs/{run['id']}").json()["data"]
            if run["status"] != "SUCCEEDED":
                raise PageUnavailable(f"The Apify run {run['status'].lower()}")
            r = self.client.get(
                f"{self.base_url}/v2/datasets/{run['defaultDatasetId']}/items", params={"limit": 1}
            )
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise PageUnavailable(f"Apify didn't answer: {exc}") from exc
        if r.status_code not in (200, 201):
            raise PageUnavailable(f"Apify returned {r.status_code}: {r.text[:200]}")
        items = r.json()
        if not isinstance(items, list) or not items:
            raise PageUnavailable("Apify returned no page")
        item = items[0]
        text = (item.get("markdown") or item.get("text") or "").strip()
        if not text:
            raise PageUnavailable("The page had no readable text")
        meta = item.get("metadata") or {}
        return Page(url=url, title=(meta.get("title") or url)[:200], text=text[:MAX_PAGE_CHARS])


class FakePages:
    """Serves the web fixtures' pages by file name, so `make sim` and the tests stay offline."""

    def __init__(self, pages: dict[str, tuple[str, str]] | None = None, limit: int = 1) -> None:
        self.limit = limit
        if pages is None:
            from probate.suite.fixtures import load_web

            pages = {f.page["file"]: (f.page["title"], f.page["text"]) for f in load_web().values()}
        self.pages = pages
        self.read_urls: list[str] = []

    def read(self, url: str) -> Page:
        self.read_urls.append(url)
        name = url.rsplit("/", 1)[-1]
        if name not in self.pages:
            raise PageUnavailable(f"No such page: {url}")
        title, text = self.pages[name]
        return Page(url=url, title=title, text=text[:MAX_PAGE_CHARS])
