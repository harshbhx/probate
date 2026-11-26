"""One way to build the HTTP clients that talk to the connector gateway and the Sprites API.

Kept-alive connections are switched off: a server that closed an idle connection makes the next
request on it fail with "SSL: UNEXPECTED_EOF_WHILE_READING", which on a real Sprite stalled
births, deaths and the mail loop. A failed connect is retried.

A response that is cut off while it is being read (the same error, mid-request) is retried too,
but only for requests that are safe to repeat: GET, HEAD, PUT and DELETE always, and every method
for a client built with retry_all=True (the Sprites API, whose calls here are all repeatable).
A POST to a vendor, such as sending an email or asking a model, is not repeated.
"""

from __future__ import annotations

import time

import httpx

DROPPED = (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError, httpx.WriteError)
SAFE_METHODS = {"GET", "HEAD", "PUT", "DELETE"}


class RetryingClient(httpx.Client):
    def __init__(self, *args, retry_all: bool = False, attempts: int = 4, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.retry_all = retry_all
        self.attempts = attempts

    def send(self, request: httpx.Request, **kwargs) -> httpx.Response:
        repeatable = self.retry_all or request.method in SAFE_METHODS
        for attempt in range(self.attempts):
            try:
                return super().send(request, **kwargs)
            except DROPPED:
                if not repeatable or attempt == self.attempts - 1:
                    raise
                time.sleep(1 + attempt * 2)
        raise AssertionError("unreachable")  # pragma: no cover


def gateway_client(*, retry_all: bool = False, **kwargs) -> httpx.Client:
    kwargs.setdefault(
        "transport",
        httpx.HTTPTransport(retries=3, limits=httpx.Limits(max_keepalive_connections=0)),
    )
    return RetryingClient(retry_all=retry_all, **kwargs)
