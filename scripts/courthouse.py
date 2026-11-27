"""Run the family from your laptop: check it is ready, then pause, resume or start a new line.

    services/core/.venv/bin/python scripts/courthouse.py --env staging status   # a named environment
    services/core/.venv/bin/python scripts/courthouse.py preflight          # read-only checks
    services/core/.venv/bin/python scripts/courthouse.py preflight --fix    # also make the URL public
    services/core/.venv/bin/python scripts/courthouse.py status [--deep]
    services/core/.venv/bin/python scripts/courthouse.py pause | resume | tick | force-death
    services/core/.venv/bin/python scripts/courthouse.py line 16            # next child: Gen 16's
    services/core/.venv/bin/python scripts/courthouse.py line --cancel
    services/core/.venv/bin/python scripts/courthouse.py decide <item_id> approve|refuse

Reads services/core/.env (PROBATE_ADMIN_TOKEN, PROBATE_SPRITES_TOKEN) and the Courthouse URL
from .data/courthouse-url.txt (courthouse-url-<env>.txt with --env; written by deploy.py) or PROBATE_PUBLIC_URL. Prints no secrets.

`preflight` exists because of the real run: the Courthouse URL went private (judges were sent
to a Sprites sign-in page), generations 1 to 12 had a gate that could not reach its judge, and
generations 17 and 18 were born after AgentMail's daily limit ran out. Each is checked here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import envs  # noqa: E402

ENV_FILE = ROOT / "services" / "core" / ".env"
URL_FILE = ROOT / ".data" / "courthouse-url.txt"
SITE = "https://probate.dualmindlab.tech"
SPRITE = "probate-courthouse"


def read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def courthouse_url(env: dict[str, str], url_file: Path = URL_FILE) -> str:
    if url_file.exists() and url_file.read_text(encoding="utf-8").strip():
        return url_file.read_text(encoding="utf-8").strip().rstrip("/")
    return env.get("PROBATE_PUBLIC_URL", "").rstrip("/")


class Report:
    def __init__(self) -> None:
        self.failed = 0
        self.warned = 0

    def ok(self, text: str) -> None:
        print(f"  ok    {text}")

    def warn(self, text: str) -> None:
        self.warned += 1
        print(f"  warn  {text}")

    def fail(self, text: str) -> None:
        self.failed += 1
        print(f"  FAIL  {text}")


def is_private(r: httpx.Response) -> bool:
    loc = r.headers.get("location", "")
    return r.status_code in (301, 302, 303, 307, 308) and "sprites.dev/auth" in loc


def preflight(
    env: dict[str, str], url: str, fix: bool, deep: bool, sprite: str = SPRITE
) -> int:
    rep = Report()
    print("Configuration")
    if not ENV_FILE.exists():
        rep.fail("services/core/.env is missing")
    for key in ("PROBATE_ADMIN_TOKEN", "PROBATE_SPRITES_TOKEN", "PROBATE_CONNECTIONS"):
        (rep.ok if env.get(key) else rep.fail)(f"{key} {'set' if env.get(key) else 'missing'}")
    if env.get("PROBATE_ADMIN_TOKEN") in ("dev-admin", ""):
        rep.fail("PROBATE_ADMIN_TOKEN is the dev default")
    if not url:
        rep.fail("no Courthouse URL: run deploy.py (same --env), or set PROBATE_PUBLIC_URL")
        return finish(rep)

    print(f"Courthouse {url}")
    http = httpx.Client(timeout=20, follow_redirects=False)
    try:
        r = http.get(f"{url}/healthz")
    except httpx.HTTPError as exc:
        rep.fail(f"/healthz unreachable ({type(exc).__name__})")
        return finish(rep)
    if is_private(r):
        if fix and env.get("PROBATE_SPRITES_TOKEN"):
            from probate.adapters.sprites import SpritesAPI

            SpritesAPI(env["PROBATE_SPRITES_TOKEN"]).make_public(env.get("COURTHOUSE", sprite))
            r = http.get(f"{url}/healthz")
            if is_private(r):
                rep.fail("URL is still private after asking Sprites to make it public")
            else:
                rep.ok("URL was private (Sprites sign-in page); it is public again")
        else:
            rep.fail(
                "URL is private: visitors get the Sprites sign-in page. "
                "Run `preflight --fix` or `make deploy`"
            )
    if is_private(r):
        check_site(http, rep)
        return finish(rep)  # nothing else can be read until the URL is public
    if r.status_code == 200:
        rep.ok("/healthz 200")
    else:
        rep.fail(f"/healthz answered {r.status_code}")

    s = http.get(f"{url}/api/summary")
    if s.status_code == 200:
        n = (s.json().get("counts") or {}).get("generations", "?")
        rep.ok(f"/api/summary 200 ({n} generations in the register)")
    else:
        rep.fail(f"/api/summary answered {s.status_code}")

    st = http.get(
        f"{url}/admin/status",
        params={"deep": "true"} if deep else None,
        headers={"X-Probate-Admin": env.get("PROBATE_ADMIN_TOKEN", "")},
    )
    if st.status_code == 403:
        rep.fail("admin token refused: the .env here and the Courthouse's differ (`make deploy`)")
    elif st.status_code == 404:
        rep.warn("/admin/status is missing: the Courthouse runs older code (`make deploy`)")
    elif st.status_code != 200:
        rep.fail(f"/admin/status answered {st.status_code}")
    else:
        d = st.json()
        print("Family")
        rep.ok(f"mode {d['mode']}, judge: {d['judge']}, suite tier {d['suite_tier']}")
        if d["paused"]:
            rep.warn("births are paused (`courthouse.py resume` to start)")
        if d["resting"]:
            rep.warn(f"resting: {d['resting']}")
        living = d.get("living")
        rep.ok(
            f"alive: Gen {living['gen']} {living['name']} ({living['state']})"
            if living
            else f"no one alive; next is Gen {d['next_gen']}"
        )
        if d.get("next_parent"):
            rep.ok(f"next child starts a new line from Gen {d['next_parent']}")
        m = d["mail"]
        if m["limit"]:
            need = m["next_life_needs"] + m["reserve"]
            lives = m["left_today"] // max(m["next_life_needs"], 1)
            line = (
                f"AgentMail today: {m['used_today']} of {m['limit']} sent; about {lives} more lives"
            )
            (rep.ok if m["left_today"] >= need else rep.warn)(
                line if m["left_today"] >= need else line + " (waits for 00:00 UTC)"
            )
        b = d["budget"]
        if b["limit_usd"] and b["spent_usd"] >= b["limit_usd"]:
            rep.fail(f"spending cap reached: {b['spent_usd']} of {b['limit_usd']} USD")
        else:
            rep.ok(f"spent {b['spent_usd']} of {b['limit_usd'] or 'no cap'} USD")
        if deep and "living_gate_errors" in d:
            (rep.fail if d["living_gate_errors"] else rep.ok)(
                f"living generation's gate errors: {d['living_gate_errors']}"
                + (" (its gate lets everything through)" if d["living_gate_errors"] else "")
            )
        for e in d["recent_errors"][:3]:
            rep.warn(f"recent error {e['ts'][:19]}: {e['text'][:110]}")

    check_site(http, rep)
    return finish(rep)


def check_site(http: httpx.Client, rep: Report) -> None:
    print("Public site")
    try:
        site = http.get(SITE)
        (rep.ok if site.status_code == 200 else rep.fail)(f"{SITE} {site.status_code}")
    except httpx.HTTPError as exc:
        rep.fail(f"{SITE} unreachable ({type(exc).__name__})")


def finish(rep: Report) -> int:
    print(
        f"\n{'Ready' if not rep.failed else 'Not ready'}: "
        f"{rep.failed} failed, {rep.warned} warnings."
    )
    return 1 if rep.failed else 0


def admin(env: dict[str, str], url: str, method: str, path: str, **params) -> int:
    r = httpx.request(
        method,
        f"{url}{path}",
        params=params or None,
        headers={"X-Probate-Admin": env.get("PROBATE_ADMIN_TOKEN", "")},
        timeout=60,
    )
    try:
        print(json.dumps(r.json(), indent=2, default=str))
    except ValueError:
        print(r.text[:500])
    return 0 if r.status_code < 400 else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--env", help="a named environment from config/environments.yaml")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--fix", action="store_true", help="make a private Courthouse URL public")
    p.add_argument("--deep", action="store_true", help="also read the living generation's log")
    st = sub.add_parser("status")
    st.add_argument("--deep", action="store_true")
    for name in ("pause", "resume", "tick", "force-death"):
        sub.add_parser(name)
    ln = sub.add_parser("line")
    ln.add_argument("gen", nargs="?", type=int)
    ln.add_argument("--cancel", action="store_true")
    dc = sub.add_parser("decide")
    dc.add_argument("item_id")
    dc.add_argument("decision", choices=["approve", "refuse"])
    args = ap.parse_args()

    target = envs.resolve(args.env)
    envs.announce(target)
    env = read_env()
    url = courthouse_url(env, target.url_file if target else URL_FILE)
    if args.cmd == "preflight":
        sys.exit(preflight(env, url, args.fix, args.deep, target.sprite if target else SPRITE))
    if target and target.read_only and args.cmd != "status":
        sys.exit(f"{target.name} is a read-only record; {args.cmd} refused.")
    if not url:
        sys.exit("No Courthouse URL: run deploy.py, or set PROBATE_PUBLIC_URL.")
    if args.cmd == "status":
        sys.exit(admin(env, url, "GET", "/admin/status", **({"deep": "true"} if args.deep else {})))
    if args.cmd in ("pause", "resume", "tick", "force-death"):
        sys.exit(admin(env, url, "POST", f"/admin/{args.cmd}"))
    if args.cmd == "line":
        if args.cancel:
            sys.exit(admin(env, url, "DELETE", "/admin/lineage"))
        if not args.gen:
            sys.exit("Say which generation: `courthouse.py line 16`.")
        sys.exit(admin(env, url, "POST", "/admin/lineage", from_gen=args.gen))
    if args.cmd == "decide":
        sys.exit(
            admin(env, url, "POST", f"/admin/contested/{args.item_id}", decision=args.decision)
        )


if __name__ == "__main__":
    main()
