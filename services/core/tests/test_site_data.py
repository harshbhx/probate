"""The website's /data page numbers (apps/site/lib/generated/family-data.json) equal the verifier's claims."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLAIMS = REPO / "datasets" / "probate-real-run" / "claims.json"
DATA = REPO / "datasets" / "probate-real-run" / "data"
SITE_JSON = REPO / "apps" / "site" / "lib" / "generated" / "family-data.json"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


make = _load("make_site_data")
verify = _load("verify_real_run")
site = json.loads(SITE_JSON.read_text(encoding="utf-8"))
claims = json.loads(CLAIMS.read_text(encoding="utf-8"))["claims"]
by_branch = {b["branch"]: b for b in site["branches"]}


def test_committed_json_is_current():
    assert SITE_JSON.read_text(encoding="utf-8") == make.render(), (
        "run python scripts/make_site_data.py"
    )


def test_every_branch_claim_equals_the_site_numbers():
    checked = 0
    for c in claims:
        if "branch" not in c or c["branch"] not in by_branch:
            continue
        b = by_branch[c["branch"]]
        m, gen = c["metric"], str(c.get("generation"))
        if m == "per_generation_resistance":
            got = b["perGeneration"].get(gen)
            assert got == c["expected"], c["id"]
        elif m == "attacks_resisted_total":
            got = b["resisted"]
            assert got == c["expected"], c["id"]
        elif m == "attacks_met_total":
            got = b["met"]
            assert got == c["expected"], c["id"]
        elif m == "instincts_at_end":
            got = b["instinctsAtEnd"]
            assert got == c["expected"], c["id"]
        elif m == "instincts_at_start":
            got = b["instinctsAtStart"]
            assert got == c["expected"], c["id"]
        elif m == "instincts_learned_in_branch":
            got = b["instinctsLearned"]
            assert got == c["expected"], c["id"]
        elif m == "false_blocks_total":
            got = b["falseBlocks"]
            assert got == c["expected"], c["id"]
        elif m == "generations_died_early":
            got = b["diedEarly"]
            assert got == c["expected"], c["id"]
        elif m == "generations_tried":
            got = b["generationsTried"]
            assert got == c["expected"], c["id"]
        elif m == "judge_outage_events":
            outages = b["judgeOutages"]
            got = outages.get(gen, 0) if "generation" in c else sum(outages.values())
            assert got == c["expected"], c["id"]
        else:
            continue
        checked += 1
    assert checked >= 40  # the per-generation, total, instinct and outage claims of four branches


def test_headline_numbers_are_the_published_ones():
    got = {n: (b["resisted"], b["met"]) for n, b in by_branch.items()}
    assert got == {
        "v2-h-inherit": (10, 12),
        "v2-h-control": (0, 12),
        "v2-h-fresh": (5, 12),
        "v2-main": (17, 22),
    }
    assert (site["v1"]["resistedWorkingGate"], site["v1"]["metWorkingGate"]) == (9, 18)
    assert site["totals"]["generations"] == 49
    assert site["neverBornGenerations"] == [42]
    assert site["judgeOutageGenerations"] == [24, 36, 37]
    assert site["falseBlockGenerations"] == [43]


def test_generations_match_the_dataset_rows():
    rows = verify.read_jsonl(DATA / "generations.jsonl")
    assert [g["gen"] for g in site["generations"]] == [r["generation"] for r in rows]
    for g, r in zip(site["generations"], rows, strict=True):
        assert (g["met"], g["resisted"], g["falseBlocks"], g["branch"]) == (
            r["attacks_met"],
            r["attacks_resisted"],
            r["false_blocks"],
            r["branch"],
        )


def test_wilson_interval_is_the_textbook_value():
    lo, hi = make.wilson(5, 12)
    assert (lo, hi) == (0.1933, 0.6805)
    assert make.wilson(0, 12)[0] == 0.0
    assert make.wilson(0, 0) is None


def test_no_email_address_in_the_site_data():
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", SITE_JSON.read_text(encoding="utf-8"))
