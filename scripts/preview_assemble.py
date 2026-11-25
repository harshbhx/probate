"""Combine the built live site with its API snapshot into one deployable folder.

    python scripts/preview_assemble.py --dist apps/web/dist --snapshot .preview/snapshot --out .preview/web

Copies the Vite build, adds the snapshot's api/ folder, and checks the result is servable:
index.html exists and api/summary.json parses and lists generations.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dist", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    dist, snap, out = Path(a.dist), Path(a.snapshot), Path(a.out)

    if not (dist / "index.html").is_file():
        sys.exit(f"{dist}/index.html is missing; build the web app first.")
    if not (snap / "api" / "summary.json").is_file():
        sys.exit(f"{snap}/api/summary.json is missing; run scripts/preview_snapshot.py first.")

    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(dist, out)
    shutil.copytree(snap / "api", out / "api")

    summary = json.loads((out / "api" / "summary.json").read_text(encoding="utf-8"))
    gens = summary.get("generations") or []
    if not gens:
        sys.exit("api/summary.json lists no generations.")
    missing = [g["gen"] for g in gens if not (out / "api" / "generations" / f"{g['gen']}.json").is_file()]
    if missing:
        sys.exit(f"Snapshot is missing generation files for: {missing}")
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"assembled {out}: {files} files, {len(gens)} generations")


if __name__ == "__main__":
    main()
