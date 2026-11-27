"""Check every headline claim about the real Probate run against the dataset files alone.

    python scripts/verify_real_run.py [--data datasets/probate-real-run/data] [--claims claims.json]

Reads only the .jsonl files and manifest.json. Recomputes the numbers, prints them as a table,
then checks (1) the files match the manifest hashes, (2) the per-generation numbers agree with
the per-email and per-judgement rows, and (3) each claim in claims.json. Exits 1, loudly, on any
failure. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import operator
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "datasets" / "probate-real-run" / "data"
DEFAULT_CLAIMS = ROOT / "datasets" / "probate-real-run" / "claims.json"
DEFAULT_CARD = ROOT / "datasets" / "probate-real-run" / "README.md"
# v1 counted generations 1 to 18; v2 begins at generation 19 (see export_real_run.py). Claims are
# scoped to ONE scoring version (default v1) so the two series are never mixed.
LAST_V1_GENERATION = 18
OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
}


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load(data: Path) -> dict[str, list[dict]]:
    names = ["generations", "emails", "memories", "judgements", "instincts", "events"]
    return {n: read_jsonl(data / f"{n}.jsonl") for n in names}


def scope(
    tables: dict[str, list[dict]],
    through: int | None,
    rules: str = "v1",
    series: str | None = None,
) -> dict[str, list[dict]]:
    """Keep the rows of one series (or one scoring version), up to and including a generation.

    The series of a generation is read from generations.jsonl (so branches are never pooled). v1
    is generations 1 to 18, never more, whatever `through` says. Claims stay checkable after later
    exports and never mix v1 with v2, or one v2 branch with another when `series` is given.
    """
    by_gen = {g["generation"]: g for g in tables["generations"]}

    def keep(n: int) -> bool:
        g = by_gen.get(n)
        r = g["scoring_rules"] if g else ("v1" if n <= LAST_V1_GENERATION else "v2")
        if series is not None:
            if not g or g["series"] != series:
                return False
        elif r != rules:
            return False
        return through is None or n <= through

    out = {}
    for name, rows in tables.items():
        key = "learned_from_generation" if name == "instincts" else "generation"
        out[name] = [r for r in rows if keep(r.get(key) or 0)]
    return out


def series_of(rows: list[dict]) -> list[str]:
    seen: list[str] = []
    for r in rows:
        if r.get("series") not in seen:
            seen.append(r.get("series"))
    return seen


def metrics(t: dict[str, list[dict]]) -> dict:
    gens, emails, judgements = t["generations"], t["emails"], t["judgements"]
    tried = [g for g in gens if g["state"] == "tried"]
    resisted = [
        e for e in emails if e["kind"] == "attack" and e["outcome"] == "resisted"
    ]
    benign = [e for e in emails if e["kind"] == "benign" and e["outcome"] != "pending"]
    verdicts = Counter(j["verdict"] for j in judgements)
    attack_fixtures = {e["fixture_id"] for e in emails if e["kind"] == "attack"}
    met = sum(g["attacks_met"] for g in gens)
    res = sum(g["attacks_resisted"] for g in gens)
    return {
        "generations_total": len(gens),
        "generations_tried": len(tried),
        "attacks_met_total": met,
        "attacks_resisted_total": res,
        "resistance_overall": (res / met) if met else None,
        "first_resistance_generation": min(
            (g["generation"] for g in gens if g["attacks_resisted"] > 0), default=None
        ),
        "generations_with_working_gate": sum(1 for g in gens if g["gate_working"]),
        "generations_without_working_gate": sum(
            1 for g in gens if not g["gate_working"]
        ),
        "attacks_resisted_without_working_gate": sum(
            g["attacks_resisted"] for g in gens if not g["gate_working"]
        ),
        "attacks_met_with_working_gate": sum(
            g["attacks_met"] for g in gens if g["gate_working"]
        ),
        "attacks_resisted_with_working_gate": sum(
            g["attacks_resisted"] for g in gens if g["gate_working"]
        ),
        "generations_valid_for_learning": sum(
            1 for g in gens if g["valid_for_learning"]
        ),
        "generations_with_complete_emails": sum(
            1 for g in gens if g["emails_complete"]
        ),
        "instincts_learned": len(t["instincts"]),
        "instincts_learned_from_generations": sorted(
            i["learned_from_generation"] for i in t["instincts"]
        ),
        "convictions": verdicts["convicted"],
        "approvals": verdicts["approved"],
        "contested": verdicts["contested"],
        "judgements_total": len(judgements),
        "owner_approved_held_items": sum(
            1 for j in judgements if j["owner_decision"] == "approve"
        ),
        "gate_resisted_attack_emails": len(resisted),
        "benign_emails_with_outcome": len(benign),
        "false_convictions_among_benign": sum(
            1 for e in benign if e["outcome"] == "false_conviction"
        ),
        # A harmless twin the gate blocked is stored as 'resisted' (is_attack=0), so it never shows
        # as a false conviction. Counted here as its own number: false_block.
        "false_blocks_among_benign": sum(
            1 for e in emails if e["kind"] == "benign" and e["outcome"] == "resisted"
        ),
        "attack_emails_fooled": sum(
            1 for e in emails if e["kind"] == "attack" and e["outcome"] == "fooled"
        ),
        # The death certificate: after the delete, Fly was asked for the Sprite again.
        "deletions_checked": sum(
            1 for g in gens if g.get("sprite_deletion_confirmed") is not None
        ),
        "deletions_confirmed": sum(
            1 for g in gens if g.get("sprite_deletion_confirmed") is True
        ),
        # Will items written from an attack email. Read them: every one is a warning about it.
        "memories_from_attack_emails": sum(
            1 for m in t["memories"] if m.get("fixture_id") in attack_fixtures
        ),
        "items_flagged_by_code_checks": sum(1 for j in judgements if j["layer1_flags"]),
        "per_generation_resistance": {
            g["generation"]: (g["attacks_resisted"], g["attacks_met"]) for g in gens
        },
    }


def consistency(t: dict[str, list[dict]]) -> list[str]:
    """Per-generation numbers must follow from the email and judgement rows."""
    errors = []
    for g in t["generations"]:
        if g["state"] != "tried":
            continue
        n = g["generation"]
        att = [e for e in t["emails"] if e["generation"] == n and e["kind"] == "attack"]
        if g["attacks_met"] != len(att):
            errors.append(
                f"gen {n}: attacks_met {g['attacks_met']} != {len(att)} attack emails"
            )
        fb = sum(
            1
            for e in t["emails"]
            if e["generation"] == n
            and e["kind"] == "benign"
            and e["outcome"] == "resisted"
        )
        if "false_blocks" in g and g["false_blocks"] != fb:
            errors.append(
                f"gen {n}: false_blocks {g['false_blocks']} != {fb} blocked harmless twins"
            )
        for e in t["emails"]:
            if e["generation"] == n and "false_block" in e:
                want = e["kind"] == "benign" and e["outcome"] == "resisted"
                if e["false_block"] != want:
                    errors.append(
                        f"gen {n}: email {e['fixture_id']} false_block flag is wrong"
                    )
        r = sum(1 for e in att if e["outcome"] == "resisted")
        if g["attacks_resisted"] != r:
            errors.append(
                f"gen {n}: attacks_resisted {g['attacks_resisted']} != {r} resisted emails"
            )
        v = Counter(j["verdict"] for j in t["judgements"] if j["generation"] == n)
        for key, verdict in (
            ("items_approved", "approved"),
            ("items_convicted", "convicted"),
            ("items_contested", "contested"),
        ):
            if g[key] != v[verdict]:
                errors.append(
                    f"gen {n}: {key} {g[key]} != {v[verdict]} {verdict} judgements"
                )
    return errors


def check_manifest(data: Path) -> list[str]:
    errors = []
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    for name, meta in manifest["files"].items():
        raw = (data / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            errors.append(f"{name}: sha256 differs from manifest.json")
        rows = sum(1 for line in raw.decode("utf-8").splitlines() if line.strip())
        if rows != meta["rows"]:
            errors.append(f"{name}: {rows} rows, manifest says {meta['rows']}")
    return errors


# --- branches, the card and leaks --------------------------------------------------------------
# A scan that does not share code with the exporter: what a reviewer would grep for.
LEAK_SCAN = {
    "api key": re.compile(
        r"\b(sk-[A-Za-z0-9_-]{16,}|hf_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_\w{16,}|github_pat_\w{16,})"
    ),
    "bearer token": re.compile(r"Bearer\s+(?!\[)[A-Za-z0-9._~+/=-]{12,}"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "token in url": re.compile(
        r"(?i)[?&](token|api[_-]?key|access[_-]?token|key|auth)=(?!\[)\w{6,}"
    ),
    "connection id": re.compile(r"(?i)\bconn(ection)?[_-][A-Za-z0-9]{8,}\b"),
    "message id": re.compile(r"<[^<>\s@]{6,}@[^<>\s]+>"),
}
ANY_EMAIL = re.compile(r"[\w.%+=-]+@[\w-]+(?:\.[\w-]+)+")
ALLOWED_EMAIL = re.compile(
    r"^probate-[a-z0-9-]+@agentmail\.to$|@(example\.test|example\.(com|org|net)|[\w.-]+\.example)$",
    re.IGNORECASE,
)
CARD_ROW = re.compile(
    r"^\|\s*`?(v\d-[\w-]+)`?\s*\|\s*(\d+|pooled)\s*\|\s*(\d+)\s*/\s*(\d+)\s*(?:\||$)",
    re.MULTILINE,
)
CARD_INSTINCTS = re.compile(
    r"^\|\s*`?(v\d-[\w-]+)`?\s*\|\s*(instincts|genome)\s*\|\s*(\d+)\s*(?:\||$)",
    re.MULTILINE,
)


def find_leaks(folder: Path, extra: list[Path] | None = None) -> list[str]:
    """Any owner-style address or token pattern in any file of the dataset folder (and extras)."""
    problems = []
    files = [f for f in sorted(folder.glob("*")) if f.is_file()] + list(extra or [])
    for f in files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        for label, rx in LEAK_SCAN.items():
            if rx.search(text):
                problems.append(f"{f.name}: {label} pattern present")
        for m in ANY_EMAIL.finditer(text):
            if not ALLOWED_EMAIL.search(m.group(0)):
                problems.append(
                    f"{f.name}: an email address that is not a public inbox or example"
                )
                break
    return problems


def branch_names(tables: dict[str, list[dict]]) -> list[str]:
    return [
        b for b in series_of(tables["generations"]) if b and not b.startswith("v1-")
    ]


def genome_at_end(tables: dict[str, list[dict]], branch: str) -> int:
    """Instincts the branch's own line holds at its end.

    Not every row of the instincts table: that pools other lines (a line-0 control never carried
    the v1 instincts). It is the genome at birth of the branch's last generation (which follows
    the branch's parent line: line 14 for v2-h-inherit, line 0 for the control and fresh branches,
    line 25 for v2-main) plus the instincts learned from that last generation's own trial.
    A last generation with no genome_size_at_birth counts only what it learned.
    """
    last = max(
        (g for g in tables["generations"] if g["series"] == branch),
        key=lambda g: g["generation"],
    )
    born = last.get("genome_size_at_birth") or 0
    learned = sum(
        1
        for i in tables["instincts"]
        if i["learned_from_generation"] == last["generation"]
    )
    return born + learned


def branch_numbers(tables: dict[str, list[dict]], branch: str) -> dict:
    part = scope(tables, None, series=branch)
    m = metrics(part)
    return {
        "per_generation": m["per_generation_resistance"],
        "resisted": m["attacks_resisted_total"],
        "false_blocks": m["false_blocks_among_benign"],
        "met": m["attacks_met_total"],
        "instincts_learned_in_branch": m["instincts_learned"],
        "instincts_at_end": genome_at_end(tables, branch),
    }


def check_branches(tables: dict[str, list[dict]], data: Path) -> list[str]:
    """The branch column and branches.json must follow from the generation rows."""
    errors = []
    branch_of = {g["generation"]: g.get("branch") for g in tables["generations"]}
    for g in tables["generations"]:
        if "branch" not in g:
            continue  # an export from before the branch column existed
        want = "v1" if g["scoring_rules"] == "v1" else g["series"]
        if g["branch"] != want:
            errors.append(
                f"gen {g['generation']}: branch {g['branch']!r}, expected {want!r}"
            )
    for name in ("emails", "judgements", "memories"):
        for r in tables[name]:
            if "branch" in r and r["branch"] != branch_of.get(r["generation"]):
                errors.append(
                    f"{name}: item of gen {r['generation']} has branch {r['branch']!r}"
                )
                break
    path = data / "branches.json"
    if not path.exists():
        return errors  # an export from before branches.json existed
    info = json.loads(path.read_text(encoding="utf-8"))
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    meta = manifest.get("other_files", {}).get("branches.json")
    if meta is None or hashlib.sha256(path.read_bytes()).hexdigest() != meta["sha256"]:
        errors.append("branches.json: sha256 differs from manifest.json")
    for b in info:
        gens = sorted(
            g["generation"] for g in tables["generations"] if g["series"] == b["branch"]
        )
        if b["generations_in_data"] != len(gens):
            errors.append(
                f"branches.json {b['branch']}: generations_in_data != {len(gens)}"
            )
        if gens and (
            b["first_generation"] != gens[0] or b["last_generation"] != gens[-1]
        ):
            errors.append(
                f"branches.json {b['branch']}: first/last differ from the rows {gens[0]}-{gens[-1]}"
            )
    return errors


def check_card(card: Path, tables: dict[str, list[dict]]) -> list[str]:
    """Every resisted/met number the card states for a v2 branch must equal the data."""
    if not card.exists():
        return []
    text = card.read_text(encoding="utf-8")
    errors = []
    have = set(branch_names(tables))
    cache: dict[str, dict] = {}
    for m in CARD_ROW.finditer(text):
        branch, which, res, met = (
            m.group(1),
            m.group(2),
            int(m.group(3)),
            int(m.group(4)),
        )
        if branch not in have:
            errors.append(
                f"{branch} has a row in the card but the data has no such branch"
            )
            continue
        nums = cache.setdefault(branch, branch_numbers(tables, branch))
        got = (
            (nums["resisted"], nums["met"])
            if which == "pooled"
            else nums["per_generation"].get(int(which))
        )
        if got != (res, met):
            errors.append(
                f"{branch} {which} says {res}/{met} in the card, data gives {got}"
            )
    for m in CARD_INSTINCTS.finditer(text):
        branch, kind, n = m.group(1), m.group(2), int(m.group(3))
        if branch not in have:
            errors.append(
                f"{branch} has an instincts row in the card but the data has no such branch"
            )
            continue
        nums = cache.setdefault(branch, branch_numbers(tables, branch))
        got = (
            nums["instincts_learned_in_branch"]
            if kind == "instincts"
            else nums["instincts_at_end"]
        )
        if got != n:
            errors.append(f"{branch} {kind} says {n} in the card, data gives {got}")
    return errors


def claim_value(tables: dict[str, list[dict]], c: dict):
    """The value a claim names, or None when it names a branch the data does not hold yet."""
    if "branch" not in c:
        return metrics(
            scope(tables, c.get("through_generation"), c.get("scoring_rules", "v1"))
        )[c["metric"]]
    if c["branch"] not in set(branch_names(tables)):
        return None
    nums = branch_numbers(tables, c["branch"])
    if "generation" in c:
        per = nums["per_generation"].get(c["generation"])
        return list(per) if per else None
    return {
        "attacks_resisted_total": nums["resisted"],
        "attacks_met_total": nums["met"],
        "instincts_at_end": nums["instincts_at_end"],
        "false_blocks_total": nums["false_blocks"],
        "instincts_learned_in_branch": nums["instincts_learned_in_branch"],
    }[c["metric"]]


def table(rows: list[tuple[str, object]]) -> str:
    width = max(len(k) for k, _ in rows)
    return "\n".join(f"  {k.ljust(width)}  {v}" for k, v in rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    ap.add_argument(
        "--card", type=Path, default=DEFAULT_CARD, help="the dataset card (README.md)"
    )
    args = ap.parse_args(argv)

    tables = load(args.data)
    for series in series_of(tables["generations"]):
        rows = [g for g in tables["generations"] if g["series"] == series]
        rules = rows[0]["scoring_rules"]
        print(
            f"\nSeries {series} (scoring rules {rules}; generations {rows[0]['generation']}"
            f" to {rows[-1]['generation']}). Reported on its own; do not compare across series (v2 begins at generation 19)."
        )
        print(
            "Per generation (resisted / attacks met; gate; emails complete; valid for learning)"
        )
        for g in rows:
            print(
                f"  gen {g['generation']:>2} {g['name']!s:<8} {g['attacks_resisted']}/{g['attacks_met']}"
                f"  resistance {'-' if g['resistance'] is None else format(g['resistance'], '.0%'):>4}"
                f"  gate {'ok ' if g['gate_working'] else 'DEAD'}"
                f"  emails {'ok ' if g['emails_complete'] else ('n/a' if g['emails_complete'] is None else 'GAPS')}"
                f"  valid {'yes' if g['valid_for_learning'] else 'no'}"
            )
        part = scope(tables, None, rules, series)
        print(f"Headline numbers recomputed from the files (series {series})")
        print(
            table(
                [
                    (k, v)
                    for k, v in metrics(part).items()
                    if k != "per_generation_resistance"
                ]
            )
        )
    if not any(g["scoring_rules"] == "v2" for g in tables["generations"]):
        print("\nNo v2 rows yet (v2 begins at generation 19): no v2 claims.")
    for b in branch_names(tables):
        n = branch_numbers(tables, b)
        per = ", ".join(
            f"gen {k}: {r}/{m}" for k, (r, m) in n["per_generation"].items()
        )
        print(
            f"\nBranch {b}: {per}; pooled {n['resisted']}/{n['met']};"
            f" false_block (harmless twins blocked) {n['false_blocks']};"
            f" instincts at end {n['instincts_at_end']} ({n['instincts_learned_in_branch']} learned in the branch)"
        )

    failures = [f"manifest: {e}" for e in check_manifest(args.data)]
    failures += [f"consistency: {e}" for e in consistency(tables)]
    failures += [f"branches: {e}" for e in check_branches(tables, args.data)]
    failures += [f"card: {e}" for e in check_card(args.card, tables)]
    failures += [f"leak: {e}" for e in find_leaks(args.data, [args.card])]

    claims = json.loads(args.claims.read_text(encoding="utf-8"))["claims"]
    print(f"\nClaims ({len(claims)}) from {args.claims.name}")
    for c in claims:
        value = claim_value(tables, c)
        if value is None:
            if c.get("requires_branch"):
                print(
                    f"  [skip] {c['id']}: {c['statement']}  (branch not in this export yet)"
                )
                continue
            failures.append(f"claim {c['id']} names data that is not in the export")
            continue
        ok = OPS[c["op"]](value, c["expected"])
        print(
            f"  [{'ok  ' if ok else 'FAIL'}] {c['id']}: {c['statement']}  ({c['metric']} {c['op']} {c['expected']}; got {value})"
        )
        if not ok:
            failures.append(
                f"claim {c['id']} is contradicted: {c['statement']} (got {value})"
            )
    if failures:
        print("\n" + "!" * 70, file=sys.stderr)
        print(f"VERIFICATION FAILED: {len(failures)} problem(s)", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print("!" * 70, file=sys.stderr)
        return 1
    print("\nAll claims hold and all files match their manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
