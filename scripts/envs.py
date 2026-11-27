"""Named run environments (config/environments.yaml), shared by deploy.py and courthouse.py."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "environments.yaml"
DATA = ROOT / ".data"
LEGACY_SPRITE = "probate-courthouse"


@dataclass
class Environment:
    name: str
    sprite: str
    scoring_rules: str = "v2"
    read_only: bool = False
    run_label_prefix: str = ""
    description: str = ""
    settings: dict[str, str] = field(default_factory=dict)
    overridable: list[str] = field(default_factory=list)
    settings_pin: dict[str, str | int] = field(default_factory=dict)

    def pin_summary(self) -> str:
        """The pin as one line, for run-logs/branches.txt and the dataset record."""
        return " ".join(f"{k}={v}".replace(" ", "_") for k, v in self.settings_pin.items())

    @property
    def url_file(self) -> Path:
        # One file per environment, so staging never overwrites production's address.
        return DATA / f"courthouse-url-{self.name}.txt"

    def sprite_settings(self, shell: dict[str, str] | None = None) -> dict[str, str]:
        """What is written to the Sprite's .env on top of services/core/.env: the environment's own
        settings (with any allowed override from `shell`) plus its name and scoring rules."""
        shell = os.environ if shell is None else shell
        out = {k: str(v) for k, v in self.settings.items()}
        for key in self.overridable:
            if shell.get(key):
                out[key] = shell[key]
        if shell.get("PROBATE_BRANCH_NAME"):
            out["PROBATE_BRANCH_NAME"] = shell["PROBATE_BRANCH_NAME"]
        out["PROBATE_ENV_NAME"] = self.name
        out["PROBATE_SCORING_RULES"] = self.scoring_rules
        return out

    def banner(self) -> str:
        mode = "read only" if self.read_only else "writable"
        return (
            f"Environment: {self.name} (sprite {self.sprite}, scoring rules "
            f"{self.scoring_rules}, {mode})"
        )


def load_registry(path: Path = REGISTRY) -> dict[str, Environment]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, Environment] = {}
    for name, body in (raw.get("environments") or {}).items():
        out[name] = Environment(
            name=name,
            sprite=body["sprite"],
            scoring_rules=str(body.get("scoring_rules", "v2")),
            read_only=bool(body.get("read_only", False)),
            run_label_prefix=str(body.get("run_label_prefix", "")),
            description=str(body.get("description", "")),
            settings={k: str(v) for k, v in (body.get("settings") or {}).items()},
            overridable=list(body.get("overridable") or []),
            settings_pin=dict(body.get("settings_pin") or {}),
        )
    return out


def resolve(name: str | None, path: Path = REGISTRY) -> Environment | None:
    """None means no --env was given: the old defaults apply (sprite probate-courthouse)."""
    if not name:
        return None
    registry = load_registry(path)
    if name not in registry:
        sys.exit(f"Unknown environment {name!r}. Known: {', '.join(registry)}")
    return registry[name]


def announce(env: Environment | None) -> None:
    print(env.banner() if env else f"Environment: none (--env not given; sprite {LEGACY_SPRITE})")
