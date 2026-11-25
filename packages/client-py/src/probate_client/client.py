"""Sync and async clients. Both use httpx and never retry."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx

from probate_client.types import (
    AskAnswer,
    CourthouseEvent,
    Evidence,
    GenerationDetail,
    Genome,
    Health,
    Instinct,
    Summary,
    Trial,
)

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_TIMEOUT = 30.0


class ApiError(Exception):
    """The Courthouse answered with an error status, or the body was not JSON."""

    def __init__(self, status: int, message: str, body: Any = None) -> None:
        super().__init__(f"{status}: {message}")
        self.status = status
        self.message = message
        self.body = body


def _headers(api_key: str | None) -> dict[str, str]:
    h = {"Accept": "application/json"}
    if api_key:
        h["X-Probate-Key"] = api_key  # reserved: the Courthouse does not check it today
    return h


def _parse(res: httpx.Response) -> Any:
    try:
        data = res.json() if res.content else None
    except ValueError:
        data = None
    if res.is_error:
        msg = None
        if isinstance(data, dict):
            msg = data.get("error") or data.get("detail")
        raise ApiError(
            res.status_code,
            msg if isinstance(msg, str) else (res.reason_phrase or f"HTTP {res.status_code}"),
            data,
        )
    if data is None:
        raise ApiError(res.status_code, "Response was not JSON")
    return data


def _gen(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"Expected an integer generation number, got {n!r}")
    return n


class ProbateClient:
    """Synchronous client.

    ``http_client`` lets you pass your own ``httpx.Client`` (for tests or proxies); it is
    not closed by :meth:`close`. ``timeout`` is in seconds (``None`` disables it).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        api_key: str | None = None,
        timeout: float | None = DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._owns = http_client is None
        self._http = http_client or httpx.Client()

    def __enter__(self) -> ProbateClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns:
            self._http.close()

    def _request(self, method: str, path: str, *, json: Any = None) -> Any:
        res = self._http.request(
            method,
            self.base_url + path,
            json=json,
            headers=_headers(self._api_key),
            timeout=self._timeout,
        )
        return _parse(res)

    def summary(self) -> Summary:
        return self._request("GET", "/api/summary")

    def generation(self, n: int) -> GenerationDetail:
        return self._request("GET", f"/api/generations/{_gen(n)}")

    def trial(self, n: int) -> Trial:
        return self._request("GET", f"/api/trials/{_gen(n)}")

    def latest_trial(self) -> Trial:
        """404 ApiError until a generation has died."""
        return self._request("GET", "/api/trials/latest")

    def genome(self) -> Genome:
        return self._request("GET", "/api/genome")

    def instincts(self) -> list[Instinct]:
        return self.genome()["instincts"]

    def evidence(self) -> Evidence:
        return self._request("GET", "/api/evidence")

    def health(self) -> Health:
        return self._request("GET", "/healthz")

    def ask(self, gen: int, question: str) -> AskAnswer:
        """Only dead generations can be asked (400 "not_dead"); 10 a minute per IP (429)."""
        return self._request(
            "POST", f"/api/generations/{_gen(gen)}/ask", json={"question": question}
        )

    def events(self, *, since: int = 0, interval: float = 5.0) -> Iterator[CourthouseEvent]:
        """Follow ``GET /api/events`` by polling.

        The Courthouse serves it as a JSON list (newest 50, ``?since=<id>``), not as a stream.
        Yields each event once, oldest first, forever; break out of the loop to stop.
        """
        while True:
            rows: list[CourthouseEvent] = self._request("GET", f"/api/events?since={int(since)}")
            for ev in sorted(rows, key=lambda e: e["id"]):
                since = max(since, ev["id"])
                yield ev
            time.sleep(interval)


class AsyncProbateClient:
    """Asynchronous client with the same methods as :class:`ProbateClient`."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        api_key: str | None = None,
        timeout: float | None = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._owns = http_client is None
        self._http = http_client or httpx.AsyncClient()

    async def __aenter__(self) -> AsyncProbateClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns:
            await self._http.aclose()

    async def _request(self, method: str, path: str, *, json: Any = None) -> Any:
        res = await self._http.request(
            method,
            self.base_url + path,
            json=json,
            headers=_headers(self._api_key),
            timeout=self._timeout,
        )
        return _parse(res)

    async def summary(self) -> Summary:
        return await self._request("GET", "/api/summary")

    async def generation(self, n: int) -> GenerationDetail:
        return await self._request("GET", f"/api/generations/{_gen(n)}")

    async def trial(self, n: int) -> Trial:
        return await self._request("GET", f"/api/trials/{_gen(n)}")

    async def latest_trial(self) -> Trial:
        return await self._request("GET", "/api/trials/latest")

    async def genome(self) -> Genome:
        return await self._request("GET", "/api/genome")

    async def instincts(self) -> list[Instinct]:
        return (await self.genome())["instincts"]

    async def evidence(self) -> Evidence:
        return await self._request("GET", "/api/evidence")

    async def health(self) -> Health:
        return await self._request("GET", "/healthz")

    async def ask(self, gen: int, question: str) -> AskAnswer:
        return await self._request(
            "POST", f"/api/generations/{_gen(gen)}/ask", json={"question": question}
        )

    async def events(
        self, *, since: int = 0, interval: float = 5.0
    ) -> AsyncIterator[CourthouseEvent]:
        """Async version of :meth:`ProbateClient.events` (polls; break or cancel to stop)."""
        while True:
            rows: list[CourthouseEvent] = await self._request(
                "GET", f"/api/events?since={int(since)}"
            )
            for ev in sorted(rows, key=lambda e: e["id"]):
                since = max(since, ev["id"])
                yield ev
            await asyncio.sleep(interval)
