"""The spending cap: estimate what the family costs and stop births once it reaches the cap.

Spend is an estimate built from `config/pricing.yaml`:

- each generation's life, charged at its death (hours alive x generation usage x Sprite rates),
  plus its own brain and gate calls, estimated from how many emails it handled;
- the Courthouse's own uptime, charged on every clock tick;
- per-call vendor costs for calls the Courthouse makes itself (trial, obituary, ancestor),
  counted by wrapping the adapters.

A living generation always finishes its life. The cap only stops the next birth.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from probate.common.config import REPO_ROOT, Settings

log = logging.getLogger("probate.budget")

SPENT = "budget_spent_usd"


@dataclass
class Pricing:
    cpu_hour: float = 0.0385
    memory_gb_hour: float = 0.021875
    generation_cpu: float = 0.5
    generation_gb: float = 1.0
    courthouse_cpu: float = 0.25
    courthouse_gb: float = 0.75
    per_call: dict[str, float] = field(
        default_factory=lambda: {"brain": 0.0, "jev": 0.0, "voice_per_1k_chars": 0.0}
    )

    @classmethod
    def load(cls, path: Path | None = None) -> Pricing:
        path = path or REPO_ROOT / "config" / "pricing.yaml"
        if not path.exists():
            return cls()
        d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        s = d.get("sprites", {})
        gen, ch = s.get("generation", {}), s.get("courthouse", {})
        p = cls()
        p.cpu_hour = float(s.get("cpu_hour_usd", p.cpu_hour))
        p.memory_gb_hour = float(s.get("memory_gb_hour_usd", p.memory_gb_hour))
        p.generation_cpu = float(gen.get("cpu", p.generation_cpu))
        p.generation_gb = float(gen.get("memory_gb", p.generation_gb))
        p.courthouse_cpu = float(ch.get("cpu", p.courthouse_cpu))
        p.courthouse_gb = float(ch.get("memory_gb", p.courthouse_gb))
        p.per_call.update({k: float(v) for k, v in (d.get("per_call_usd") or {}).items()})
        return p

    def generation_hour(self) -> float:
        return self.generation_cpu * self.cpu_hour + self.generation_gb * self.memory_gb_hour

    def courthouse_hour(self) -> float:
        return self.courthouse_cpu * self.cpu_hour + self.courthouse_gb * self.memory_gb_hour


class Budget:
    def __init__(self, cfg: Settings, store: Any, pricing: Pricing | None = None) -> None:
        self.cfg = cfg
        self.store = store
        self.pricing = pricing or Pricing.load()

    # --- reading -------------------------------------------------------------------------
    @property
    def limit(self) -> float:
        return self.cfg.budget_usd

    def spent(self) -> float:
        return float(self.store.get_setting(SPENT, "0") or 0)

    def exhausted(self) -> bool:
        return self.limit > 0 and self.spent() >= self.limit

    def breakdown(self) -> dict[str, float]:
        keys = ("generations", "courthouse", "brain", "jev", "voice")
        return {k: round(float(self.store.get_setting(f"budget:{k}", "0") or 0), 4) for k in keys}

    # --- charging ------------------------------------------------------------------------
    def charge(self, usd: float, what: str) -> None:
        if usd <= 0:
            return
        # Read-modify-write under the store's lock: threads must not lose each other's charges.
        with self.store.lock:
            self.store.set_setting(SPENT, f"{self.spent() + usd:.6f}")
            key = f"budget:{what}"
            prev = float(self.store.get_setting(key, "0") or 0)
            self.store.set_setting(key, f"{prev + usd:.6f}")
        if self.exhausted():
            log.warning("spending cap reached: %.2f of %.2f USD", self.spent(), self.limit)

    def charge_life(self, hours: float, emails: int) -> None:
        self.charge(max(hours, 0) * self.pricing.generation_hour(), "generations")
        # Each email costs the generation one gate check and one brain call on its own Sprite.
        self.charge(emails * self.pricing.per_call.get("brain", 0), "brain")
        self.charge(emails * self.pricing.per_call.get("jev", 0), "jev")

    def charge_courthouse(self, seconds: float) -> None:
        self.charge(max(seconds, 0) / 3600 * self.pricing.courthouse_hour(), "courthouse")

    # --- metering the Courthouse's own vendor calls --------------------------------------
    def meter(self, w: Any) -> Any:
        """Wrap the world's adapters so every billable call is charged. Free calls pass through."""
        per = self.pricing.per_call
        if per.get("brain"):
            w.llm = _Metered(w.llm, "complete", lambda *a, **k: self.charge(per["brain"], "brain"))
        if per.get("jev"):
            w.jev = _Metered(w.jev, "ask", lambda *a, **k: self.charge(per["jev"], "jev"))
        if per.get("voice_per_1k_chars"):

            def voice_cost(text: str = "", *_a: Any, **_k: Any) -> None:
                self.charge(len(text) / 1000 * per["voice_per_1k_chars"], "voice")

            w.voice = _Metered(w.voice, "speak", voice_cost)
        return w


class _Metered:
    """Forwards everything to the real adapter and charges after one named method succeeds."""

    def __init__(self, inner: Any, method: str, on_call: Any) -> None:
        self._inner, self._method, self._on_call = inner, method, on_call

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._inner, name)
        if name != self._method:
            return attr

        def wrapped(*a: Any, **k: Any) -> Any:
            out = attr(*a, **k)
            self._on_call(*a, **k)
            return out

        return wrapped
