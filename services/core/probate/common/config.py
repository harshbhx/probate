"""Runtime settings, read from the environment (see services/core/.env.example)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from probate.common.models import OwnerProfile

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_DIR = Path(os.environ.get("PROBATE_CONFIG_DIR", REPO_ROOT / "config"))


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass
class Settings:
    fake: bool = field(default_factory=lambda: _env("PROBATE_FAKE", "1") == "1")
    data_dir: Path = field(
        default_factory=lambda: Path(_env("PROBATE_DATA_DIR", str(REPO_ROOT / ".data")))
    )
    sprites_token: str = field(default_factory=lambda: _env("PROBATE_SPRITES_TOKEN"))
    admin_token: str = field(default_factory=lambda: _env("PROBATE_ADMIN_TOKEN", "dev-admin"))
    connections: dict = field(
        default_factory=lambda: json.loads(_env("PROBATE_CONNECTIONS", "{}") or "{}")
    )
    lifespan_seconds: int = field(
        default_factory=lambda: int(_env("PROBATE_LIFESPAN_SECONDS", "600"))
    )
    gap_seconds: int = field(default_factory=lambda: int(_env("PROBATE_GAP_SECONDS", "60")))
    suite_per_life: int = field(default_factory=lambda: int(_env("PROBATE_SUITE_PER_LIFE", "8")))
    repo_url: str = field(
        default_factory=lambda: _env("PROBATE_REPO_URL", "https://github.com/OWNER/probate")
    )
    family_inbox: str = field(
        default_factory=lambda: _env("PROBATE_FAMILY_INBOX", "probate-family@agentmail.to")
    )
    # The owner's own address. The suite's "from the owner" emails are sent from it through
    # Cloudflare Email Service, so AgentMail only needs three inboxes.
    owner_sender: str = field(
        default_factory=lambda: _env("PROBATE_OWNER_SENDER", "harsh@dualmindlab.tech")
    )
    cf_account_id: str = field(default_factory=lambda: _env("PROBATE_CF_ACCOUNT_ID"))
    friend_inbox: str = field(
        default_factory=lambda: _env("PROBATE_FRIEND_INBOX", "probate-friend@agentmail.to")
    )
    stranger_inbox: str = field(
        default_factory=lambda: _env("PROBATE_STRANGER_INBOX", "probate-stranger@agentmail.to")
    )
    # Which route reaches Jev: "typesafe" (the TypeSafe connector) or "cloudflare" (the model
    # `typesafe/jev` on Workers AI through the cloudflare connector, billed by Cloudflare).
    jev_provider: str = field(default_factory=lambda: _env("PROBATE_JEV", "typesafe").lower())
    brain: str = field(default_factory=lambda: _env("PROBATE_BRAIN", "ollama:gpt-oss:120b"))
    # Tried in order when the brain fails, e.g. "groq:openai/gpt-oss-120b,anthropic:claude-haiku-5-5".
    # VERIFY in spike S8: model names available on each account.
    brain_fallbacks: list[str] = field(
        default_factory=lambda: [
            b.strip()
            for b in _env("PROBATE_BRAIN_FALLBACKS", "anthropic:claude-haiku-5-5").split(",")
            if b.strip()
        ]
    )
    budget_usd: float = field(default_factory=lambda: float(_env("PROBATE_BUDGET_USD", "20")))
    # "continuous" (default): the clock free-runs and a new life starts as soon as one ends.
    # "on_demand": nothing runs until a visitor asks for one short demo life (docs/13-RUNBOOK.md).
    mode: str = field(default_factory=lambda: _env("PROBATE_MODE", "continuous").strip().lower())
    demo_lifespan_seconds: int = field(
        default_factory=lambda: int(_env("PROBATE_DEMO_LIFESPAN_SECONDS", "120"))
    )
    demo_suite_per_life: int = field(
        default_factory=lambda: int(_env("PROBATE_DEMO_SUITE_PER_LIFE", "6"))
    )
    demo_cooldown_seconds: int = field(
        default_factory=lambda: int(_env("PROBATE_DEMO_COOLDOWN_SECONDS", "120"))
    )
    demo_ip_per_hour: int = field(
        default_factory=lambda: int(_env("PROBATE_DEMO_IP_PER_HOUR", "3"))
    )
    demo_max_per_day: int = field(
        default_factory=lambda: int(_env("PROBATE_DEMO_MAX_PER_DAY", "30"))
    )
    demo_daily_budget_usd: float = field(
        default_factory=lambda: float(_env("PROBATE_DEMO_DAILY_BUDGET_USD", "2"))
    )
    # How long past its death time a demo life may run (the trial included) before it is cut off.
    demo_hard_timeout_extra: int = field(
        default_factory=lambda: int(_env("PROBATE_DEMO_HARD_TIMEOUT_EXTRA_SECONDS", "240"))
    )
    # A real birth spends time creating the Sprite and installing code before the life starts.
    demo_birth_allowance: int = field(
        default_factory=lambda: int(_env("PROBATE_DEMO_BIRTH_ALLOWANCE_SECONDS", "120"))
    )
    # Judge key: one shared secret that lets a judge PLAY (start a life, attack the family) while the
    # read-only pages stay open. It is not an admin credential (docs/13-RUNBOOK.md section 6).
    judge_key: str = field(default_factory=lambda: _env("PROBATE_JUDGE_KEY"))
    # Shared secret with the Cloudflare edge Worker (docs/EDGE.md). Unset: nothing changes. Set: a
    # request carrying a matching X-Probate-Edge header has its real client address taken from
    # X-Probate-Client-IP. A value under 16 characters is ignored.
    edge_token: str = field(default_factory=lambda: _env("PROBATE_EDGE_TOKEN").strip())
    require_key_for_play_env: str = field(
        default_factory=lambda: _env("PROBATE_REQUIRE_KEY_FOR_PLAY").strip()
    )
    judge_lives_per_hour: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_LIVES_PER_HOUR", "6"))
    )
    judge_daily_budget_usd: float = field(
        default_factory=lambda: float(_env("PROBATE_JUDGE_DAILY_BUDGET_USD", "5"))
    )
    judge_attacks_per_hour: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_ATTACKS_PER_HOUR", "60"))
    )
    judge_attacks_per_ip_minute: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_ATTACKS_PER_IP_MINUTE", "6"))
    )
    judge_bad_keys_per_ip: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_BAD_KEYS_PER_IP", "8"))
    )
    # Judge mailroom (POST /api/judge/mail): real mail to the family inbox, as the Friend or the Stranger.
    judge_mail_per_ip_minute: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_MAIL_PER_IP_MINUTE", "2"))
    )
    judge_mail_per_ip_hour: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_MAIL_PER_IP_HOUR", "10"))
    )
    judge_mail_per_hour: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_MAIL_PER_HOUR", "30"))
    )
    judge_mail_per_day: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_MAIL_PER_DAY", "100"))
    )
    judge_mail_max_pending: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_MAIL_MAX_PENDING", "4"))
    )
    judge_mail_owner_digests_per_day: int = field(
        default_factory=lambda: int(_env("PROBATE_JUDGE_MAIL_OWNER_DIGESTS_PER_DAY", "3"))
    )
    # Outgoing webhooks (docs/WEBHOOKS.md). Subscriptions are operator-only.
    webhook_urls: list[str] = field(
        default_factory=lambda: [
            u.strip() for u in _env("PROBATE_WEBHOOK_URLS").split(",") if u.strip()
        ]
    )
    webhook_secret: str = field(default_factory=lambda: _env("PROBATE_WEBHOOK_SECRET"))
    webhook_allow_insecure: bool = field(
        default_factory=lambda: _env("PROBATE_WEBHOOK_ALLOW_INSECURE") == "1"
    )
    webhook_ports: list[int] = field(
        default_factory=lambda: [
            int(p) for p in _env("PROBATE_WEBHOOK_PORTS", "443").split(",") if p.strip()
        ]
    )
    webhook_max_endpoints: int = field(
        default_factory=lambda: int(_env("PROBATE_WEBHOOK_MAX_ENDPOINTS", "10"))
    )
    webhook_max_failures: int = field(
        default_factory=lambda: int(_env("PROBATE_WEBHOOK_MAX_FAILURES", "10"))
    )
    # Public origin of the website, used for links inside events (optional).
    public_url: str = field(default_factory=lambda: _env("PROBATE_PUBLIC_URL").rstrip("/"))
    web_dist: Path = field(
        default_factory=lambda: Path(
            _env("PROBATE_WEB_DIST", str(REPO_ROOT / "apps" / "web" / "dist"))
        )
    )

    def __post_init__(self) -> None:
        if self.on_demand:
            # Demo lives are short and small; the free-running clock's settings don't apply.
            self.lifespan_seconds = self.demo_lifespan_seconds
            self.suite_per_life = self.demo_suite_per_life
            self.gap_seconds = 0

    @property
    def require_key_for_play(self) -> bool:
        """Default on for a real on-demand Courthouse; PROBATE_REQUIRE_KEY_FOR_PLAY=0/1 overrides."""
        if self.require_key_for_play_env:
            return self.require_key_for_play_env == "1"
        return self.on_demand and not self.fake

    @property
    def on_demand(self) -> bool:
        return self.mode == "on_demand"

    def gateway(self, provider: str) -> str:
        conn = self.connections.get(provider, "")
        return f"https://api.sprites.dev/v1/gateway/{provider}/{conn}"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "probate.db"


def load_owner() -> OwnerProfile:
    for name in ("owner.yaml", "owner.example.yaml"):
        path = CONFIG_DIR / name
        if path.exists():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return OwnerProfile(**(raw.get("owner") or {}))
    return OwnerProfile()


def load_names() -> list[dict]:
    path = CONFIG_DIR / "names.yaml"
    return (
        yaml.safe_load(path.read_text(encoding="utf-8"))
        if path.exists()
        else [{"name": "Ada", "pronoun": "she"}]
    )


settings = Settings()
