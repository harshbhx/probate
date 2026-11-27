"""Pack the code a Sprite needs into one tar.gz.

The Courthouse ships its own code to every generation it creates, so a child always runs
exactly the Courthouse's version and nothing depends on the GitHub repo being reachable.
The deploy script uses the same bundle (plus the built website) to install the Courthouse.
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import yaml

from probate.common.config import REPO_ROOT

SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".data"}
SKIP_FILES = {".env"}
# Anything that looks like a secret, a key or local state never ships, whatever its exact name.
SKIP_SUFFIXES = (
    ".pem", ".key", ".p12", ".pfx", ".db", ".sqlite", ".sqlite3", ".log", ".bak", ".orig",
    ".swp", ".secret", ".secrets",
)  # fmt: skip
SKIP_PREFIXES = (".env", "id_rsa", "id_ed25519", "id_ecdsa", "credentials", "secret", ".netrc")
SKIP_CONTAINS = ("owner.yaml.",)  # owner.yaml.bak and friends

# Installs the bundle on a fresh Sprite (Ubuntu 25.10, PEP 668 managed Python).
INSTALL = (
    "set -e; mkdir -p app; tar xzf bundle.tgz -C app; rm bundle.tgz; "
    "python3 -m pip install --user --break-system-packages -q -e 'app/services/core' "
    "|| uv pip install --system --break-system-packages -q -e 'app/services/core'"
)


def _secret_name(name: str) -> bool:
    low = name.lower()
    return (
        name in SKIP_FILES
        or low.startswith(SKIP_PREFIXES)
        or low.endswith(SKIP_SUFFIXES)
        or any(c in low for c in SKIP_CONTAINS)
        or low.endswith("~")
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
        if redact_owner and child.name in ("owner.yaml", "owner.example.yaml"):
            continue
        tar.add(child, arcname=f"config/{child.name}", filter=_keep)
    if redact_owner:
        data = _redacted_owner(config)
        info = tarfile.TarInfo("config/owner.yaml")
        info.size = len(data)
        info.mtime = 0
        info.mode = 0o644
        info.uid = info.gid = 1000
        info.uname = info.gname = "sprite"
        tar.addfile(info, io.BytesIO(data))


def _keep(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    parts = Path(info.name).parts
    if any(p in SKIP_DIRS or p.endswith(".egg-info") for p in parts):
        return None
    if parts and _secret_name(parts[-1]):
        return None
    info.uid = info.gid = 1000
    info.uname = info.gname = "sprite"
    return info


def make_bundle(
    root: Path = REPO_ROOT, *, web: bool = False, tests: bool = False, redact_owner: bool = False
) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        core = root / "services" / "core"
        for child in sorted(core.iterdir()):
            if child.name == "tests" and not tests:
                continue
            tar.add(child, arcname=f"services/core/{child.name}", filter=_keep)
        _add_config(tar, root / "config", redact_owner)
        dist = root / "apps" / "web" / "dist"
        if web:
            if not (dist / "index.html").exists():
                raise FileNotFoundError("apps/web/dist is missing. Run `npm run build` first.")
            tar.add(dist, arcname="apps/web/dist", filter=_keep)
    return buf.getvalue()
