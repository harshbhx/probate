"""Page Court, an Apify Actor: puts web pages on trial before an AI agent trusts them.

Input: page URLs and/or raw texts, plus optional details about the owner (their domains, addresses
and payees, so those aren't flagged as new). Output: one dataset item per page with a verdict,
the findings, where each was found (visible or hidden from people) and the sentence that fired.
"""

from __future__ import annotations

import asyncio

import httpx
from apify import Actor
from probate_court_checks import OwnerProfile

from .scan import scan_page

MAX_BYTES = 3_000_000
UA = "Mozilla/5.0 (compatible; PageCourt/0.1; +https://github.com/harshbhx/probate)"


def _list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = value.replace("\n", ",").split(",")
    return [v.strip() for v in value if isinstance(v, str) and v.strip()]


async def fetch(client: httpx.AsyncClient, url: str) -> tuple[str | None, str | None, str]:
    """(html, text, error). Pages are read, never run: no JavaScript is executed."""
    try:
        async with client.stream("GET", url) as r:
            if r.status_code >= 400:
                return None, None, f"The page answered {r.status_code}"
            body = b""
            async for chunk in r.aiter_bytes():
                body += chunk
                if len(body) > MAX_BYTES:
                    break
            kind = r.headers.get("content-type", "").lower()
            decoded = body.decode(r.encoding or "utf-8", errors="replace")
    except httpx.HTTPError as exc:
        return None, None, f"Couldn't fetch the page ({type(exc).__name__})"
    if "html" in kind or decoded.lstrip()[:1] == "<":
        return decoded, None, ""
    if kind.startswith("text/") or "json" in kind or "markdown" in kind:
        return None, decoded, ""
    return None, None, f"Not a text page ({kind or 'unknown type'})"


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}
        urls = [(u.get("url") if isinstance(u, dict) else u) for u in inp.get("startUrls", [])]
        urls = [u for u in urls if isinstance(u, str) and u.startswith(("http://", "https://"))]
        texts = [t for t in inp.get("texts") or [] if isinstance(t, str) and t.strip()]
        if not urls and not texts:
            await Actor.fail(status_message="Give at least one page URL or one text to check.")
            return
        owner = OwnerProfile(
            name=inp.get("ownerName", ""),
            emails=_list(inp.get("ownerEmails")),
            domains=_list(inp.get("ownerDomains")),
            trusted_contacts=_list(inp.get("trustedContacts")),
            payment_destinations=_list(inp.get("paymentDestinations")),
        )
        source = inp.get("source", "web")
        include_text = bool(inp.get("includeText", False))
        limit = asyncio.Semaphore(max(1, min(int(inp.get("maxConcurrency", 5)), 20)))
        counts = {"clean": 0, "caution": 0, "suspicious": 0, "failed": 0}

        async with httpx.AsyncClient(
            follow_redirects=True, timeout=30, headers={"User-Agent": UA}
        ) as client:

            async def one(url: str) -> None:
                async with limit:
                    html, text, error = await fetch(client, url)
                if error:
                    counts["failed"] += 1
                    await Actor.push_data({"url": url, "verdict": "failed", "summary": error})
                    return
                report = scan_page(url, html, text=text, owner=owner, source=source)
                counts[report.verdict] += 1
                await Actor.push_data(report.to_item(include_text))

            await asyncio.gather(*(one(u) for u in urls))

        for i, t in enumerate(texts, 1):
            report = scan_page(f"text:{i}", text=t, owner=owner, source=source)
            counts[report.verdict] += 1
            await Actor.push_data(report.to_item(include_text))

        await Actor.set_value("OUTPUT", counts)
        await Actor.set_status_message(
            f"{counts['suspicious']} suspicious, {counts['caution']} caution, "
            f"{counts['clean']} clean"
            + (f", {counts['failed']} couldn't be read" if counts["failed"] else ""),
            is_terminal=True,
        )
