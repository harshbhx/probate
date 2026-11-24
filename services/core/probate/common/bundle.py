"""Pack the code a Sprite needs into one tar.gz.

The Courthouse ships its own code to every generation it creates, so a child always runs
exactly the Courthouse's version and nothing depends on the GitHub repo being reachable.
The deploy script uses the same bundle (plus the built website) to install the Courthouse.
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

from probate.common.config import REPO_ROOT

SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".data"}
SKIP_FILES = {".env"}

# Installs the bundle on a fresh Sprite (Ubuntu 25.10, PEP 668 managed Python).
INSTALL = (
    "set -e; mkdir -p app; tar xzf bundle.tgz -C app; rm bundle.tgz; "
    "python3 -m pip install --user --break-system-packages -q -e 'app/services/core[vendors]' "
    "|| uv pip install --system --break-system-packages -q -e 'app/services/core[vendors]'"
)


def _keep(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    parts = Path(info.name).parts
    if any(p in SKIP_DIRS or p.endswith(".egg-info") for p in parts):
        return None
    if parts and parts[-1] in SKIP_FILES:
        return None
    info.uid = info.gid = 1000
    info.uname = info.gname = "sprite"
    return info


def make_bundle(root: Path = REPO_ROOT, *, web: bool = False, tests: bool = False) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        core = root / "services" / "core"
        for child in sorted(core.iterdir()):
            if child.name == "tests" and not tests:
                continue
            tar.add(child, arcname=f"services/core/{child.name}", filter=_keep)
        tar.add(root / "config", arcname="config", filter=_keep)
        dist = root / "apps" / "web" / "dist"
        if web:
            if not (dist / "index.html").exists():
                raise FileNotFoundError("apps/web/dist is missing. Run `npm run build` first.")
            tar.add(dist, arcname="apps/web/dist", filter=_keep)
    return buf.getvalue()
