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
    sprite: str | None  # None: no Sprite (a simulation on this machine)
    scoring_rules: str = "v2"
    read_only: bool = False
    simulated: bool = False
    set_public_url: bool = False  # deploy also writes PROBATE_PUBLIC_URL into the Sprite's .env
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
        if self.simulated:
            return (
                f"Environment: {self.name} (SIMULATED, no Sprite, scoring rules "
                f"{self.scoring_rules})"
            )
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
            sprite=body.get("sprite") or None,
            scoring_rules=str(body.get("scoring_rules", "v2")),
            read_only=bool(body.get("read_only", False)),
            simulated=bool(body.get("simulated", False)),
            set_public_url=bool(body.get("set_public_url", False)),
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


GUARDED = ("PROBATE_BRAIN", "PROBATE_BRAIN_FALLBACKS", "PROBATE_JEV")


def _unquote(v: str) -> str:
    return v.strip().strip('"').strip("'")


def guard(
    extra: dict[str, str], env_file: dict[str, str], allow_change: bool = False
) -> tuple[dict[str, str], list[str]]:
    """An environment may not silently switch the brain, its fallbacks or the judge. If
    services/core/.env sets one of them to a different value, the .env value is kept (the key is
    dropped from `extra`) unless the operator passed --allow-brain-change. Returns the settings to
    apply and a line for each decision, for the operator to read."""
    out, notes = dict(extra), []
    for key in GUARDED:
        if key not in out:
            continue
        have = _unquote(env_file.get(key, ""))
        if not have or have == out[key]:
            continue
        if allow_change:
            notes.append(f"{key}: changed from the .env value to {out[key]} (--allow-brain-change)")
        else:
            notes.append(
                f"{key}: kept {have} from services/core/.env; the environment wants {out[key]} "
                "(pass --allow-brain-change to switch)"
            )
            del out[key]
    return out, notes


# What `deploy.py --check` prints. Never anything outside this list, so no secret can appear.
SHOWN = [
    ("brain", "PROBATE_BRAIN", "(code default)"),
    ("fallbacks", "PROBATE_BRAIN_FALLBACKS", "(code default)"),
    ("judge", "PROBATE_JEV", "(code default)"),
    ("tier", "PROBATE_SUITE_TIER", "base"),
    ("per life", "PROBATE_SUITE_PER_LIFE", "8"),
    ("hard per life", "PROBATE_HARD_PER_LIFE", "2"),
    ("links per mail", "PROBATE_LINKS_PER_MAIL", "1"),
    ("lifespan s", "PROBATE_LIFESPAN_SECONDS", "600"),
    ("mode", "PROBATE_MODE", "continuous"),
    ("starts paused", "PROBATE_START_PAUSED", "0"),
    ("distill", "PROBATE_DISTILL", "1"),
    ("hard offset", "PROBATE_HARD_OFFSET", "0"),
    ("v1 last gen", "PROBATE_V1_LAST_GEN", "0"),
    ("mail daily limit", "PROBATE_MAIL_DAILY_LIMIT", "100"),
    ("mail reserve", "PROBATE_MAIL_RESERVE", "6"),
]


def effective(env_file: dict[str, str], extra: dict[str, str]) -> list[str]:
    merged = {**{k: _unquote(v) for k, v in env_file.items()}, **extra}
    return [f"  {label}: {merged.get(key) or default}" for label, key, default in SHOWN]


def announce(env: Environment | None) -> None:
    print(env.banner() if env else f"Environment: none (--env not given; sprite {LEGACY_SPRITE})")


# --- deploy guards: what a redeploy must not do silently ------------------------------------
FLAGS = ("PROBATE_DISTILL", "PROBATE_CONTEST_EMAILS")

# (env key, field in /admin/status, how the value is compared)
RUNNING_KNOBS = [
    ("PROBATE_DISTILL", "distill", "flag"),
    ("PROBATE_HARD_OFFSET", "hard_offset", "int"),
    ("PROBATE_SUITE_TIER", "suite_tier", "text"),
    ("PROBATE_LIFESPAN_SECONDS", "lifespan_seconds", "int"),
]


def bad_flags(merged: dict[str, str]) -> list[str]:
    """Yes/no settings whose value is not clearly yes or no. The Courthouse refuses them at start
    (and `PROBATE_DISTILL=off` used to leave learning on), so a deploy must refuse them first."""
    from probate.common.config import parse_flag

    out = []
    for key in FLAGS:
        try:
            parse_flag(key, _unquote(merged.get(key, "")), True)
        except ValueError as exc:
            out.append(str(exc))
    return out


def replaces_other_run(
    summary: dict | None, env_name: str | None, branch: str, force: bool = False
) -> str | None:
    """A reason to refuse when the Sprite is running a different environment or branch than the one
    being deployed (`summary` is its /api/summary). None if it is the same run, unknown, or forced."""
    if force or not summary:
        return None
    live_env = summary.get("environment") or ""
    live_branch = summary.get("branch") or ""
    want_env = env_name or ""
    if live_env and live_env != want_env:
        return (
            f"the Sprite runs environment {live_env!r}, this deploy is {want_env or 'no --env'!r}"
        )
    # The branch can be renamed while running, so a deploy that names none is left alone.
    if branch and live_branch and live_branch != branch:
        return f"the Sprite runs branch {live_branch!r}, this deploy is {branch!r}"
    return None


def _norm(value: object, how: str) -> str:
    text = _unquote(str(value)) if value is not None else ""
    if how == "flag":
        from probate.common.config import parse_flag

        try:
            return "1" if parse_flag("", text, True) else "0"
        except ValueError:
            return text
    if how == "int":
        try:
            return str(int(text or 0))
        except ValueError:
            return text
    return text.lower()


def differing_knobs(running: dict | None, merged: dict[str, str]) -> list[str]:
    """One line for each knob this deploy would change on the running Sprite (never a secret;
    only the keys in RUNNING_KNOBS). `running` is the Sprite's /admin/status."""
    if not running:
        return []
    defaults = {
        "PROBATE_DISTILL": "1",
        "PROBATE_HARD_OFFSET": "0",
        "PROBATE_SUITE_TIER": "base",
        "PROBATE_LIFESPAN_SECONDS": "600",
    }
    out = []
    for key, field_, how in RUNNING_KNOBS:
        if field_ not in running:
            continue
        have = _norm(running[field_], "flag" if how == "flag" else how)
        want = _norm(merged.get(key) or defaults[key], how)
        if have != want:
            out.append(f"{key}: running {running[field_]!r}, this deploy writes {want!r}")
    return out
