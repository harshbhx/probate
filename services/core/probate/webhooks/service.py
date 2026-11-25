"""Outgoing webhooks: endpoints, a persisted queue, signed delivery with bounded retries.

Design constraints (docs/WEBHOOKS.md):
- `emit()` only writes rows; it never touches the network and never raises into the caller.
- Delivery runs in a short-lived worker thread started by `kick()`. There is no loop that runs
  while the Courthouse is idle: the queue is drained on startup, after each emit, on every life
  tick and at the end of a life. A retry that falls due while everything sleeps waits for the
  next wake.
- Every attempt of one delivery sends the same body, event id and `X-Probate-Delivery` id.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from probate.common.config import Settings
from probate.courthouse.store import Store
from probate.webhooks import events, signing
from probate.webhooks.guard import (
    Resolver,
    WebhookURLError,
    resolve_public,
    system_resolver,
    validate_url,
)
from probate.webhooks.transport import HttpTransport, TransportError

log = logging.getLogger("probate.webhooks")

TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 4096
BACKOFF_SECONDS = (60, 300, 1800)  # after attempt 1, 2, 3; then give up (4 attempts in all)
JITTER = 0.2  # each delay is multiplied by 1 +/- 20%
EXPIRE_SECONDS = 6 * 3600  # a still-pending delivery this old is dropped
KEEP_DELIVERIES = 200  # per endpoint
BATCH = 50
ERROR_EXCERPT = 160


class WebhookError(Exception):
    """An operator mistake (bad URL, too many endpoints...). The message is safe to show."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if ts is None else ts, UTC).isoformat()


def _public(row: sqlite3.Row) -> dict:
    """An endpoint as the admin API shows it. The secret is never part of this."""
    ev = row["events"]
    return {
        "id": row["id"],
        "url": row["url"],
        "events": "*" if ev == "*" else json.loads(ev),
        "description": row["description"],
        "source": row["source"],
        "enabled": bool(row["enabled"]),
        "disabled_reason": row["disabled_reason"],
        "consecutive_failures": row["consecutive_failures"],
        "last_success_at": row["last_success_at"],
        "last_failure_at": row["last_failure_at"],
        "created_at": row["created_at"],
    }


class Webhooks:
    def __init__(
        self,
        store: Store,
        cfg: Settings,
        *,
        transport: HttpTransport | None = None,
        resolver: Resolver = system_resolver,
        clock: Callable[[], float] = time.time,
        rng: Callable[[], float] = random.random,
        autorun: bool = True,
    ) -> None:
        self.store = store
        self.cfg = cfg
        self.transport = transport or HttpTransport()
        self.resolver = resolver
        self.clock = clock
        self.rng = rng
        self.autorun = autorun  # tests call process_due() by hand
        self._busy = threading.Lock()  # one drain at a time
        self._write = threading.RLock()
        self.thread: threading.Thread | None = None

    # ------------------------------------------------------------------ endpoints
    def _check_url(self, url: str, resolve: bool) -> None:
        try:
            target = validate_url(
                url,
                allow_insecure=self.cfg.webhook_allow_insecure,
                allowed_ports=self.cfg.webhook_ports,
            )
            if resolve:
                resolve_public(
                    target, allow_insecure=self.cfg.webhook_allow_insecure, resolver=self.resolver
                )
        except WebhookURLError as exc:
            raise WebhookError(str(exc)) from exc

    @staticmethod
    def _norm_events(names: list[str] | None) -> str:
        if names is None or names == ["*"]:
            return "*"
        known = set(events.event_names())
        bad = [n for n in names if n not in known]
        if bad or not names:
            raise WebhookError(
                f"unknown or empty event list; choose from {sorted(known)} or omit for all"
            )
        return json.dumps(sorted(set(names)))

    def create_endpoint(
        self, url: str, names: list[str] | None = None, description: str = "", source: str = "admin"
    ) -> tuple[dict, str]:
        """Add an endpoint. Returns (public view, secret). The secret is only ever returned here."""
        self._check_url(url, resolve=True)
        evs = self._norm_events(names)
        with self._write:
            count = self.store.one("SELECT COUNT(*) AS n FROM webhook_endpoints")["n"]
            if count >= self.cfg.webhook_max_endpoints:
                raise WebhookError(
                    f"at most {self.cfg.webhook_max_endpoints} endpoints are allowed", 409
                )
            secret = signing.new_secret()
            eid = "we_" + uuid.uuid4().hex[:16]
            self.store.x(
                "INSERT INTO webhook_endpoints(id,url,secret,events,description,source,created_at)"
                " VALUES(?,?,?,?,?,?,?)",
                eid,
                url,
                secret,
                evs,
                description[:200],
                source,
                _iso(self.clock()),
            )
        return self.endpoint(eid), secret

    def endpoint(self, eid: str) -> dict | None:
        row = self.store.one("SELECT * FROM webhook_endpoints WHERE id=?", eid)
        return _public(row) if row else None

    def list_endpoints(self) -> list[dict]:
        return [
            _public(r) for r in self.store.q("SELECT * FROM webhook_endpoints ORDER BY created_at")
        ]

    def delete_endpoint(self, eid: str) -> bool:
        with self._write:
            row = self.store.one("SELECT source FROM webhook_endpoints WHERE id=?", eid)
            if not row:
                return False
            if row["source"] == "env":
                raise WebhookError(
                    "this endpoint comes from PROBATE_WEBHOOK_URLS; remove it there", 409
                )
            self.store.x("DELETE FROM webhook_deliveries WHERE endpoint_id=?", eid)
            self.store.x("DELETE FROM webhook_endpoints WHERE id=?", eid)
            self._prune_events()
        return True

    def set_enabled(self, eid: str, enabled: bool) -> dict | None:
        with self._write:
            if not self.store.one("SELECT 1 FROM webhook_endpoints WHERE id=?", eid):
                return None
            if enabled:
                self.store.x(
                    "UPDATE webhook_endpoints SET enabled=1, disabled_reason=NULL,"
                    " consecutive_failures=0 WHERE id=?",
                    eid,
                )
            else:
                self.store.x(
                    "UPDATE webhook_endpoints SET enabled=0, disabled_reason=? WHERE id=?",
                    "Disabled by the operator.",
                    eid,
                )
        return self.endpoint(eid)

    def deliveries(self, eid: str, limit: int = 50) -> list[dict] | None:
        if not self.store.one("SELECT 1 FROM webhook_endpoints WHERE id=?", eid):
            return None
        rows = self.store.q(
            "SELECT * FROM webhook_deliveries WHERE endpoint_id=? ORDER BY created_at DESC, rowid DESC"
            " LIMIT ?",
            eid,
            max(1, min(limit, KEEP_DELIVERIES)),
        )
        return [
            {
                "id": r["id"],
                "event_id": r["event_id"],
                "event_type": r["event_type"],
                "status": r["status"],
                "attempts": r["attempts"],
                "next_attempt_at": _iso(r["next_attempt_at"]) if r["status"] == "pending" else None,
                "last_status_code": r["last_status_code"],
                "last_error": r["last_error"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "delivered_at": r["delivered_at"],
            }
            for r in rows
        ]

    def sync_env(self) -> None:
        """Make PROBATE_WEBHOOK_URLS (with PROBATE_WEBHOOK_SECRET) match the env-sourced rows."""
        urls = self.cfg.webhook_urls
        if urls and not self.cfg.webhook_secret:
            log.warning("PROBATE_WEBHOOK_URLS is set but PROBATE_WEBHOOK_SECRET is not; ignored")
            urls = []
        have = {
            r["url"]: r for r in self.store.q("SELECT * FROM webhook_endpoints WHERE source='env'")
        }
        with self._write:
            for url in urls:
                try:
                    self._check_url(url, resolve=False)
                except WebhookError as exc:
                    log.warning("env webhook skipped (%s)", exc)
                    continue
                if url in have:
                    self.store.x(
                        "UPDATE webhook_endpoints SET secret=? WHERE id=?",
                        self.cfg.webhook_secret,
                        have[url]["id"],
                    )
                    continue
                eid = "we_" + hashlib.sha256(url.encode()).hexdigest()[:16]
                self.store.x(
                    "INSERT OR IGNORE INTO webhook_endpoints(id,url,secret,events,description,source,"
                    "created_at) VALUES(?,?,?,?,?,?,?)",
                    eid,
                    url,
                    self.cfg.webhook_secret,
                    "*",
                    "From PROBATE_WEBHOOK_URLS",
                    "env",
                    _iso(self.clock()),
                )
            for url, row in have.items():
                if url not in urls:
                    self.store.x("DELETE FROM webhook_deliveries WHERE endpoint_id=?", row["id"])
                    self.store.x("DELETE FROM webhook_endpoints WHERE id=?", row["id"])

    # ------------------------------------------------------------------ emitting
    def emit(
        self,
        type_: str,
        data: dict,
        *,
        dedupe: str | None = None,
        only_endpoint: str | None = None,
    ) -> str | None:
        """Queue an event for every enabled endpoint subscribed to it. Never raises, never blocks
        on the network. Returns the event id (None if the event could not be queued)."""
        try:
            ev = events.build(type_, data, dedupe=dedupe)
            body = json.dumps(ev, separators=(",", ":"), ensure_ascii=False)
            with self._write:
                self.store.x(
                    "INSERT OR IGNORE INTO webhook_events(id,type,created_at,payload) VALUES(?,?,?,?)",
                    ev["id"],
                    type_,
                    ev["created_at"],
                    body,
                )
                rows = self.store.q(
                    "SELECT id, events FROM webhook_endpoints WHERE enabled=1"
                    + (" AND id=?" if only_endpoint else ""),
                    *([only_endpoint] if only_endpoint else []),
                )
                now = self.clock()
                for r in rows:
                    wanted = r["events"]
                    if type_ != "ping" and wanted != "*" and type_ not in json.loads(wanted):
                        continue
                    self.store.x(
                        "INSERT OR IGNORE INTO webhook_deliveries(id,event_id,endpoint_id,event_type,"
                        "next_attempt_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                        "dlv_" + uuid.uuid4().hex[:24],
                        ev["id"],
                        r["id"],
                        type_,
                        now,
                        _iso(now),
                        _iso(now),
                    )
            self.kick()
            return ev["id"]
        except Exception:
            log.warning("could not queue webhook event %s", type_, exc_info=True)
            return None

    def ping(self, eid: str) -> tuple[str | None, str | None]:
        """Queue a `ping` for one endpoint. Returns (event id, delivery id)."""
        event_id = self.emit(
            "ping", {"message": "Probate Courthouse webhook test"}, only_endpoint=eid
        )
        row = event_id and self.store.one(
            "SELECT id FROM webhook_deliveries WHERE event_id=? AND endpoint_id=?", event_id, eid
        )
        return event_id, row["id"] if row else None

    # ------------------------------------------------------------------ delivering
    def kick(self) -> None:
        """Start a background drain of due deliveries, unless one is already running."""
        if not self.autorun or self._busy.locked():
            return
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._drain_quietly, name="webhooks", daemon=True)
        self.thread.start()

    def _drain_quietly(self) -> None:
        try:
            self.process_due()
        except Exception:
            log.exception("webhook delivery run failed")

    def process_due(self, now: float | None = None) -> int:
        """Attempt every delivery that is due. Returns the number of attempts made."""
        if not self._busy.acquire(blocking=False):
            return 0
        try:
            fixed = now
            now = self.clock() if fixed is None else fixed
            self._expire(now)
            made = 0
            for _ in range(20):  # bounded: a hostile endpoint can't pin the worker
                due = self.store.q(
                    "SELECT d.*, e.payload FROM webhook_deliveries d"
                    " JOIN webhook_events e ON e.id=d.event_id"
                    " JOIN webhook_endpoints p ON p.id=d.endpoint_id"
                    " WHERE d.status='pending' AND d.next_attempt_at<=? AND p.enabled=1"
                    " ORDER BY d.created_at, d.rowid LIMIT ?",
                    now,
                    BATCH,
                )
                if not due:
                    break
                for d in due:
                    self._attempt(d, now)
                    made += 1
                if fixed is None:
                    now = self.clock()
            self._prune_events()
            return made
        finally:
            self._busy.release()

    def _expire(self, now: float) -> None:
        self.store.x(
            "UPDATE webhook_deliveries SET status='failed', last_error='expired before delivery',"
            " updated_at=? WHERE status='pending' AND created_at<?",
            _iso(now),
            _iso(now - EXPIRE_SECONDS),
        )

    def _scrub(self, text: str, secret: str, url: str) -> str:
        for needle in (secret, url):
            if needle:
                text = text.replace(needle, "[redacted]")
        return " ".join(text.split())[:ERROR_EXCERPT]

    def _attempt(self, d: sqlite3.Row, now: float) -> None:
        ep = self.store.one("SELECT * FROM webhook_endpoints WHERE id=?", d["endpoint_id"])
        if ep is None:
            return
        body = d["payload"].encode()
        code: int | None = None
        error: str | None = None
        try:
            target = validate_url(
                ep["url"],
                allow_insecure=self.cfg.webhook_allow_insecure,
                allowed_ports=self.cfg.webhook_ports,
            )
            # Resolved here, at connect time; the connection uses this answer, not a new lookup.
            ip = resolve_public(
                target, allow_insecure=self.cfg.webhook_allow_insecure, resolver=self.resolver
            )[0]
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Probate-Courthouse-Webhooks/1",
                "X-Probate-Event": d["event_type"],
                "X-Probate-Event-Id": d["event_id"],
                "X-Probate-Delivery": d["id"],
                "X-Probate-Attempt": str(d["attempts"] + 1),
                "X-Probate-Signature": signing.sign(ep["secret"], body, int(now)),
            }
            code = self.transport.post(
                ip=ip,
                target=target,
                headers=headers,
                body=body,
                timeout=TIMEOUT_SECONDS,
                max_bytes=MAX_RESPONSE_BYTES,
            )
            if not 200 <= code < 300:
                error = f"HTTP {code}"
        except (WebhookURLError, TransportError) as exc:
            error = self._scrub(str(exc), ep["secret"], ep["url"])
        except Exception as exc:  # noqa: BLE001 - a delivery must never take the worker down
            error = f"unexpected error ({type(exc).__name__})"
        self._record(d, ep, now, code, error)

    def _record(self, d, ep, now: float, code: int | None, error: str | None) -> None:
        attempts = d["attempts"] + 1
        stamp = _iso(now)
        with self._write:
            if error is None:
                self.store.x(
                    "UPDATE webhook_deliveries SET status='succeeded', attempts=?, last_status_code=?,"
                    " last_error=NULL, updated_at=?, delivered_at=? WHERE id=?",
                    attempts,
                    code,
                    stamp,
                    stamp,
                    d["id"],
                )
                self.store.x(
                    "UPDATE webhook_endpoints SET consecutive_failures=0, last_success_at=? WHERE id=?",
                    stamp,
                    ep["id"],
                )
                return
            gave_up = attempts > len(BACKOFF_SECONDS)
            delay = 0.0
            if not gave_up:
                delay = BACKOFF_SECONDS[attempts - 1] * (1 + JITTER * (2 * self.rng() - 1))
            self.store.x(
                "UPDATE webhook_deliveries SET status=?, attempts=?, last_status_code=?, last_error=?,"
                " next_attempt_at=?, updated_at=? WHERE id=?",
                "failed" if gave_up else "pending",
                attempts,
                code,
                error,
                now + delay,
                stamp,
                d["id"],
            )
            fails = ep["consecutive_failures"] + 1
            self.store.x(
                "UPDATE webhook_endpoints SET consecutive_failures=?, last_failure_at=? WHERE id=?",
                fails,
                stamp,
                ep["id"],
            )
            if fails >= self.cfg.webhook_max_failures and ep["enabled"]:
                self.store.x(
                    "UPDATE webhook_endpoints SET enabled=0, disabled_reason=? WHERE id=?",
                    f"Disabled after {fails} consecutive failed attempts. Re-enable it with "
                    "PATCH /admin/webhooks/{id}.",
                    ep["id"],
                )
                self.store.x(
                    "UPDATE webhook_deliveries SET status='skipped', last_error='endpoint disabled',"
                    " updated_at=? WHERE endpoint_id=? AND status='pending'",
                    stamp,
                    ep["id"],
                )
                log.warning("webhook endpoint %s disabled after %s failures", ep["id"], fails)

    def _prune_events(self) -> None:
        """Capped retention: the newest KEEP_DELIVERIES finished rows per endpoint, and only the
        events something still points at."""
        with self._write:
            for r in self.store.q("SELECT id FROM webhook_endpoints"):
                self.store.x(
                    "DELETE FROM webhook_deliveries WHERE endpoint_id=? AND status!='pending' AND id NOT IN"
                    " (SELECT id FROM webhook_deliveries WHERE endpoint_id=?"
                    "  ORDER BY created_at DESC, rowid DESC LIMIT ?)",
                    r["id"],
                    r["id"],
                    KEEP_DELIVERIES,
                )
            self.store.x(
                "DELETE FROM webhook_events WHERE id NOT IN (SELECT event_id FROM webhook_deliveries)"
                " AND created_at < ?",
                _iso(self.clock() - 3600),
            )
