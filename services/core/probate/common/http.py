"""One way to build the HTTP clients that talk to the connector gateway and the Sprites API.

Kept-alive connections are switched off: a server that closed an idle connection makes the next
request on it fail with "SSL: UNEXPECTED_EOF_WHILE_READING", which on a real Sprite stalled
births, deaths and the mail loop. A failed connect is retried.
"""

from __future__ import annotations

import httpx


def gateway_client(**kwargs) -> httpx.Client:
    kwargs.setdefault(
        "transport",
        httpx.HTTPTransport(retries=3, limits=httpx.Limits(max_keepalive_connections=0)),
    )
    return httpx.Client(**kwargs)
