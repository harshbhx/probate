"""Freeze the live family into static JSON for a preview deploy.

    python scripts/preview_snapshot.py --out .preview/snapshot

Simulates a family with stand-in models (PROBATE_FAKE=1, no network, no secrets), starts the
Courthouse on a free local port, saves every read-only /api route as <route>.json, and stops
the server. The result is what the live site reads when its api.ts is patched for a preview
(see scripts/preview_patch_api.py). Needs `pip install -e services/core` first.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "services" / "core"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def fetch(base: str, route: str):
    with urllib.request.urlopen(base + route, timeout=20) as r:
        return json.load(r)


def save(out: Path, route: str, data) -> None:
    f = out / (route.lstrip("/") + ".json")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data), encoding="utf-8")


def wait_healthy(base: str, proc: subprocess.Popen, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            sys.exit(f"The Courthouse exited early (code {proc.returncode}).")
        try:
            fetch(base, "/healthz")
            return
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(0.5)
    sys.exit("The Courthouse did not answer /healthz in time.")


def dump(base: str, out: Path) -> int:
    """Save every GET /api/* route. Core routes must work; per-generation ones may 404."""
    summary = fetch(base, "/api/summary")
    save(out, "/api/summary", summary)
    for route in ("/api/evidence", "/api/genome", "/api/events"):
        save(out, route, fetch(base, route))
    gens = sorted({g["gen"] for g in summary.get("generations", [])})
    if not gens:
        sys.exit("The simulation produced no generations; nothing to preview.")
    for n in gens:
        for route in (f"/api/generations/{n}", f"/api/trials/{n}"):
            try:
                save(out, route, fetch(base, route))
            except urllib.error.HTTPError as e:
                print(f"skip {route}: HTTP {e.code}")
    try:
        save(out, "/api/trials/latest", fetch(base, "/api/trials/latest"))
    except urllib.error.HTTPError as e:
        print(f"skip /api/trials/latest: HTTP {e.code}")
    return len(gens)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="directory to write; <out>/api/... is created")
    ap.add_argument("--generations", type=int, default=12)
    ap.add_argument("--port", type=int, default=0, help="0 picks a free port")
    args = ap.parse_args()

    out = Path(args.out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    data_dir = tempfile.mkdtemp(prefix="probate-sim-")
    env = {**os.environ, "PROBATE_FAKE": "1", "PROBATE_DATA_DIR": data_dir}
    # No real connector may be reachable from a preview, even by accident.
    for k in list(env):
        if any(word in k.upper() for word in ("TOKEN", "API_KEY", "SECRET", "CONNECTIONS")):
            env.pop(k)

    proc = None
    try:
        print(f"simulating {args.generations} generations (fake mode)", flush=True)
        subprocess.run(
            [sys.executable, "-m", "probate.courthouse.simulate", "--generations", str(args.generations)],
            cwd=ROOT,
            env=env,
            check=True,
        )
        port = args.port or free_port()
        base = f"http://127.0.0.1:{port}"
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "probate.courthouse.app:app",
                "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning",
            ],
            cwd=CORE,
            env=env,
        )
        wait_healthy(base, proc)
        n = dump(base, out)  # routes already start with /api
        print(f"dumped {n} generations to {out}")
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
