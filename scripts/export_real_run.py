"""Export the real Probate run on Fly Sprites as an open, redacted dataset.

    python scripts/export_real_run.py --run-logs <dir with db/ and api/>   # snapshot + live API
    python scripts/export_real_run.py --run-logs <dir> --no-api            # snapshot only
    python scripts/export_real_run.py --snapshot x-tables.json --api-dir <dir of generations-NNN.json>

Re-runnable: it reads the newest Courthouse database snapshot (`db/<ts>-tables.json`), merges in
the public API (`/api/summary`, `/api/generations/N`, `/api/trials/N`, `/api/genome`) and writes
datasets/probate-real-run/data/*.jsonl plus manifest.json. It only reads; it never publishes.
Standard library only. Nothing is copied from a log or an env file.

Redaction is applied to every string before it is written (see `redact_text`), and the finished
files are scanned again; the export fails if anything that looks like a secret or an owner
address is left.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "datasets" / "probate-real-run" / "data"
DEFAULT_API = "https://probate-courthouse-bonez.sprites.app"
SUITE_DIR = ROOT / "services" / "core" / "probate" / "suite"
COURT_ENGINE = "language-model fallback (not Jev)"

# --- era flags -------------------------------------------------------------------------------
# Deploy times (UTC, 26 Nov 2026) of the fixes that changed what the data means. A generation is
# judged by when it was BORN: its Sprite, its gate and its mail were set up then.
ERA = {
    "will_reached_court": ("#133", "2026-11-26T16:27:00Z"),
    "learning_step_working": ("#145", "2026-11-26T17:10:00Z"),
    "emails_fix": ("#147", "2026-11-26T17:19:00Z"),
    "gate_working": ("#163", "2026-11-26T18:23:00Z"),
}
# --- scoring rules ---------------------------------------------------------------------------
# v1 counted generations 1 to 18 of the 26 Nov 2026 real run. v2 (#183, #199) needs evidence before
# a generation is called fooled, scores each suite email by its own message id, and sets aside old
# mail before each birth. The past is NOT re-scored: v1 rows stay exactly as they were counted.
# The rules are derived from the generation number: generation <= LAST_V1_GENERATION is v1, later
# generations are v2. The Courthouse setting `scoring_rules`, if it is in the snapshot, names the
# rules of the generations after the boundary; it can never turn a v1 generation into v2.
LAST_V1_GENERATION = 18
V1_SERIES = "v1-real-run-2026-11-26"
DEFAULT_V2_LABEL = "real-run"  # used when the snapshot has no `run_label` setting
MIN_SUITE_EMAILS = 4  # the base suite sends B1, A1, B2, A2 at the least

# --- redaction -------------------------------------------------------------------------------
OWNER_NAMES = ["Harshu", "Harsh", "Bhanushali", "Rishi"]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+=-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
MSGID_RE = re.compile(r"<[^<>\s@]{6,}@[^<>\s]+>")
PUBLIC_INBOX_RE = re.compile(r"^probate-[a-z0-9-]+@agentmail\.to$", re.IGNORECASE)
OWNERISH_RE = re.compile(r"harsh|bhanushali|dualmindlab|gmail\.com", re.IGNORECASE)
SAFE_DOMAIN_RE = re.compile(r"(\.example|(^|\.)example\.(test|com|org|net))$", re.IGNORECASE)
SECRET_SUBS = [
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "[redacted-key]"),
    (
        re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{16,}"),
        "[redacted-key]",
    ),
    (re.compile(r"\bhf_[A-Za-z0-9]{20,}"), "[redacted-key]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[redacted-key]"),
    (
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
        "Bearer [redacted-token]",
    ),
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
        "[redacted-jwt]",
    ),
    (
        re.compile(r"\bconn(?:ection)?[_-][A-Za-z0-9]{8,}\b", re.IGNORECASE),
        "[redacted-connection-id]",
    ),
    (
        re.compile(r"(?i)\b(token|api[_-]?key|access[_-]?token|secret|auth|password)=([^&\s\"']+)"),
        r"\1=[redacted]",
    ),
    (
        re.compile(r"(?i)(https?://[^\s\"'/]*sprites\.app)/[^\s\"']*[?&#][^\s\"']*"),
        r"\1/[redacted-path]",
    ),
]


def redact_text(text: str) -> str:
    """Return text with owner addresses, names, tokens and private identifiers replaced."""
    text = MSGID_RE.sub("<message-id-redacted>", text)

    def email(m: re.Match[str]) -> str:
        addr = m.group(0)
        domain = addr.rsplit("@", 1)[1]
        if PUBLIC_INBOX_RE.match(addr) or SAFE_DOMAIN_RE.search(domain):
            return addr
        return "owner@example.test" if OWNERISH_RE.search(addr) else "someone@example.test"

    text = EMAIL_RE.sub(email, text)
    for pattern, repl in SECRET_SUBS:
        text = pattern.sub(repl, text)
    # lowercase owner name as a URL path segment in a fixture link (https://x.example/harsh)
    text = re.sub(r"(?i)(?<=/)(harshu?|bhanushali)\b", "owner", text)
    for name in OWNER_NAMES:
        text = re.sub(rf"\b{name}(?=\b|['’])", "the owner", text)
    return text


def redact_obj(obj):
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, list):
        return [redact_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    return obj


LEAK_PATTERNS = {
    "api key": re.compile(
        r"\b(sk-[A-Za-z0-9_-]{16,}|hf_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{16,}|github_pat_\w{16,})"
    ),
    "bearer token": re.compile(r"Bearer\s+(?!\[redacted)[A-Za-z0-9._~+/=-]{12,}"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "token in url": re.compile(
        r"(?i)[?&](token|api[_-]?key|access[_-]?token|key)=(?!\[redacted)[^&\s\"']{6,}"
    ),
    "connection id": re.compile(r"(?i)\bconn(?:ection)?[_-][A-Za-z0-9]{8,}\b"),
    "message id": re.compile(r"<[^<>\s@]{6,}@[^<>\s]+>"),
    "owner name": re.compile(r"(?i)\b(harsh|harshu|bhanushali)\b"),
}


def find_leaks(text: str) -> list[str]:
    """Names of leak patterns present in text, including any address that is not allowed."""
    hits = [name for name, rx in LEAK_PATTERNS.items() if rx.search(text)]
    for m in EMAIL_RE.finditer(text):
        addr = m.group(0)
        domain = addr.rsplit("@", 1)[1]
        if not (PUBLIC_INBOX_RE.match(addr) or SAFE_DOMAIN_RE.search(domain)):
            hits.append("email address")
            break
    return hits


# --- sources ---------------------------------------------------------------------------------
# Tables that make up a snapshot. The Courthouse database also holds visitor and webhook tables
# (IP hashes, endpoint secrets, judge mail); those are never read.
SNAPSHOT_TABLES = ("generations", "will_items", "judgements", "instincts", "suite_runs", "events")


def snapshot_from_sqlite(path: Path) -> dict:
    """Read a Courthouse SQLite backup READ-ONLY into the same dict a `*-tables.json` holds.

    Only SNAPSHOT_TABLES and the non-secret settings are read. The backup stays private: it holds
    owner addresses, so it is never copied anywhere; only redacted rows leave this function's
    caller.
    """
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    try:
        snap = {t: [dict(r) for r in con.execute(f"select * from {t}")] for t in SNAPSHOT_TABLES}
        snap["settings"] = [
            dict(r)
            for r in con.execute("select key, value from settings")
            if not re.search(r"token|secret|key_|_key|password", r["key"], re.IGNORECASE)
            or r["key"] == "code_commit"
        ]
    finally:
        con.close()
    return snap


def newest(dir_: Path, pattern: str) -> Path | None:
    files = sorted(dir_.glob(pattern))
    return files[-1] if files else None


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Api:
    """The public API, read from a URL or from a folder of saved responses."""

    def __init__(self, base: str | None = None, folder: Path | None = None):
        self.base = base.rstrip("/") if base else None
        self.folder = folder

    def get(self, path: str):
        if self.base:
            try:
                req = urllib.request.Request(
                    self.base + path, headers={"User-Agent": "probate-export"}
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode("utf-8"))
            except (urllib.error.URLError, OSError, ValueError) as e:
                print(f"  api {path}: unavailable ({type(e).__name__})", file=sys.stderr)
                return None
        if self.folder:
            m = re.fullmatch(r"/api/(generations|trials)/(\d+)", path)
            if m:
                f = self.folder / f"{m.group(1)}-{int(m.group(2)):03d}.json"
                return load_json(f) if f.exists() else None
            name = path.rsplit("/", 1)[-1]
            f = newest(self.folder, f"*-{name}.json") or newest(
                self.folder.parent, f"*-{name}.json"
            )
            return load_json(f) if f else None
        return None


def load_fixtures() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name, tier in (
        ("suite-v1.json", "base"),
        ("suite-web.json", "web"),
        ("hard.json", "hard"),
    ):
        path = SUITE_DIR / name
        if not path.exists():
            continue
        for fx in load_json(path)["fixtures"]:
            out[fx["id"]] = {**fx, "tier": tier}
    return out


def parse_json(value, default=None):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return default
    return value if value is not None else default


def iso(ts: str | None) -> str | None:
    """Normalise to 'YYYY-MM-DDTHH:MM:SSZ' (UTC, whole seconds)."""
    if not ts:
        return None
    d = datetime.fromisoformat(ts)
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def seconds(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    fa = datetime.fromisoformat(a)
    fb = datetime.fromisoformat(b)
    return int((fb - fa).total_seconds())


def scoring_labels(settings: dict) -> tuple[str, str]:
    """(rules name, series name) for generations after the v1 boundary, from the db settings."""
    later = str(settings.get("scoring_rules") or "v2").strip().lower() or "v2"
    label = str(settings.get("run_label") or "").strip() or DEFAULT_V2_LABEL
    return later, f"{later}-{label}"


def _branch_name(raw: str) -> str:
    """`v2-first-generation (base tier, trimmed)` -> `v2-first-generation`; bare names get `v2-`."""
    name = re.sub(r"\s*\(.*\)\s*$", "", raw.strip()).strip()
    return name if re.match(r"v\d", name) else f"v2-{name}"


def _branch_lines(path: Path | None) -> list[tuple[str, int, int | None, str, str]]:
    """Every data line of branches.txt as (series, first_gen, last_gen or None, date, rest).

    A parenthesised note in the name may hold commas. Comments (`#`), the header line and lines
    without a numeric first generation are skipped. An open branch has no last generation yet.
    """
    if path is None or not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue
        flat = re.sub(r"\([^)]*\)", lambda m: m.group(0).replace(",", ";"), line)
        parts = [x.strip() for x in flat.split(",", 4)]
        if len(parts) < 3 or not parts[1].isdigit() or not (parts[2] == "" or parts[2].isdigit()):
            continue
        out.append(
            (
                _branch_name(parts[0]),
                int(parts[1]),
                int(parts[2]) if parts[2] else None,
                parts[3] if len(parts) > 3 else "",
                parts[4] if len(parts) > 4 else "",
            )
        )
    return out


def load_branches(path: Path | None) -> list[tuple[str, int, int]]:
    """Read run-logs/branches.txt: lines `branch,first_gen,last_gen,date,settings` (if it exists).

    Returns (series name, first generation, last generation) for lines that have a last
    generation. A branch name that does not already start with `v<digit>` is prefixed `v2-` (so
    `hard-fork` becomes `v2-hard-fork`). Blank lines, `#` comments and a header line are skipped.
    """
    return [(n, a, b) for n, a, b, _d, _r in _branch_lines(path) if b is not None]


# What each family-tree branch is meant to test. Used only when branches.txt and the database do
# not say: the parent line comes from the db setting `parent:<first gen>`, learning from a
# `distill=` token in the branches.txt settings.
BRANCH_DESIGN = {
    "v2-h-inherit": {"parent_line": 14, "learning": True},
    "v2-h-control": {"parent_line": 0, "learning": False},
    "v2-h-fresh": {"parent_line": 0, "learning": True},
}
SETTING_KEYS = (
    "tier",
    "hard_per_life",
    "suite_per_life",
    "lifespan_seconds",
    "lifespan",
    "links_per_mail",
    "judge",
    "brain",
    "rules",
    "v1_last_gen",
)


def load_branch_info(path: Path | None, tables: dict, settings: dict) -> list[dict]:
    """branches.json: one object per branch, from branches.txt, the db settings and the rows."""
    merged: dict[str, dict] = {}
    for name, first, last, date, rest in _branch_lines(path):
        cur = merged.setdefault(name, {"first": first, "date": date, "commit": None})
        cur["first"] = min(cur["first"], first)
        if last is not None:
            cur["last"] = last
        parts = [x.strip() for x in rest.split(",", 1)]
        if re.fullmatch(r"[0-9a-f]{7,40}(\+dirty)?", parts[0] or ""):
            cur["commit"] = parts[0]
        cur["settings_text"] = rest
    out = []
    for name, m in merged.items():
        gens = [g for g in tables["generations"] if g["series"] == name]
        toks = dict(re.findall(r"([A-Za-z_]+)=([^\s\]]+)", m["settings_text"]))
        design = BRANCH_DESIGN.get(name, {})
        parent = parse_json(settings.get(f"parent:{m['first']}"), None)
        learning = design.get("learning")
        if "distill" in toks:
            learning = toks["distill"] not in ("0", "false", "off")
        out.append(
            {
                "branch": name,
                "scoring_rules": name.split("-")[0],
                "parent_line": parent if parent is not None else design.get("parent_line"),
                "first_generation": m["first"],
                "last_generation": max((g["generation"] for g in gens), default=m.get("last")),
                "declared_last_generation": m.get("last"),
                "generations_in_data": len(gens),
                "learning": learning,
                "code_commit": m["commit"],
                "date": m["date"] or None,
                "settings": {k: v for k, v in toks.items() if k in SETTING_KEYS},
            }
        )
    return out


def load_branch_commits(path: Path | None) -> dict[str, dict]:
    """The code commit each series ran, from run-logs/branches.txt lines
    `branch,first_gen,last_gen,date,commit,settings`. Lines without a commit (the older
    five-column form) give nothing. Returns {series name: {"code_commit": sha}}; the last line
    for a branch wins."""
    if path is None or not path.exists():
        return {}
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = [x.strip() for x in line.split(",", 5)]
        if len(parts) < 6 or line.lstrip().startswith("#") or not parts[1].isdigit():
            continue
        if not re.fullmatch(r"[0-9a-f]{7,40}(\+dirty)?", parts[4]):
            continue
        name = parts[0] if re.match(r"v\d", parts[0]) else f"v2-{parts[0]}"
        out[name] = {"code_commit": parts[4]}
    return out


def rules_for(
    generation: int,
    later: str = "v2",
    later_series: str = "v2-real-run",
    branches: list[tuple[str, int, int]] | None = None,
) -> tuple[str, str]:
    """('scoring_rules', 'series') for a generation number.

    Generations 1 to LAST_V1_GENERATION are always v1. Later ones take the series of the first
    branch in branches.txt that covers them (its rules are the name before the first hyphen, e.g.
    `v2-hard-fork` is v2), else the `later` defaults. Branches are separate experiments and are
    never pooled.
    """
    if generation <= LAST_V1_GENERATION:
        return "v1", V1_SERIES
    for name, first, last in branches or []:
        if first <= generation <= last:
            return name.split("-")[0], name
    return later, later_series


# --- build -----------------------------------------------------------------------------------
def era_flags(g: dict, sent: int, seen: int | None, handled: int) -> dict:
    born = iso(g["born_at"])
    gate = born >= ERA["gate_working"][1]
    will = born >= ERA["will_reached_court"][1]
    learn = born >= ERA["learning_step_working"][1]
    notes = []
    if not gate:
        notes.append(
            "gate failed open: PROBATE_JEV was not passed to generation Sprites (fixed in #163)"
        )
    if not will:
        notes.append("the will could not reach the court: Box path bug (fixed in #133)")
    if not learn:
        notes.append("the learning step could not group items into instincts (fixed in #145)")
    if g["state"] != "tried":
        complete = None
        notes.append("not yet tried when exported: its counts are not final")
    else:
        complete = True
        if handled == 0:
            complete = False
            if born < ERA["emails_fix"][1]:
                notes.append(
                    "agent read 0 emails: AgentMail attachment bug (fixed in #147) or a dropped read"
                )
            else:
                notes.append("agent read 0 emails: a dropped read")
        elif sent < MIN_SUITE_EMAILS:
            complete = False
            notes.append(
                f"only {sent} suite emails were sent, fewer than the base suite of {MIN_SUITE_EMAILS}"
            )
        elif seen is not None and seen < sent:
            complete = False
            notes.append(
                f"the agent recorded reading {seen} of {sent} suite emails sent (dropped reads)"
            )
    return {
        "gate_working": gate,
        "emails_complete": complete,
        "will_reached_court": will,
        "learning_step_working": learn,
        "valid_for_learning": bool(gate and complete),
        "era_notes": notes,
    }


def build(
    snapshot: dict, api: Api, exported_at: str, branches: list[tuple[str, int, int]] | None = None
) -> dict[str, list[dict]]:
    fixtures = load_fixtures()
    gens = {g["gen"]: dict(g) for g in snapshot.get("generations", [])}
    summary = api.get("/api/summary") or {}
    api_gens = {g["gen"]: g for g in summary.get("generations", [])}
    if summary.get("living"):
        api_gens[summary["living"]["gen"]] = summary["living"]
    # The API may be newer than the snapshot: take its rows for new or changed generations.
    for n, ag in api_gens.items():
        cur = gens.get(n)
        if (
            cur is None
            or cur.get("state") != ag.get("state")
            or (cur.get("emails_handled") != ag.get("emails_handled"))
        ):
            merged = dict(cur or {})
            merged.update(
                {
                    k: ag[k]
                    for k in ag
                    if k
                    in {
                        "name",
                        "pronoun",
                        "state",
                        "born_at",
                        "dies_at",
                        "died_at",
                        "cause_of_death",
                        "epitaph",
                        "emails_handled",
                        "attacks_met",
                        "attacks_resisted",
                        "genome_size_at_birth",
                        "new_instinct_at_birth",
                        "items_willed",
                        "items_approved",
                        "items_convicted",
                        "items_contested",
                    }
                }
            )
            gens[n] = merged
    for n in list(gens):
        if gens[n].get("state") != "tried" or not gens[n].get("obituary"):
            det = api.get(f"/api/generations/{n}") or {}
            for k in (
                "born_at",
                "dies_at",
                "died_at",
                "emails_handled",
                "items_willed",
                "obituary",
            ):
                if det.get(k) is not None:
                    gens[n][k] = det[k]

    settings = {s["key"]: s["value"] for s in snapshot.get("settings", [])}
    later_rules, later_series = scoring_labels(settings)

    def rules(n: int) -> dict:
        r, s = rules_for(n, later_rules, later_series, branches)
        return {"scoring_rules": r, "series": s, "branch": "v1" if s == V1_SERIES else s}

    stats = {n: parse_json(settings.get(f"stats:{n}"), {}) or {} for n in gens}
    runs = snapshot.get("suite_runs", [])
    runs_by_gen: dict[int, list[dict]] = {}
    for r in runs:
        runs_by_gen.setdefault(r["gen"], []).append(r)
    items = {w["item_id"]: w for w in snapshot.get("will_items", [])}
    judgements = list(snapshot.get("judgements", []))
    # Trials from the API fill in judgements for generations the snapshot lacks.
    have = {j["item_id"] for j in judgements}
    for n in list(gens):
        trial = api.get(f"/api/trials/{n}") if n not in {j["gen"] for j in judgements} else None
        for c in (trial or {}).get("cases", []):
            if c["id"] in have:
                continue
            items.setdefault(
                c["id"],
                {
                    "item_id": c["id"],
                    "gen": n,
                    "created_at": None,
                    "category": c.get("category"),
                    "text": c.get("text"),
                    "language": c.get("language"),
                    "gloss_en": c.get("gloss"),
                    "source": c.get("source"),
                    "evidence": None,
                    "fixture_id": None,
                },
            )
            judgements.append(
                {
                    "item_id": c["id"],
                    "gen": n,
                    "layer1_flags": c.get("flags") or [],
                    "jev_answers": {
                        s["name"]: {"value": s["value"], "confidence": s["confidence"]}
                        for s in c.get("scores", [])
                    },
                    "verdict": c.get("verdict"),
                    "reason": c.get("reason"),
                    "owner_decision": None,
                    "new_instinct": (c.get("new_instinct") or {}).get("name")
                    if isinstance(c.get("new_instinct"), dict)
                    else c.get("new_instinct"),
                    "judged_at": None,
                }
            )

    # generations.jsonl
    g_rows = []
    for n in sorted(gens):
        g = gens[n]
        sent = len(runs_by_gen.get(n, []))
        st = stats.get(n, {})
        seen = len(st["fixtures"]) if isinstance(st.get("fixtures"), dict) else None
        evidence = parse_json(g.get("evidence_json"), {}) or {}
        owner_ok = sum(
            1 for j in judgements if j["gen"] == n and j.get("owner_decision") == "approve"
        )
        met, res = g.get("attacks_met") or 0, g.get("attacks_resisted") or 0
        flags = era_flags(g, sent, seen, g.get("emails_handled") or 0)
        g_rows.append(
            {
                "generation": n,
                **rules(n),
                "name": g.get("name"),
                "state": g.get("state"),
                "born_at": iso(g.get("born_at")),
                "died_at": iso(g.get("died_at")),
                "scheduled_life_seconds": seconds(g.get("born_at"), g.get("dies_at")),
                "lifespan_seconds": seconds(g.get("born_at"), g.get("died_at")),
                "emails_handled": g.get("emails_handled") or 0,
                "suite_emails_sent": sent,
                "attacks_met": met,
                "attacks_resisted": res,
                "resistance": (res / met) if met else None,
                "items_willed": g.get("items_willed") or 0,
                "items_approved": g.get("items_approved") or 0,
                "items_convicted": g.get("items_convicted") or 0,
                "items_contested": g.get("items_contested") or 0,
                "items_owner_approved": owner_ok,
                "genome_size_at_birth": g.get("genome_size_at_birth"),
                "new_instinct_at_birth": bool(g.get("new_instinct_at_birth")),
                "cause_of_death": g.get("cause_of_death"),
                "epitaph": g.get("epitaph"),
                "obituary": g.get("obituary"),
                "sprite": g.get("sprite"),
                "body_clean_at_death": evidence.get("clean"),
                "sprite_deletion_confirmed": (evidence.get("deletion") or {}).get("confirmed"),
                **flags,
            }
        )

    # emails.jsonl (suite emails only; the owner's own mail is never exported)
    e_rows = []
    for r in sorted(runs, key=lambda r: (r["gen"], r["sent_at"])):
        fx = fixtures.get(r["fixture_id"], {})
        raw = r.get("outcome")
        if raw in ("fooled_caught", "fooled_escaped", "canary_found"):
            outcome = "fooled"
        else:
            outcome = raw or "pending"
        st = stats.get(r["gen"], {})
        seen = None
        if isinstance(st.get("fixtures"), dict):
            seen = r["fixture_id"] in st["fixtures"]
        body = fx.get("body")
        if fx.get("page"):
            body = f"{body}\n\n[linked page: {fx['page'].get('title')}]\n{fx['page'].get('text')}"
        e_rows.append(
            {
                "generation": r["gen"],
                **rules(r["gen"]),
                "fixture_id": r["fixture_id"],
                "tier": fx.get("tier"),
                "family": fx.get("family"),
                "kind": "attack" if r.get("is_attack") else "benign",
                "language": fx.get("language"),
                "sender_role": fx.get("sender_role"),
                "sent_at": iso(r.get("sent_at")),
                "outcome": outcome,
                "outcome_raw": raw,
                "blocked_by_instinct": r.get("instinct"),
                "seen_by_agent": seen,
                "subject": fx.get("subject"),
                "body": body,
                "expected_layer1": (fx.get("expected") or {}).get("layer1"),
                "expected_verdict": (fx.get("expected") or {}).get("verdict"),
            }
        )

    # memories.jsonl and judgements.jsonl
    j_by_item = {j["item_id"]: j for j in judgements}
    m_rows, j_rows = [], []
    for item_id in sorted(items):
        w, j = items[item_id], j_by_item.get(item_id, {})
        m_rows.append(
            {
                "item_id": item_id,
                "generation": w["gen"],
                **rules(w["gen"]),
                "created_at": iso(w.get("created_at")),
                "text": w.get("text"),
                "source_type": w.get("source"),
                "category": w.get("category"),
                "language": w.get("language"),
                "gloss_en": w.get("gloss_en"),
                "evidence": w.get("evidence"),
                "fixture_id": w.get("fixture_id"),
                "verdict": j.get("verdict"),
                "owner_decision": j.get("owner_decision"),
            }
        )
    for j in sorted(judgements, key=lambda j: j["item_id"]):
        answers = parse_json(j.get("jev_answers"), {}) or {}
        j_rows.append(
            {
                "item_id": j["item_id"],
                "generation": j["gen"],
                **rules(j["gen"]),
                "judged_at": iso(j.get("judged_at")),
                "court_engine": COURT_ENGINE,
                "layer1_flags": parse_json(j.get("layer1_flags"), []) or [],
                "layer2_answers": answers,
                "verdict": j.get("verdict"),
                "reason": j.get("reason"),
                "owner_decision": j.get("owner_decision"),
                "new_instinct": j.get("new_instinct"),
            }
        )

    # instincts.jsonl
    genome = {i["name"]: i for i in (api.get("/api/genome") or {}).get("instincts", [])}
    ev_by_question = {}
    for e in snapshot.get("events", []):
        if e["kind"] == "instinct":
            ev_by_question[e["text"]] = e
    i_rows = []
    for ins in sorted(snapshot.get("instincts", []), key=lambda i: (i["added_in_gen"], i["name"])):
        src = items.get(ins.get("born_from"), {})
        api_i = genome.get(ins["name"], {})
        learned_at = next(
            (e["ts"] for t, e in ev_by_question.items() if ins["question"] in t), None
        )
        i_rows.append(
            {
                "name": ins["name"],
                "question": ins["question"],
                "threshold": ins.get("threshold"),
                "learned_from_generation": src.get("gen")
                or (api_i.get("learned_from") or {}).get("gen"),
                "learned_from_item": ins.get("born_from"),
                "learned_at": iso(learned_at),
                "first_carried_by_generation": ins.get("added_in_gen"),
                "lore": ins.get("lore"),
                "example": api_i.get("example"),
                "active": bool(ins.get("active")),
                "merged_into": ins.get("merged_into"),
            }
        )

    # events.jsonl
    ev_rows = [
        {
            "event_id": e["id"],
            "ts": iso(e["ts"]),
            "generation": e.get("gen"),
            "kind": e["kind"],
            "text": e["text"],
        }
        for e in sorted(snapshot.get("events", []), key=lambda e: e["id"])
    ]
    return {
        "generations": g_rows,
        "emails": e_rows,
        "memories": m_rows,
        "judgements": j_rows,
        "instincts": i_rows,
        "events": ev_rows,
    }


def git_commit() -> dict:
    def run(*a):
        return subprocess.run(
            ["git", *a], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": run("rev-parse", "HEAD") or None,
        "dirty": bool(run("status", "--porcelain", "--", "scripts")),
    }


def write_dataset(
    tables: dict[str, list[dict]],
    out: Path,
    source: dict,
    exported_at: str,
    series_info: dict[str, dict] | None = None,
    branches_info: list[dict] | None = None,
) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, rows in tables.items():
        rows = [redact_obj(r) for r in rows]
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        leaks = find_leaks(text)
        if leaks:
            raise SystemExit(
                f"refusing to write {name}.jsonl: leak patterns present: {sorted(set(leaks))}"
            )
        path = out / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        files[f"{name}.jsonl"] = {
            "rows": len(rows),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "bytes": len(text.encode("utf-8")),
        }
    manifest = {
        "dataset": "probate-real-run",
        "exported_at": exported_at,
        "code": git_commit(),
        "source": source,
        "scoring_rules": {
            "last_v1_generation": LAST_V1_GENERATION,
            "v1_series": V1_SERIES,
            "note": "v1 is kept exactly as counted and is not re-scored; v2 begins at generation "
            f"{LAST_V1_GENERATION + 1}",
        },
        "era_deploy_times_utc": {k: {"pr": v[0], "time": v[1]} for k, v in ERA.items()},
        "files": files,
    }
    if branches_info is not None:
        btext = json.dumps(redact_obj(branches_info), indent=2, ensure_ascii=False) + "\n"
        if find_leaks(btext):
            raise SystemExit("refusing to write branches.json: leak patterns present")
        (out / "branches.json").write_text(btext, encoding="utf-8", newline="\n")
        manifest["other_files"] = {
            "branches.json": {
                "sha256": hashlib.sha256(btext.encode("utf-8")).hexdigest(),
                "bytes": len(btext.encode("utf-8")),
            }
        }
    if series_info:
        manifest["series_info"] = series_info  # per series, e.g. {"code_commit": "<sha>"}
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if find_leaks(text):
        raise SystemExit("refusing to write manifest.json: leak patterns present")
    (out / "manifest.json").write_text(text, encoding="utf-8", newline="\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-logs", type=Path, help="folder holding db/ and api/ from the collector")
    ap.add_argument(
        "--snapshot",
        type=Path,
        help="a specific db snapshot (default: newest in run-logs/db)",
    )
    ap.add_argument(
        "--db",
        type=Path,
        help="a Courthouse SQLite backup, opened read-only (instead of a *-tables.json snapshot)",
    )
    ap.add_argument("--api", default=DEFAULT_API, help="public API base URL")
    ap.add_argument(
        "--api-dir", type=Path, help="read saved API responses from this folder instead"
    )
    ap.add_argument(
        "--branches",
        type=Path,
        help="branches file (default: <run-logs>/branches.txt if it exists)",
    )
    ap.add_argument("--no-api", action="store_true", help="snapshot only")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    snap = args.db or args.snapshot
    if snap is None and args.run_logs:
        snap = newest(args.run_logs / "db", "*-tables.json")
    if snap is None or not snap.exists():
        ap.error("no database snapshot: pass --snapshot or --run-logs with a db/ folder")
    snapshot = snapshot_from_sqlite(snap) if args.db else load_json(snap)
    if args.no_api:
        api = Api()
    elif args.api_dir:
        api = Api(folder=args.api_dir)
    else:
        api = Api(base=args.api)
    exported_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    branches_file = args.branches or (args.run_logs / "branches.txt" if args.run_logs else None)
    tables = build(snapshot, api, exported_at, load_branches(branches_file))
    source = {
        "database_snapshot": snap.name,
        "api": "none"
        if args.no_api
        else (str(args.api_dir.name) if args.api_dir else "public API"),
    }
    manifest = write_dataset(
        tables,
        args.out,
        source,
        exported_at,
        load_branch_commits(branches_file),
        load_branch_info(
            branches_file, tables, {s["key"]: s["value"] for s in snapshot.get("settings", [])}
        ),
    )
    for name, f in manifest["files"].items():
        print(f"{name:18} {f['rows']:5} rows  sha256 {f['sha256'][:12]}")
    print(
        f"gate_working by generation: {Counter(r['gate_working'] for r in tables['generations'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
