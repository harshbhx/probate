"""Webhook signatures: `X-Probate-Signature: t=<unix>,v1=<hex hmac-sha256 of "t.body">`."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

DEFAULT_TOLERANCE = 300  # seconds; the recommended replay window for receivers


def new_secret() -> str:
    return "whsec_" + secrets.token_urlsafe(32)


def _mac(secret: str, t: int, body: bytes) -> str:
    return hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()


def sign(secret: str, body: bytes, t: int | None = None) -> str:
    t = int(time.time()) if t is None else int(t)
    return f"t={t},v1={_mac(secret, t, body)}"


def verify(
    secret: str,
    header: str,
    body: bytes,
    *,
    tolerance: int = DEFAULT_TOLERANCE,
    now: float | None = None,
) -> bool:
    """Constant-time check of a signature header, including the replay window."""
    try:
        fields = dict(p.split("=", 1) for p in header.split(","))
        t = int(fields["t"])
        given = fields["v1"]
    except (KeyError, ValueError, AttributeError):
        return False
    if abs((time.time() if now is None else now) - t) > tolerance:
        return False
    return hmac.compare_digest(_mac(secret, t, body), given)
