"""The one place that opens a connection for a webhook."""

from __future__ import annotations

import time

import httpx

from probate.webhooks.guard import Target


class TransportError(Exception):
    """Delivery failed before an HTTP status came back. The message is safe to store."""


class HttpTransport:
    """POST to an address the guard already approved.

    The connection goes to the validated IP. The original name travels as the Host header and as
    TLS SNI (certificate checks are against the name, not the IP). Redirects are never followed,
    proxies from the environment are ignored, and at most `max_bytes` of the reply are read.
    """

    def post(
        self,
        *,
        ip: str,
        target: Target,
        headers: dict[str, str],
        body: bytes,
        timeout: float,
        max_bytes: int,
    ) -> int:
        host = f"[{ip}]" if ":" in ip else ip
        url = f"{target.scheme}://{host}:{target.port}{target.path}"
        hdrs = {**headers, "Host": target.host_header}
        ext = {"sni_hostname": target.host} if target.scheme == "https" else {}
        deadline = time.monotonic() + timeout
        try:
            with (
                httpx.Client(
                    timeout=httpx.Timeout(timeout),
                    follow_redirects=False,
                    trust_env=False,
                ) as client,
                client.stream("POST", url, content=body, headers=hdrs, extensions=ext) as resp,
            ):
                got = 0
                for chunk in resp.iter_raw():
                    got += len(chunk)
                    if got >= max_bytes or time.monotonic() > deadline:
                        break  # we never use the body; stop reading
                return resp.status_code
        except httpx.TimeoutException as exc:
            raise TransportError("timed out") from exc
        except httpx.HTTPError as exc:
            # Only the exception class: its text can echo the URL, which may hold a token.
            raise TransportError(f"connection failed ({type(exc).__name__})") from exc
