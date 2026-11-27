"""AgentMail's daily send limit, counted so a generation is never born into an empty inbox.

The real run on 26 Nov 2026 hit the plan's 100 sends a day after generation 16: generations 17
and 18 lived and died with no test emails, and their lives measured nothing. Every send that
goes through AgentMail is counted here, per UTC day, and the clock waits for the next day
rather than start a life the suite can't reach. Mail from the owner's own domain is routed
through Cloudflare and is not counted.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

PREFIX = "agentmail_sent:"


def day(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%d")


class MailQuota:
    def __init__(self, store: Any, limit: int, reserve: int) -> None:
        self.store = store
        self.limit = max(int(limit), 0)  # 0 means no limit is enforced
        self.reserve = max(int(reserve), 0)  # kept back for owner digests and judge mail

    def used(self, now: datetime | None = None) -> int:
        return int(self.store.get_setting(PREFIX + day(now), "0") or 0)

    def record(self, n: int = 1, now: datetime | None = None) -> None:
        with self.store.lock:
            self.store.set_setting(PREFIX + day(now), str(self.used(now) + n))

    def left(self, now: datetime | None = None) -> int | None:
        if not self.limit:
            return None
        return max(self.limit - self.used(now), 0)

    def room_for(self, sends: int, now: datetime | None = None) -> bool:
        left = self.left(now)
        return left is None or left >= sends + self.reserve

    def wrap(self, mail: Any) -> Any:
        """Count every send `mail` makes through AgentMail. Routed senders are not counted."""
        if isinstance(mail, _Counted):
            return mail
        return _Counted(mail, self)


class _Counted:
    def __init__(self, inner: Any, quota: MailQuota) -> None:
        self._inner = inner
        self._quota = quota
        # Read the routes without touching the adapter's own attributes (fakes may refuse that).
        routes = getattr(inner, "__dict__", {}).get("routes", {})
        self._routed = {a.lower() for a in routes}

    def send(self, from_inbox: str, *a: Any, **kw: Any) -> str:
        mid = self._inner.send(from_inbox, *a, **kw)
        if from_inbox.lower() not in self._routed:
            self._quota.record()
        return mid

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
