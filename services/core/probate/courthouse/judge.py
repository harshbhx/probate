"""The judge key: one shared secret that lets a judge PLAY, never administer.

A judge needs it to start a life (`POST /api/lives`) and to attack the family (`POST /api/attacks`).
The public read-only pages never need it. It is a shared secret printed in the submission, so it
is deliberately weaker than the admin token: it can only start short, capped, budgeted lives and run
sandboxed trial previews, and the admin can switch it off instantly (`POST /admin/judge/disable`).

The key is read from `PROBATE_JUDGE_KEY`. It is compared in constant time, never logged and never
echoed back. Brute force is limited per visitor address.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from datetime import UTC, datetime

from probate.common.config import Settings
from probate.courthouse.store import Store

HEADER = "x-probate-key"
HOUR = 3600
MIN_KEY_LENGTH = 20
DEV_KEYS = {"", "dev-judge", "dev-admin", "changeme", "change-me", "judge", "secret", "password"}
BAD_KEY_WINDOW = 600
MAX_KEY_LENGTH = 256


def _digest(s: str) -> bytes:
    return hashlib.sha256(s.encode("utf-8", "replace")).digest()


def _ip_key(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:12]


class Judge:
    def __init__(self, cfg: Settings, store: Store) -> None:
        self.cfg = cfg
        self.store = store
        self.lock = threading.Lock()
        self._bad: dict[str, list[float]] = {}
        self._attacks: dict[str, list[float]] = {}

    # ---------------------------------------------------------------- configuration
    @property
    def configured(self) -> bool:
        """A usable key: set, not a dev default, long enough, and not the admin token."""
        k = self.cfg.judge_key
        return (
            k.strip().lower() not in DEV_KEYS
            and len(k) >= MIN_KEY_LENGTH
            and not hmac.compare_digest(_digest(k), _digest(self.cfg.admin_token))
        )

    @property
    def misconfigured(self) -> bool:
        """Play needs a key but the server has no usable one: refuse to run open by accident."""
        return self.cfg.require_key_for_play and not self.configured

    @property
    def disabled(self) -> bool:
        return self.store.get_setting("judge:disabled", "0") == "1"

    def set_disabled(self, value: bool) -> None:
        self.store.set_setting("judge:disabled", "1" if value else "0")

    # ---------------------------------------------------------------- checking a key
    def _throttled(self, ipk: str, now: float) -> bool:
        with self.lock:
            hits = [t for t in self._bad.get(ipk, []) if now - t < BAD_KEY_WINDOW]
            self._bad[ipk] = hits
            if len(self._bad) > 5000:  # bounded memory under a flood of addresses
                self._bad = {k: v for k, v in self._bad.items() if v}
            return 0 < self.cfg.judge_bad_keys_per_ip <= len(hits)

    def _fail(self, ipk: str, now: float) -> None:
        with self.lock:
            self._bad.setdefault(ipk, []).append(now)

    def check(self, provided: str | None, ip: str) -> str:
        """Returns ok | missing | invalid | disabled | throttled | unavailable."""
        if not provided:
            return "missing"
        now = time.time()
        ipk = _ip_key(ip)
        if self._throttled(ipk, now):
            return "throttled"
        if not self.configured:
            return "unavailable"
        # Equal-length digests keep the comparison independent of the guess and the real key.
        same = hmac.compare_digest(_digest(provided[:MAX_KEY_LENGTH]), _digest(self.cfg.judge_key))
        if not same or len(provided) > MAX_KEY_LENGTH:
            self._fail(ipk, now)
            return "invalid"
        return "disabled" if self.disabled else "ok"

    # ---------------------------------------------------------------- quota (its own, per key)
    def _day(self, now: datetime) -> dict:
        today = now.date().isoformat()
        d = json.loads(self.store.get_setting("judge:day", "{}") or "{}")
        if d.get("date") != today:
            d = {"date": today, "usd": 0.0, "lives": 0, "attacks": 0}
            self.store.set_setting("judge:day", json.dumps(d))
        return d

    def _life_times(self, now: datetime) -> list[float]:
        times = json.loads(self.store.get_setting("judge:lives", "[]") or "[]")
        return [t for t in times if t > now.timestamp() - HOUR]

    def lives_wait(self, now: datetime) -> int:
        """Seconds until another judge life is allowed by the hourly quota, or 0."""
        times = self._life_times(now)
        limit = self.cfg.judge_lives_per_hour
        if limit <= 0 or len(times) < limit:
            return 0
        return int(min(times) + HOUR - now.timestamp()) + 1

    def daily_block(self, now: datetime, est: float) -> bool:
        cap = self.cfg.judge_daily_budget_usd
        return cap > 0 and self._day(now)["usd"] + est > cap

    def record_life(self, now: datetime, est: float) -> None:
        d = self._day(now)
        d["usd"] = round(d["usd"] + est, 4)
        d["lives"] += 1
        self.store.set_setting("judge:day", json.dumps(d))
        times = [*self._life_times(now), now.timestamp()]
        self.store.set_setting("judge:lives", json.dumps(times))

    def record_attack(self, now: datetime, est: float) -> None:
        d = self._day(now)
        d["usd"] = round(d["usd"] + est, 4)
        d["attacks"] += 1
        self.store.set_setting("judge:day", json.dumps(d))

    def attack_limit(self, ip: str, now: float | None = None) -> int:
        """Seconds to wait if this attack would exceed the per-key or per-address rate, else 0
        (and the attack is counted)."""
        now = now or time.time()
        ipk = _ip_key(ip)
        with self.lock:
            key_hits = [t for t in self._attacks.get("*", []) if now - t < HOUR]
            ip_hits = [t for t in self._attacks.get(ipk, []) if now - t < 60]
            lim_key, lim_ip = self.cfg.judge_attacks_per_hour, self.cfg.judge_attacks_per_ip_minute
            if 0 < lim_key <= len(key_hits):
                return int(min(key_hits) + HOUR - now) + 1
            if 0 < lim_ip <= len(ip_hits):
                return int(min(ip_hits) + 60 - now) + 1
            self._attacks["*"] = [*key_hits, now]
            self._attacks[ipk] = [*ip_hits, now]
            return 0

    def status(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        d = self._day(now)
        times = self._life_times(now)
        lim = self.cfg.judge_lives_per_hour
        cap = self.cfg.judge_daily_budget_usd
        return {
            "valid": True,
            "lives": {
                "per_hour": lim,
                "used_this_hour": len(times),
                "remaining_this_hour": max(0, lim - len(times)) if lim > 0 else None,
                "next_available_in": self.lives_wait(now),
            },
            "budget": {
                "daily_cap_usd": cap,
                "used_today_usd": round(d["usd"], 2),
                "remaining_today_usd": round(max(0.0, cap - d["usd"]), 2) if cap > 0 else None,
            },
            "attacks": {"per_hour": self.cfg.judge_attacks_per_hour, "today": d["attacks"]},
        }
