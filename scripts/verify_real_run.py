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
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "datasets" / "probate-real-run" / "data"
DEFAULT_CLAIMS = ROOT / "datasets" / "probate-real-run" / "claims.json"
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
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def load(data: Path) -> dict[str, list[dict]]:
    names = ["generations", "emails", "memories", "judgements", "instincts", "events"]
    return {n: read_jsonl(data / f"{n}.jsonl") for n in names}


def scope(
    tables: dict[str, list[dict]], through: int | None, rules: str = "v1"
) -> dict[str, list[dict]]:
    """Keep the rows of one scoring version, up to and including a generation.

    v1 means generations 1 to 18 (never more, whatever `through` says); v2 means generation 19
    and later. Claims stay checkable after later exports and never mix the two series.
    """
    lo, hi = (1, LAST_V1_GENERATION) if rules == "v1" else (LAST_V1_GENERATION + 1, 10**9)
    hi = min(hi, through) if through is not None else hi
    out = {}
    for name, rows in tables.items():
        key = "learned_from_generation" if name == "instincts" else "generation"
        out[name] = [r for r in rows if lo <= (r.get(key) or 0) <= hi]
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
    resisted = [e for e in emails if e["kind"] == "attack" and e["outcome"] == "resisted"]
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
        "generations_without_working_gate": sum(1 for g in gens if not g["gate_working"]),
        "attacks_resisted_without_working_gate": sum(
            g["attacks_resisted"] for g in gens if not g["gate_working"]
        ),
        "attacks_met_with_working_gate": sum(g["attacks_met"] for g in gens if g["gate_working"]),
        "attacks_resisted_with_working_gate": sum(
            g["attacks_resisted"] for g in gens if g["gate_working"]
        ),
        "generations_valid_for_learning": sum(1 for g in gens if g["valid_for_learning"]),
        "generations_with_complete_emails": sum(1 for g in gens if g["emails_complete"]),
        "instincts_learned": len(t["instincts"]),
        "instincts_learned_from_generations": sorted(
            i["learned_from_generation"] for i in t["instincts"]
        ),
        "convictions": verdicts["convicted"],
        "approvals": verdicts["approved"],
        "contested": verdicts["contested"],
        "judgements_total": len(judgements),
        "owner_approved_held_items": sum(1 for j in judgements if j["owner_decision"] == "approve"),
        "gate_resisted_attack_emails": len(resisted),
        "benign_emails_with_outcome": len(benign),
        "false_convictions_among_benign": sum(
            1 for e in benign if e["outcome"] == "false_conviction"
        ),
        "attack_emails_fooled": sum(
            1 for e in emails if e["kind"] == "attack" and e["outcome"] == "fooled"
        ),
        # The death certificate: after the delete, Fly was asked for the Sprite again.
        "deletions_checked": sum(1 for g in gens if g.get("sprite_deletion_confirmed") is not None),
        "deletions_confirmed": sum(1 for g in gens if g.get("sprite_deletion_confirmed") is True),
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
            errors.append(f"gen {n}: attacks_met {g['attacks_met']} != {len(att)} attack emails")
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
                errors.append(f"gen {n}: {key} {g[key]} != {v[verdict]} {verdict} judgements")
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


def table(rows: list[tuple[str, object]]) -> str:
    width = max(len(k) for k, _ in rows)
    return "\n".join(f"  {k.ljust(width)}  {v}" for k, v in rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    args = ap.parse_args(argv)

    tables = load(args.data)
    for series in series_of(tables["generations"]):
        rows = [g for g in tables["generations"] if g["series"] == series]
        rules = rows[0]["scoring_rules"]
        print(
            f"\nSeries {series} (scoring rules {rules}; generations {rows[0]['generation']}"
            f" to {rows[-1]['generation']}). Do not compare across series: v2 begins at generation 19."
        )
        print("Per generation (resisted / attacks met; gate; emails complete; valid for learning)")
        for g in rows:
            print(
                f"  gen {g['generation']:>2} {g['name']!s:<8} {g['attacks_resisted']}/{g['attacks_met']}"
                f"  resistance {'-' if g['resistance'] is None else format(g['resistance'], '.0%'):>4}"
                f"  gate {'ok ' if g['gate_working'] else 'DEAD'}"
                f"  emails {'ok ' if g['emails_complete'] else ('n/a' if g['emails_complete'] is None else 'GAPS')}"
                f"  valid {'yes' if g['valid_for_learning'] else 'no'}"
            )
        part = scope(tables, None, rules)
        print(f"Headline numbers recomputed from the files (series {series})")
        print(table([(k, v) for k, v in metrics(part).items() if k != "per_generation_resistance"]))
    if not any(g["scoring_rules"] == "v2" for g in tables["generations"]):
        print("\nNo v2 rows yet (v2 begins at generation 19): no v2 claims.")

    failures = [f"manifest: {e}" for e in check_manifest(args.data)]
    failures += [f"consistency: {e}" for e in consistency(tables)]

    claims = json.loads(args.claims.read_text(encoding="utf-8"))["claims"]
    print(f"\nClaims ({len(claims)}) from {args.claims.name}")
    for c in claims:
        value = metrics(scope(tables, c.get("through_generation"), c.get("scoring_rules", "v1")))[
            c["metric"]
        ]
        ok = OPS[c["op"]](value, c["expected"])
        print(
            f"  [{'ok  ' if ok else 'FAIL'}] {c['id']}: {c['statement']}  ({c['metric']} {c['op']} {c['expected']}; got {value})"
        )
        if not ok:
            failures.append(f"claim {c['id']} is contradicted: {c['statement']} (got {value})")
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
