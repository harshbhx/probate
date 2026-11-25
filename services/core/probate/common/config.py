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
    # Harsh's own address. The suite's "from Harsh" emails are sent from it through
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
    brain: str = field(default_factory=lambda: _env("PROBATE_BRAIN", "ollama:gpt-oss:120b"))
    budget_usd: float = field(default_factory=lambda: float(_env("PROBATE_BUDGET_USD", "20")))
    web_dist: Path = field(
        default_factory=lambda: Path(
            _env("PROBATE_WEB_DIST", str(REPO_ROOT / "apps" / "web" / "dist"))
        )
    )

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
        yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else [{"name": "Ada", "pronoun": "she"}]
    )


settings = Settings()
