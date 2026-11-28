"""Write the trimmed JSON the website's /data page and docs charts are built from.

    python scripts/make_site_data.py          # rewrite apps/site/lib/generated/family-data.json
    python scripts/make_site_data.py --check  # exit 1 if the committed file is out of date

Reads datasets/probate-real-run/data/*.jsonl and branches.json, and takes every count from the
verifier (scripts/verify_real_run.py), so the site shows the numbers the verifier recomputes.
Adds Wilson 95% score intervals (z = 1.96) for each branch's resisted/attacks. Writes no text
that was typed by hand and no email address. Standard library only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets" / "probate-real-run" / "data"
OUT = ROOT / "apps" / "site" / "lib" / "generated" / "family-data.json"
Z = 1.96  # Wilson 95% interval

spec = importlib.util.spec_from_file_location(
    "verify_real_run", ROOT / "scripts" / "verify_real_run.py"
)
verify = importlib.util.module_from_spec(spec)
sys.modules["verify_real_run"] = verify
spec.loader.exec_module(verify)

COMPARED = ["v2-h-inherit", "v2-h-control", "v2-h-fresh", "v2-main"]
WHAT_DIFFERS = {
    "v2-h-inherit": "Learning on, born from generation 14 (Nadia), so it inherits her instincts",
    "v2-h-control": "No learning",
    "v2-h-fresh": "Learning on, started from nothing",
    "v2-main": "Learning on, born from generation 25 (Yara, 6 inherited instincts), on newer code",
}


def wilson(k: int, n: int, z: float = Z) -> tuple[float, float] | None:
    """Wilson score interval for k successes in n trials, as fractions (None when n is 0)."""
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)


def offline() -> dict:
    """Offline gate evaluation (run 5), every count recomputed from the raw per-fixture rows."""
    ge = verify.load_gate_eval(verify.DEFAULT_GATE_EVAL)
    pn = {name: verify.phase_numbers(rows) for name, rows in ge.items()}

    def repeats(phases: list[str]) -> list[dict]:
        return [
            {
                "blocked": pn[p]["attacks_blocked"],
                "harmlessBlocked": pn[p]["harmless_blocked"],
            }
            for p in phases
        ]

    def genome(name: str, phases: list[str], instincts: int | None) -> dict:
        return {"genome": name, "instincts": instincts, "repeats": repeats(phases)}

    t = verify.load(DATA)
    n_inherit = sum(
        1
        for i in t["instincts"]
        if i["learned_from_generation"] in verify.GENOME_LEARNED_FROM["inherit"]
    )
    n_fresh = sum(
        1
        for i in t["instincts"]
        if i["learned_from_generation"] in verify.GENOME_LEARNED_FROM["fresh"]
    )
    fix, exp = pn["prod_inherit_r1"], pn["exp_inherit"]

    def control(phase: str) -> dict:
        rows = ge[phase]
        return {
            "blocked": sum(1 for r in rows if r["is_attack"] and r["blocked_control"]),
            "harmlessBlocked": sum(
                1 for r in rows if not r["is_attack"] and r["blocked_control"]
            ),
        }

    return {
        "run": "run-5",
        "date": "2026-11-28",
        "fixtures70": {
            "attacks": fix["attacks_total"],
            "harmless": fix["harmless_total"],
            "genomes": [
                genome("inherit", ["prod_inherit_r1", "prod_inherit_r2"], n_inherit),
                genome("fresh", ["prod_fresh_r1", "prod_fresh_r2"], n_fresh),
                {
                    "genome": "control",
                    "instincts": 0,
                    "repeats": [control("prod_inherit_r1")],
                },
            ],
        },
        "expert": {
            "attacks": exp["attacks_total"],
            "harmless": exp["harmless_total"],
            "genomes": [
                genome("inherit", ["exp_inherit"], n_inherit),
                genome("fresh", ["exp_fresh"], n_fresh),
                {
                    "genome": "control",
                    "instincts": 0,
                    "repeats": [control("exp_inherit")],
                },
            ],
        },
        "judges": {
            "haikuAlone": pn["cmp_haiku_inherit"]["attacks_blocked"],
            "gptOssAlone": pn["cmp_gptoss_inherit"]["attacks_blocked"],
            "haikuAloneErrors": pn["cmp_haiku_inherit"]["judge_errors"],
        },
        "note": "Supporting evidence, not the headline. The 70 fixtures contain the tricks the instincts were learned from, so that score is optimistic; the expert tier is the unseen test.",
    }


def build() -> dict:
    t = verify.load(DATA)
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    branches_json = {
        b["branch"]: b
        for b in json.loads((DATA / "branches.json").read_text(encoding="utf-8"))
    }
    gens = sorted(t["generations"], key=lambda g: g["generation"])

    outages: dict[int, int] = {}
    for e in t["events"]:
        if (
            e["kind"] == "gate"
            and e["generation"]
            and "could not ask the judge" in e["text"]
        ):
            outages[e["generation"]] = outages.get(e["generation"], 0) + 1

    out_gens = []
    for g in gens:
        out_gens.append(
            {
                "gen": g["generation"],
                "name": g["name"],
                "branch": g["branch"],
                "rules": g["scoring_rules"],
                "state": g["state"],
                "born": g["born_at"],
                "died": g["died_at"],
                "lifeSeconds": g["lifespan_seconds"],
                "met": g["attacks_met"],
                "resisted": g["attacks_resisted"],
                "falseBlocks": g["false_blocks"],
                "instinctsAtBirth": g["genome_size_at_birth"] or 0,
                "newInstinct": bool(g["new_instinct_at_birth"]),
                "cause": g["cause_of_death"],
                "gateWorking": bool(g["gate_working"]),
                "judgeOutages": outages.get(g["generation"], 0),
            }
        )

    instincts = [
        {
            "name": i["name"],
            "learnedFrom": i["learned_from_generation"],
            "firstCarriedBy": i["first_carried_by_generation"],
        }
        for i in sorted(
            t["instincts"], key=lambda i: (i["learned_from_generation"], i["name"])
        )
    ]

    branches = []
    for name in COMPARED:
        n = verify.branch_numbers(t, name)
        info = branches_json[name]
        branches.append(
            {
                "branch": name,
                "whatDiffers": WHAT_DIFFERS[name],
                "firstGen": info["first_generation"],
                "lastGen": info["last_generation"],
                "learning": info["learning"],
                "codeCommit": (info["code_commit"] or "")[:7],
                "generationsTried": n["generations_tried"],
                "diedEarly": n["generations_died_early"],
                "resisted": n["resisted"],
                "met": n["met"],
                "rate": round(n["resisted"] / n["met"], 4),
                "wilson95": wilson(n["resisted"], n["met"]),
                "perGeneration": {
                    str(k): list(v) for k, v in sorted(n["per_generation"].items())
                },
                "instinctsAtStart": n["instincts_at_start"],
                "instinctsAtEnd": n["instincts_at_end"],
                "instinctsLearned": n["instincts_learned_in_branch"],
                "falseBlocks": n["false_blocks"],
                "judgeOutages": {
                    str(k): v for k, v in sorted(n["judge_outages"].items())
                },
            }
        )

    v1 = verify.scope(t, None, "v1")
    v1m = verify.metrics(v1)
    working = [g for g in v1["generations"] if g["gate_working"]]
    met_w = sum(g["attacks_met"] for g in working)
    res_w = sum(g["attacks_resisted"] for g in working)
    v1_block = {
        "branch": "v1",
        "generations": f"1 to {verify.LAST_V1_GENERATION}",
        "generationsTried": v1m["generations_tried"],
        "workingGateFrom": min(g["generation"] for g in working),
        "resistedWorkingGate": res_w,
        "metWorkingGate": met_w,
        "wilson95WorkingGate": wilson(res_w, met_w),
        "attacksResistedWithoutWorkingGate": v1m[
            "attacks_resisted_without_working_gate"
        ],
        "generationsWithoutWorkingGate": v1m["generations_without_working_gate"],
    }

    claims = json.loads(
        (ROOT / "datasets" / "probate-real-run" / "claims.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        "about": "Generated by scripts/make_site_data.py from datasets/probate-real-run/data. Do not edit by hand.",
        "dataset": {
            "name": manifest["dataset"],
            "exportedAt": manifest["exported_at"],
            "hf": "https://huggingface.co/datasets/harshbhx/probate-real-run",
            "publishedRelease": "beta-2",
            "pendingRelease": "beta-3",
            "claimsChecked": len(claims["claims"]),
        },
        "totals": {
            "generations": len(gens),
            "tried": sum(1 for g in gens if g["state"] == "tried"),
            "instincts": len(instincts),
        },
        "wilsonNote": "Wilson score interval, 95% (z = 1.96), computed by scripts/make_site_data.py from resisted and attacks.",
        "generations": out_gens,
        "instincts": instincts,
        "branches": branches,
        "v1": v1_block,
        "offline": offline(),
        "judgeOutageGenerations": sorted(outages),
        "falseBlockGenerations": [g["gen"] for g in out_gens if g["falseBlocks"]],
        "neverBornGenerations": [
            g["gen"] for g in out_gens if g["state"] == "died_early"
        ],
    }


def render() -> str:
    text = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        raise SystemExit(
            "refusing to write: the output contains something shaped like an email address"
        )
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--check", action="store_true", help="fail if the committed JSON is out of date"
    )
    args = ap.parse_args()
    text = render()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT} is out of date: run python scripts/make_site_data.py")
            return 1
        print("site data is up to date")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
