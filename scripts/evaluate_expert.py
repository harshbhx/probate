"""Measure the gate on the opt-in expert tier (E1 to E36), the way evaluate_gate.py does for the rest.

For each expert fixture this builds the email (attachments included), asks the gate with the
family's inherited instincts and, as the control, with none, and reports attacks blocked and
harmless twins wrongly blocked. No published number uses this tier yet.

It needs live connectors (the judge model), so run it where they are reachable, with the
Courthouse's settings loaded, for example on the Courthouse Sprite:

    cd app/services/core && set -a && . ./.env && set +a && \
        python3 ../../scripts/evaluate_expert.py --out /home/sprite/expert-evaluation.json

Without connectors it prints a clear message and exits with status 2. `--list` only lists the
fixtures and needs nothing. It never touches the family's database except to read its genome.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "core"))

from probate.suite.fixtures import load_expert


def mail_for(fx):
    from probate.common.models import Mail

    return Mail(
        id=f"eval-{fx.id}",
        inbox="eval",
        sender=f"{fx.sender_role}@example.test",
        subject=fx.subject,
        text=fx.body,
        received_at=datetime.now(UTC),
        attachments=[
            {"name": a.get("name", "file"), "content": a.get("content", "")}
            for a in fx.attachments
        ],
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="where to write the JSON result")
    ap.add_argument(
        "--list", action="store_true", help="list the expert fixtures and exit"
    )
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    fixtures = load_expert()
    if args.list:
        for f in fixtures.values():
            kind = "attack" if f.is_attack else "twin"
            print(
                f"{f.id:4} {kind:6} {f.language:12} {f.family:22} {f.title or f.subject}"
            )
        return 0
    if not args.out:
        ap.error("--out is required unless --list is given")

    try:
        from probate.adapters import world
        from probate.common.config import settings
        from probate.court.distill import concept_map
        from probate.courthouse.store import Store
        from probate.generation.gate import Gate

        store = Store(settings.db_path)
        genome = store.genome()
        w = world(settings, fresh=True)
    except Exception as exc:  # noqa: BLE001 - any missing connector or setting ends here
        print(
            "evaluate_expert.py needs live connectors (judge model, settings and the family's "
            f"database) and could not start: {type(exc).__name__}: {exc}\n"
            "Run it where they are reachable (see the docstring), or use --list.",
            file=sys.stderr,
        )
        return 2

    with_instincts = Gate(w.jev, genome, concept_map(genome))
    control = Gate(w.jev, [], {})

    def run(fx):
        m = mail_for(fx)
        r = with_instincts.check(m)
        c = control.check(m)
        return {
            "id": fx.id,
            "family": fx.family,
            "language": fx.language,
            "is_attack": fx.is_attack,
            "twin_id": fx.twin_id,
            "blocked_with_instincts": r.resisted,
            "instinct": r.instinct,
            "score": round(r.score, 3),
            "judge_error": r.error,
            "blocked_control": c.resisted,
        }

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(run, fixtures.values()))
    attacks = [r for r in rows if r["is_attack"]]
    benign = [r for r in rows if not r["is_attack"]]
    summary = {
        "when": datetime.now(UTC).isoformat(timespec="seconds"),
        "court_engine": settings.court_engine,
        "instincts": [{"name": g.name, "question": g.question} for g in genome],
        "attacks": len(attacks),
        "attacks_blocked": sum(r["blocked_with_instincts"] for r in attacks),
        "attacks_blocked_by_control": sum(r["blocked_control"] for r in attacks),
        "harmless": len(benign),
        "harmless_blocked": sum(r["blocked_with_instincts"] for r in benign),
        "judge_errors": sum(bool(r["judge_error"]) for r in rows),
    }
    Path(args.out).write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
