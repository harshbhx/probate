"""Pack the code a Sprite needs into one tar.gz.

The Courthouse ships its own code to every generation it creates, so a child always runs
exactly the Courthouse's version and nothing depends on the GitHub repo being reachable.
The deploy script uses the same bundle (plus the built website) to install the Courthouse.
"""

from __future__ import annotations

import io
import tarfile
from fnmatch import fnmatch
from pathlib import Path

import yaml

from probate.common.config import REPO_ROOT

# A strict allowlist: only what a generation (or the Courthouse) needs to run ships. Anything
# else in these folders, whatever its name (prod.env, token.txt, .npmrc, a dump, a key), stays
# behind, so a stray secret file cannot ride along.
SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".data"}
# services/core: the pyproject and the probate package (Python code, the SQL schema, the prompts
# and the suite fixtures; nothing else).
CORE_FILES = {"pyproject.toml"}
PACKAGE_DATA = ("courthouse/schema.sql", "suite/*.json", "prompts/*.md")  # as in pyproject.toml
TEST_SUFFIXES = {".py", ".json", ".md"}
# config/: the files the code reads, by exact name. owner.yaml is written redacted for a Sprite.
CONFIG_FILES = {
    "names.yaml", "pricing.yaml", "environments.yaml", "owner.yaml", "owner.example.yaml",
}  # fmt: skip
# apps/web/dist: built website assets only.
WEB_SUFFIXES = {
    ".html", ".js", ".mjs", ".css", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif",
    ".ico", ".woff", ".woff2", ".ttf", ".otf", ".webmanifest", ".mp3", ".ogg", ".wav",
}  # fmt: skip

# Installs the bundle on a fresh Sprite (Ubuntu 25.10, PEP 668 managed Python).
INSTALL = (
    "set -e; mkdir -p app; tar xzf bundle.tgz -C app; rm bundle.tgz; "
    "python3 -m pip install --user --break-system-packages -q -e 'app/services/core' "
    "|| uv pip install --system --break-system-packages -q -e 'app/services/core'"
)


def _redacted_owner(config: Path) -> bytes:
    """config/owner.yaml as a Sprite may see it: names and addresses, no payment destinations.
    The generation only classifies senders (owner or trusted contact); the court keeps the real list."""
    for name in ("owner.yaml", "owner.example.yaml"):
        path = config / name
        if path.exists():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            owner = dict(raw.get("owner") or {})
            owner["payment_destinations"] = []
            return yaml.safe_dump({"owner": owner}, sort_keys=False).encode()
    return b"owner: {}\n"


def _add_config(tar: tarfile.TarFile, config: Path, redact_owner: bool) -> None:
    for child in sorted(config.iterdir()):
        if child.name not in CONFIG_FILES or not child.is_file():
            continue
        if redact_owner and child.name in ("owner.yaml", "owner.example.yaml"):
            continue
        tar.add(child, arcname=f"config/{child.name}", filter=_owned_by_sprite)
    if redact_owner:
        data = _redacted_owner(config)
        info = tarfile.TarInfo("config/owner.yaml")
        info.size = len(data)
        info.mtime = 0
        info.mode = 0o644
        info.uid = info.gid = 1000
        info.uname = info.gname = "sprite"
        tar.addfile(info, io.BytesIO(data))


def _owned_by_sprite(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = info.gid = 1000
    info.uname = info.gname = "sprite"
    return info


def _walk(base: Path, suffixes: set[str], data: tuple[str, ...] = ()):
    """Regular files under `base` with an allowed suffix or matching a `data` pattern, skipping
    build and cache folders. Symlinks are never followed."""
    for path in sorted(base.rglob("*")):
        rel = path.relative_to(base)
        if any(p in SKIP_DIRS or p.endswith(".egg-info") for p in rel.parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() in suffixes or any(fnmatch(rel.as_posix(), d) for d in data):
            yield path, rel


def make_bundle(
    root: Path = REPO_ROOT, *, web: bool = False, tests: bool = False, redact_owner: bool = False
) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        core = root / "services" / "core"
        for name in sorted(CORE_FILES):
            if (core / name).is_file():
                tar.add(core / name, arcname=f"services/core/{name}", filter=_owned_by_sprite)
        for path, rel in _walk(core / "probate", {".py"}, PACKAGE_DATA):
            tar.add(
                path, arcname=f"services/core/probate/{rel.as_posix()}", filter=_owned_by_sprite
            )
        if tests and (core / "tests").is_dir():
            for path, rel in _walk(core / "tests", TEST_SUFFIXES):
                tar.add(
                    path, arcname=f"services/core/tests/{rel.as_posix()}", filter=_owned_by_sprite
                )
        _add_config(tar, root / "config", redact_owner)
        dist = root / "apps" / "web" / "dist"
        if web:
            if not (dist / "index.html").exists():
                raise FileNotFoundError("apps/web/dist is missing. Run `npm run build` first.")
            for path, rel in _walk(dist, WEB_SUFFIXES):
                tar.add(path, arcname=f"apps/web/dist/{rel.as_posix()}", filter=_owned_by_sprite)
    return buf.getvalue()
