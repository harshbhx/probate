"""Deploy the Courthouse to a Fly.io Sprite in one go.

    services/core/.venv/bin/python scripts/deploy.py            # deploy or update
    services/core/.venv/bin/python scripts/deploy.py --check    # only check config, change nothing
    services/core/.venv/bin/python scripts/deploy.py --env staging   # a named environment

--env picks the sprite, the URL file (.data/courthouse-url-<env>.txt) and the non-secret settings
from config/environments.yaml. It refuses v1-archive, which is a read-only record.

Reads services/core/.env (never committed). Builds nothing itself: run `npm run build`
first (`make deploy` does both). Steps:

1. Create the Courthouse Sprite if it isn't there (409 means it already exists).
2. Upload the code bundle (Python service, config, built website) and install it.
3. Upload .env with live settings (PROBATE_FAKE=0, clock on, data outside the code dir).
4. Make the URL public (its address goes into .env before the first start).
5. Register the `courthouse` service on port 8080: started once on a first deploy, restarted
   once on a later one. Never started twice: two processes on one database tick the same clock.
6. Wait for /healthz.

Re-running it is safe: the database lives in /home/sprite/data, which deploys never touch.
"""

from __future__ import annotations

import argparse
import shlex
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "core"))

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))

import envs

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


ADMIN_TOKEN_MIN = 24  # keep in step with probate.common.config.ADMIN_TOKEN_MIN
EDGE_TOKEN_MIN = 16


def weak_admin_token(token: str) -> bool:
    return token in ("", "dev-admin") or len(token) < ADMIN_TOKEN_MIN


def edge_problem(env: dict[str, str], extra: dict[str, str]) -> str | None:
    """A Courthouse that requires the edge needs a real edge token, or nobody can reach it."""
    merged = {**env, **extra}
    if (
        merged.get("PROBATE_REQUIRE_EDGE") == "1"
        and len(merged.get("PROBATE_EDGE_TOKEN", "")) < EDGE_TOKEN_MIN
    ):
        return f"PROBATE_REQUIRE_EDGE=1 needs PROBATE_EDGE_TOKEN of at least {EDGE_TOKEN_MIN} characters"
    return None


def read_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        sys.exit(f"Missing {ENV_FILE.relative_to(ROOT)}. Copy .env.example and fill it in.")
    env: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    missing = [k for k in REQUIRED if not env.get(k)]
    if missing:
        sys.exit(f"Fill these in {ENV_FILE.relative_to(ROOT)}: {', '.join(missing)}")
    if weak_admin_token(env["PROBATE_ADMIN_TOKEN"]):  # never print the value
        sys.exit(
            f"PROBATE_ADMIN_TOKEN in {ENV_FILE.relative_to(ROOT)} is a dev default or shorter than "
            f"{ADMIN_TOKEN_MIN} characters. Set a long random one."
        )
    return env


def render_env(env: dict[str, str], extra: dict[str, str] | None = None) -> bytes:
    # The service sources this file with bash, so every value is quoted: unquoted JSON loses its
    # double quotes and a placeholder such as <connection_id> is a syntax error.
    # Order: services/core/.env, then the environment's settings, then the live basics.
    merged = {**env, **(extra or {}), **LIVE}
    return ("\n".join(f"{k}={shlex.quote(v)}" for k, v in merged.items()) + "\n").encode()


def restore_database(api, name: str, path: Path) -> str:
    """Put a saved database on the Courthouse before it starts, so the family continues where it
    stopped (for example after the Sprite was deleted). It never overwrites a database that is
    already there. Returns what it did, for the progress line."""
    if not path.is_file():
        sys.exit(f"--restore-db: {path} is not a file")
    data = path.read_bytes()
    if not data.startswith(b"SQLite format 3"):
        sys.exit(f"--restore-db: {path} is not a SQLite database")
    if api.read_file(name, "data/probate.db"):
        return "a database is already on the Courthouse; left it alone"
    api.write_file(name, "data/probate.db", data)
    return f"restored {len(data) // 1024} KiB from {path.name}"


def start_courthouse(api, name: str, fresh: bool, wait=time.sleep, tries: int = 6) -> str:
    """Register the courthouse service and bring it up exactly once.

    A first deploy (`fresh`: the service has never run, so there is no database yet) registers the
    service and starts it only if registering did not already start it. The staging test saw
    `start` then `restart` five seconds apart: the first process was killed in the middle of birth
    and generation 1 had no agent. A later deploy restarts once to load the new code.
    """
    api.put_service(name, "courthouse", "bash", ["-lc", SERVE], http_port=8080)
    if not fresh:
        api.service_action(name, "courthouse", "restart")
        return "restarted once"
    for _ in range(tries):  # registering may start it; give that a moment before starting it again
        if api.service_status(name, "courthouse") in ("running", "starting"):
            return "started by registering it; not started again"
        wait(2)
    api.service_action(name, "courthouse", "start")
    return "started once"


def git_commit() -> str:
    """The commit of the working tree being deployed; `+dirty` if tracked files have changes."""
    import subprocess

    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "-uno"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""
    return sha + ("+dirty" if dirty else "")


def step(msg: str) -> None:
    print(f"→ {msg}", flush=True)


def main() -> None:
    # The progress lines use arrows; a Windows console defaults to a code page that cannot print them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--name", help="sprite name (default: the environment's, else probate-courthouse)"
    )
    ap.add_argument("--env", help="a named environment from config/environments.yaml")
    ap.add_argument(
        "--allow-brain-change",
        action="store_true",
        help="let the environment replace PROBATE_BRAIN, PROBATE_BRAIN_FALLBACKS or PROBATE_JEV "
        "set differently in services/core/.env",
    )
    ap.add_argument("--check", action="store_true", help="validate config and bundle, then stop")
    ap.add_argument(
        "--restore-db",
        type=Path,
        help="a saved probate.db to put on a NEW Courthouse before it starts (never overwrites one that exists)",
    )
    args = ap.parse_args()

    target = envs.resolve(args.env)
    envs.announce(target)
    if target and target.read_only:
        sys.exit(f"{target.name} is a read-only record; deploy refused.")
    if target and (target.simulated or not target.sprite):
        sys.exit(f"{target.name} is simulated and has no Sprite; run `make sim` instead.")
    args.name = args.name or (target.sprite if target else envs.LEGACY_SPRITE)
    extra = target.sprite_settings() if target else {}
    url_file = target.url_file if target else URL_FILE

    env = read_env()
    extra, notes = envs.guard(extra, env, args.allow_brain_change)
    if problem := edge_problem(env, extra):
        sys.exit(problem)
    commit = git_commit()
    if commit:
        extra["PROBATE_CODE_COMMIT"] = commit
    print("Effective settings on the Sprite (no secrets):")
    print("\n".join(envs.effective(env, extra)))
    print(f"  code commit: {commit or 'unknown (not a git checkout)'}")
    for n in notes:
        print(f"  note: {n}")
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

    # A database on the Sprite means the service has run before; none means a first deploy.
    fresh = api.read_file(args.name, "data/probate.db") is None

    step("uploading code")
    api.write_file(args.name, "bundle.tgz", bundle)
    res = api.exec(
        args.name, ["bash", "-lc", f"rm -rf app && {INSTALL} && mkdir -p data"], cwd="/home/sprite"
    )
    if res.exit_code:
        sys.exit(f"install failed ({res.exit_code}):\n{res.stderr[-1500:]}")
    if args.restore_db:
        step("database: " + restore_database(api, args.name, args.restore_db))

    # The URL is known before the service starts, so .env is complete and one start is enough.
    info = api.make_public(args.name)
    url = (info.get("url") or (api.get(args.name) or {}).get("url") or "").rstrip("/")
    if not url:
        sys.exit("Deployed, but the API returned no URL. Check `sprite info` for it.")
    if target and target.set_public_url and env.get("PROBATE_PUBLIC_URL") != url:
        extra["PROBATE_PUBLIC_URL"] = url

    step("writing .env")
    api.write_file(args.name, "app/services/core/.env", render_env(env, extra), mode="0600")

    step("starting the courthouse service")
    step(start_courthouse(api, args.name, fresh))

    step(f"waiting for {url}/healthz")
    for _ in range(30):
        try:
            if httpx.get(f"{url}/healthz", timeout=10).status_code == 200:
                url_file.parent.mkdir(exist_ok=True)
                url_file.write_text(url + "\n", encoding="utf-8")
                if target and target.name in ("production-v2", "judges-demo"):
                    URL_FILE.write_text(
                        url + "\n", encoding="utf-8"
                    )  # ship.sh links the docs site to it
                print(f"\nCourthouse is live: {url}")
                return
        except httpx.HTTPError:
            pass
        time.sleep(4)
    sys.exit(
        f"The service didn't answer in 2 minutes. Logs: GET /v1/sprites/{args.name}/services/courthouse/logs"
    )


if __name__ == "__main__":
    main()
