"""The real-run dataset exporter and verifier (issue #166), on a tiny made-up snapshot."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).parent / "fixtures" / "real_run" / "snapshot-tables.json"
COMMITTED = REPO / "datasets" / "probate-real-run" / "data"
CLAIMS = REPO / "datasets" / "probate-real-run" / "claims.json"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


export = _load("export_real_run")
verify = _load("verify_real_run")

# Fake secrets are assembled at run time so the repository holds no secret-shaped text.
FAKE_KEY = "sk-" + "a1B2" * 8
FAKE_BEARER = "Bearer " + "x9Y8" * 6
FAKE_URL = "https://gen-004-dara.sprites.app/run?" + "tok" + "en=" + "Zq7" * 8
FAKE_CONN = "conn" + "_" + "Ab12Cd34Ef56"

# Independent of the exporter's own patterns: what a reviewer would grep for.
SCAN = {
    "key": re.compile(
        r"\b(sk-[A-Za-z0-9_-]{16,}|hf_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_\w{16,})"
    ),
    "bearer": re.compile(r"Bearer\s+(?!\[)\S{12,}"),
    "url token": re.compile(r"(?i)[?&](token|key|auth)=(?!\[)\w{6,}"),
    "connection id": re.compile(r"(?i)\bconn(ection)?[_-]\w{8,}"),
    "message id": re.compile(r"<[^<>\s@]{6,}@[^<>\s]+>"),
    "owner name": re.compile(r"(?i)\b(harsh|harshu|bhanushali|rishi)\b"),
    "owner mail": re.compile(r"(?i)@(dualmindlab\.tech|gmail\.com)"),
}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
ALLOWED = re.compile(r"^probate-[a-z0-9-]+@agentmail\.to$|@(example\.test|[\w.-]+\.example)$")


def scan_dir(folder: Path) -> list[str]:
    problems = []
    for f in sorted(folder.glob("*")):
        text = f.read_text(encoding="utf-8")
        for label, rx in SCAN.items():
            if rx.search(text):
                problems.append(f"{f.name}: {label}")
        for m in EMAIL.finditer(text):
            if not ALLOWED.search(m.group(0)):
                problems.append(f"{f.name}: email {m.group(0)}")
    return problems


@pytest.fixture
def snapshot() -> dict:
    snap = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # Plant things that must never reach the output.
    snap["will_items"][0]["evidence"] += f" key {FAKE_KEY} {FAKE_BEARER} see {FAKE_URL}"
    snap["will_items"][1]["evidence"] += f" via {FAKE_CONN}, copy bhanushaliharsh434@gmail.com"
    snap["events"][2]["text"] += " Reply to Harshu <HDZMpZdPl0Rmvf6gRp86@dualmindlab.tech>"
    return snap


@pytest.fixture
def out(tmp_path: Path, snapshot: dict) -> Path:
    dest = tmp_path / "data"
    tables = export.build(snapshot, export.Api(), "2026-11-27T00:00:00Z")
    export.write_dataset(tables, dest, {"database_snapshot": "fixture"}, "2026-11-27T00:00:00Z")
    return dest


def rows(out: Path, name: str) -> list[dict]:
    return [json.loads(x) for x in (out / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]


def test_files_counts_and_manifest(out: Path):
    assert len(rows(out, "generations")) == 4
    assert len(rows(out, "emails")) == 13
    assert len(rows(out, "memories")) == 4
    assert len(rows(out, "judgements")) == 4
    assert len(rows(out, "instincts")) == 1
    assert len(rows(out, "events")) == 4
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"]["emails.jsonl"]["rows"] == 13
    assert len(manifest["files"]["events.jsonl"]["sha256"]) == 64
    assert verify.check_manifest(out) == []


def test_era_flags_come_from_birth_times(out: Path):
    g = {r["generation"]: r for r in rows(out, "generations")}
    assert [g[n]["gate_working"] for n in (1, 2, 3, 4)] == [False, False, True, True]
    assert [g[n]["will_reached_court"] for n in (1, 2, 3, 4)] == [False, True, True, True]
    assert [g[n]["learning_step_working"] for n in (1, 2, 3, 4)] == [False, True, True, True]
    assert g[1]["emails_complete"] is True
    assert g[2]["emails_complete"] is False  # agent recorded 2 of 4 suite emails
    assert g[4]["emails_complete"] is None  # still alive
    assert g[3]["valid_for_learning"] is True
    assert g[2]["valid_for_learning"] is False
    assert g[3]["resistance"] == 0.5 and g[1]["resistance"] == 0.0 and g[4]["resistance"] is None
    assert g[1]["lifespan_seconds"] == 614


def test_email_outcomes_and_text(out: Path):
    emails = rows(out, "emails")
    by = {(e["generation"], e["fixture_id"]): e for e in emails}
    assert by[(2, "A1")]["outcome"] == "fooled" and by[(2, "A1")]["outcome_raw"] == "fooled_caught"
    assert by[(3, "A2")]["outcome"] == "resisted"
    assert by[(3, "A2")]["blocked_by_instinct"] == "payment_redirect_fraud"
    assert by[(2, "B1")]["outcome"] == "false_conviction" and by[(2, "B1")]["kind"] == "benign"
    assert by[(4, "B1")]["outcome"] == "pending"
    assert by[(1, "A1")]["body"] and by[(1, "A1")]["family"] == "payment_redirect"


def test_instincts_and_judgements(out: Path):
    ins = rows(out, "instincts")[0]
    assert ins["learned_from_generation"] == 2 and ins["first_carried_by_generation"] == 3
    assert ins["learned_at"] == "2026-11-26T17:50:35Z"
    j = rows(out, "judgements")
    assert {x["court_engine"] for x in j} == {"language-model fallback (not Jev)"}
    assert j[0]["layer1_flags"] == ["new_payment_destination"]
    assert j[0]["layer2_answers"]["untrusted_origin"]["value"] == 0.9
    assert [x["owner_decision"] for x in j] == [None, "approve", None, None]


def test_redaction_removes_owner_and_secrets(out: Path):
    assert scan_dir(out) == []
    text = "".join(f.read_text(encoding="utf-8") for f in out.glob("*"))
    assert "owner@example.test" in text
    assert "probate-stranger@agentmail.to" in text  # the project's public test inbox stays
    assert "probate-friend@agentmail.to" in text
    assert "billing-update@payments-verify.example" in text  # fixture address, reserved TLD
    for secret in (FAKE_KEY, FAKE_BEARER.split()[1], FAKE_CONN, "Zq7Zq7Zq7", "Harsh", "Rishi"):
        assert secret not in text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("mail harsh@dualmindlab.tech now", "mail owner@example.test now"),
        ("a.person@corp.org wrote", "someone@example.test wrote"),
        ("probate-friend@agentmail.to", "probate-friend@agentmail.to"),
        ("other-inbox@agentmail.to", "someone@example.test"),
        ("ask Harsh's team", "ask the owner's team"),
        ("id <010001a2189a6bd3-80e7797f@email.amazonses.com>", "id <message-id-redacted>"),
    ],
)
def test_redact_text(raw: str, expected: str):
    assert export.redact_text(raw) == expected


def test_exporter_refuses_to_write_a_leak(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(export, "redact_obj", lambda o: o)
    tables = {"events": [{"text": "ping " + FAKE_KEY}]}
    with pytest.raises(SystemExit, match="refusing to write"):
        export.write_dataset(tables, tmp_path / "x", {}, "now")


def test_verifier_passes_then_fails_loudly(out: Path, tmp_path: Path, capsys):
    claims = tmp_path / "claims.json"
    good = {
        "claims": [
            {
                "id": "T1",
                "statement": "one attack resisted",
                "metric": "attacks_resisted_total",
                "op": "==",
                "expected": 1,
            },
            {
                "id": "T2",
                "statement": "first resistance in gen 3",
                "metric": "first_resistance_generation",
                "op": "==",
                "expected": 3,
            },
        ]
    }
    claims.write_text(json.dumps(good), encoding="utf-8")
    assert verify.main(["--data", str(out), "--claims", str(claims)]) == 0
    good["claims"][0]["expected"] = 5
    claims.write_text(json.dumps(good), encoding="utf-8")
    assert verify.main(["--data", str(out), "--claims", str(claims)]) == 1
    assert "VERIFICATION FAILED" in capsys.readouterr().err


def test_verifier_catches_edited_data(out: Path, tmp_path: Path):
    path = out / "generations.jsonl"
    path.write_text(
        path.read_text(encoding="utf-8").replace('"attacks_resisted": 1', '"attacks_resisted": 2'),
        encoding="utf-8",
    )
    claims = tmp_path / "c.json"
    claims.write_text(json.dumps({"claims": []}), encoding="utf-8")
    assert verify.main(["--data", str(out), "--claims", str(claims)]) == 1


@pytest.mark.skipif(not (COMMITTED / "manifest.json").exists(), reason="no committed export")
def test_committed_dataset_is_clean_and_claims_hold():
    assert scan_dir(COMMITTED) == []
    assert verify.main(["--data", str(COMMITTED), "--claims", str(CLAIMS)]) == 0


def test_scoring_rules_and_series_columns(out: Path):
    for name in ("generations", "emails", "judgements"):
        for r in rows(out, name):
            assert r["scoring_rules"] == "v1" and r["series"] == "v1-real-run-2026-11-26"
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scoring_rules"]["last_v1_generation"] == 18


def test_scoring_rules_boundary_and_settings():
    assert export.rules_for(18, "v2", "v2-x") == ("v1", export.V1_SERIES)
    assert export.rules_for(19, "v2", "v2-x") == ("v2", "v2-x")
    assert export.rules_for(19) == ("v2", "v2-real-run")
    assert export.scoring_labels({}) == ("v2", "v2-real-run")
    assert export.scoring_labels({"scoring_rules": "V2", "run_label": "night-2"}) == (
        "v2",
        "v2-night-2",
    )


def test_branch_commit_is_carried_into_series_info(tmp_path: Path):
    f = tmp_path / "branches.txt"
    sha = "0123456789abcdef0123456789abcdef01234567"
    f.write_text(
        "\n".join(
            [
                "base,19,,2026-11-28,,env=old-format",  # no commit: ignored
                f"base,19,,2026-11-28,{sha},env=production-v2",
                "control,27,30,2026-11-29,abc1234+dirty,env=x",
                "old,1,2,2026-11-29,env=five-columns",
            ]
        ),
        encoding="utf-8",
    )
    info = export.load_branch_commits(f)
    assert info == {
        "v2-base": {"code_commit": sha},
        "v2-control": {"code_commit": "abc1234+dirty"},
    }
    assert export.load_branch_commits(tmp_path / "missing.txt") == {}
    m = export.write_dataset({}, tmp_path / "out", {}, "now", info)
    assert m["series_info"]["v2-base"]["code_commit"] == sha


def test_branches_file_names_the_series(tmp_path: Path):
    f = tmp_path / "branches.txt"
    lines = [
        "branch,first_gen,last_gen,date,settings",
        "base,19,26,2026-11-28,default",
        "v2-control-no-instincts,27,30,2026-11-29,none",
        "hard-fork,31,34,2026-11-29,hard",
    ]
    f.write_text("\n".join(lines), encoding="utf-8")
    b = export.load_branches(f)
    assert [x[0] for x in b] == ["v2-base", "v2-control-no-instincts", "v2-hard-fork"]
    assert export.rules_for(18, branches=b) == ("v1", export.V1_SERIES)
    assert export.rules_for(19, branches=b) == ("v2", "v2-base")
    assert export.rules_for(32, branches=b) == ("v2", "v2-hard-fork")
    assert export.rules_for(40, branches=b) == ("v2", "v2-real-run")  # not in any branch
    assert export.load_branches(tmp_path / "missing.txt") == []


def test_verifier_scopes_claims_to_v1():
    gens = [
        {"generation": 18, "scoring_rules": "v1", "series": "v1-real-run-2026-11-26"},
        {"generation": 19, "scoring_rules": "v2", "series": "v2-base"},
        {"generation": 20, "scoring_rules": "v2", "series": "v2-hard-fork"},
    ]
    tables = {
        "generations": gens,
        "emails": [{"generation": 19}],
        "instincts": [{"learned_from_generation": 20}],
    }
    v1 = verify.scope(tables, None)
    assert [g["generation"] for g in v1["generations"]] == [18] and v1["emails"] == []
    assert verify.scope(tables, 99)["instincts"] == []  # never leaks past generation 18
    v2 = verify.scope(tables, None, "v2")
    assert [g["generation"] for g in v2["generations"]] == [19, 20] and len(v2["instincts"]) == 1
    base = verify.scope(tables, None, series="v2-base")  # branches are never pooled
    assert [g["generation"] for g in base["generations"]] == [19] and base["instincts"] == []


def test_branch_column_and_branches_json(tmp_path: Path, snapshot: dict):
    bf = tmp_path / "branches.txt"
    sha = "0123456789abcdef0123456789abcdef01234567"
    bf.write_text(
        "\n".join(
            [
                "branch,first_gen,last_gen,date,settings",
                "# a comment, with a comma",
                "v2-first (base tier, trimmed),3,3,2026-11-27,tier=base suite_per_life=4",
                f"v2-h-inherit,4,,2026-11-27,{sha},tier=hard hard_per_life=2 lifespan=300",
            ]
        ),
        encoding="utf-8",
    )
    branches = export.load_branches(bf)
    assert branches == [("v2-first", 3, 3)]
    tables = export.build(snapshot, export.Api(), "now", branches)
    info = export.load_branch_info(bf, tables, {"parent:4": "14"})
    by_name = {b["branch"]: b for b in info}
    assert by_name["v2-h-inherit"]["parent_line"] == 14
    assert by_name["v2-h-inherit"]["learning"] is True  # the design default
    assert by_name["v2-h-inherit"]["code_commit"] == sha
    assert by_name["v2-h-inherit"]["settings"]["hard_per_life"] == "2"
    assert by_name["v2-first"]["first_generation"] == 3
    dest = tmp_path / "data"
    export.write_dataset(tables, dest, {}, "now", None, info)
    for g in tables["generations"]:
        assert g["branch"] == ("v1" if g["scoring_rules"] == "v1" else g["series"])
    for r in tables["memories"] + tables["emails"] + tables["judgements"]:
        assert "branch" in r
    written = {k: rows(dest, k) for k in ("generations", "emails", "judgements", "memories")}
    assert verify.check_branches(written, dest) == []
    assert scan_dir(dest) == []


def test_sqlite_backup_is_read_only(tmp_path: Path, snapshot: dict):
    import sqlite3

    db = tmp_path / "backup.db"
    con = sqlite3.connect(db)
    for table in export.SNAPSHOT_TABLES:
        cols = list(snapshot[table][0])
        con.execute(f"create table {table} ({', '.join(cols)})")
        for row in snapshot[table]:
            con.execute(
                f"insert into {table} values ({','.join('?' * len(cols))})",
                [json.dumps(v) if isinstance(v, (list, dict)) else v for v in row.values()],
            )
    con.execute("create table settings (key, value)")
    con.execute("insert into settings values ('branch', 'v2-x'), ('webhook_secret', 'nope')")
    con.execute("create table judge_mail (id, excerpt)")
    con.commit()
    con.close()
    snap = export.snapshot_from_sqlite(db)
    assert len(snap["generations"]) == len(snapshot["generations"])
    assert [s["key"] for s in snap["settings"]] == ["branch"]  # secrets and visitor tables stay out
    assert "judge_mail" not in snap


def test_verifier_checks_card_numbers_and_leaks(tmp_path: Path):
    gens = [
        {
            "generation": n,
            "scoring_rules": "v2",
            "series": "v2-b",
            "branch": "v2-b",
            "state": "tried",
            "gate_working": True,
            "valid_for_learning": True,
            "emails_complete": True,
            "sprite_deletion_confirmed": None,
            "attacks_met": 2,
            "attacks_resisted": r,
        }
        for n, r in ((20, 2), (21, 0))
    ]
    tables = {
        "generations": gens,
        "emails": [],
        "memories": [],
        "judgements": [],
        "instincts": [{"learned_from_generation": 5}, {"learned_from_generation": 21}],
    }
    card = tmp_path / "README.md"
    card.write_text(
        "| v2-b | 20 | 2/2 |\n| v2-b | 21 | 0/2 |\n| v2-b | pooled | 2/4 |\n"
        "| v2-b | instincts | 1 |\n| v2-b | genome | 2 |\n| v2-c | pooled | TBD |\n",
        encoding="utf-8",
    )
    assert verify.check_card(card, tables) == []
    card.write_text(
        "| v2-b | 21 | 1/2 |\n| v2-b | pooled | 3/4 |\n| v2-z | 20 | 2/2 |\n", encoding="utf-8"
    )
    assert len(verify.check_card(card, tables)) == 3
    clean = tmp_path / "d"
    clean.mkdir()
    (clean / "a.jsonl").write_text('{"x": "probate-ab12@agentmail.to, a@b.example"}\n', "utf-8")
    assert verify.find_leaks(clean) == []
    (clean / "b.json").write_text('{"x": "someone' + '@mail.com"}', encoding="utf-8")
    (clean / "c.json").write_text('{"x": "sk-' + "a1B2" * 8 + '"}', encoding="utf-8")
    assert len(verify.find_leaks(clean)) == 2
