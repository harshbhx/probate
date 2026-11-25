"""Deploy the Courthouse to a Fly.io Sprite in one go.

    services/core/.venv/bin/python scripts/deploy.py            # deploy or update
    services/core/.venv/bin/python scripts/deploy.py --check    # only check config, change nothing

Reads services/core/.env (never committed). Builds nothing itself: run `npm run build`
first (`make deploy` does both). Steps:

1. Create the Courthouse Sprite if it isn't there (409 means it already exists).
2. Upload the code bundle (Python service, config, built website) and install it.
3. Upload .env with live settings (PROBATE_FAKE=0, clock on, data outside the code dir).
4. Register the `courthouse` service on port 8080 and (re)start it.
5. Make the URL public and wait for /healthz.

Re-running it is safe: the database lives in /home/sprite/data, which deploys never touch.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "core"))

import httpx

from probate.adapters.sprites import SpritesAPI
from probate.common.bundle import INSTALL, make_bundle

ENV_FILE = ROOT / "services" / "core" / ".env"
URL_FILE = ROOT / ".data" / "courthouse-url.txt"
REQUIRED = [
    "PROBATE_SPRITES_TOKEN",
    "PROBATE_ADMIN_TOKEN",
    "PROBATE_CONNECTIONS",
    "PROBATE_CF_ACCOUNT_ID",
]
LIVE = {
    "PROBATE_FAKE": "0",
    "PROBATE_RUN_CLOCK": "1",
    "PROBATE_DATA_DIR": "/home/sprite/data",
}
SERVE = (
    "cd /home/sprite/app/services/core && set -a && . ./.env && set +a && "
    "exec python3 -m uvicorn probate.courthouse.app:app --host 0.0.0.0 --port 8080"
)


def read_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        sys.exit(f"Missing {ENV_FILE.relative_to(ROOT)}. Copy .env.example and fill it in.")
    env: dict[str, str] = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    missing = [k for k in REQUIRED if not env.get(k)]
    if missing:
        sys.exit(f"Fill these in {ENV_FILE.relative_to(ROOT)}: {', '.join(missing)}")
    return env


def render_env(env: dict[str, str]) -> bytes:
    merged = {**env, **LIVE}
    return ("\n".join(f"{k}={v}" for k, v in merged.items()) + "\n").encode()


def step(msg: str) -> None:
    print(f"→ {msg}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="probate-courthouse")
    ap.add_argument("--check", action="store_true", help="validate config and bundle, then stop")
    args = ap.parse_args()

    env = read_env()
    bundle = make_bundle(web=True)
    step(f"bundle ready: {len(bundle) // 1024} KiB")
    if not (ROOT / "config" / "owner.yaml").exists():
        print("  note: config/owner.yaml is missing, so the example owner profile will be used.")
    if args.check:
        step("config looks complete. Nothing was changed.")
        return

    api = SpritesAPI(env["PROBATE_SPRITES_TOKEN"])
    step(f"sprite {args.name}")
    api.create(args.name)

    step("uploading code")
    api.write_file(args.name, "bundle.tgz", bundle)
    res = api.exec(args.name, ["bash", "-lc", f"rm -rf app && {INSTALL} && mkdir -p data"], cwd="/home/sprite")
    if res.exit_code:
        sys.exit(f"install failed ({res.exit_code}):\n{res.stderr[-1500:]}")

    step("writing .env")
    api.write_file(args.name, "app/services/core/.env", render_env(env), mode="0600")

    step("starting the courthouse service")
    api.put_service(args.name, "courthouse", "bash", ["-lc", SERVE], http_port=8080)
    try:
        api.service_action(args.name, "courthouse", "restart")
    except httpx.HTTPStatusError:
        # First deploy: nothing to restart yet.
        api.service_action(args.name, "courthouse", "start")

    info = api.make_public(args.name)
    url = (info.get("url") or (api.get(args.name) or {}).get("url") or "").rstrip("/")
    if not url:
        sys.exit("Deployed, but the API returned no URL. Check `sprite info` for it.")

    step(f"waiting for {url}/healthz")
    for _ in range(30):
        try:
            if httpx.get(f"{url}/healthz", timeout=10).status_code == 200:
                URL_FILE.parent.mkdir(exist_ok=True)
                URL_FILE.write_text(url + "\n")  # ship.sh links the docs site to it
                print(f"\nCourthouse is live: {url}")
                return
        except httpx.HTTPError:
            pass
        time.sleep(4)
    sys.exit(f"The service didn't answer in 2 minutes. Logs: GET /v1/sprites/{args.name}/services/courthouse/logs")


if __name__ == "__main__":
    main()
