"""Measure what the family's instincts do, on every fixture, without any live-inbox noise.

For each fixture of the attack suite (the 16 tricks and their harmless twins, the web pair and,
with --hard, the hard tier) this builds the email the family would receive and asks the gate,
once with the family's inherited instincts and, as the control, with none. A fixture is
"blocked" when the gate resists it. Attacks should be blocked, harmless twins should not.

Run it where the connectors are reachable (the Courthouse Sprite), with the Courthouse's
settings loaded:

    cd app/services/core && set -a && . ./.env && set +a && \
        python3 ../../scripts/evaluate_gate.py --out /home/sprite/gate-evaluation.json

Nothing here reads or writes the family's database except to read its genome.
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

from probate.adapters import world
from probate.common.config import settings
from probate.common.models import Mail
from probate.courthouse.store import Store
from probate.generation.gate import Gate
from probate.suite.fixtures import load_all


def concept_map_for(genome):
    from probate.court.distill import concept_map

    return concept_map(genome)


def mail_for(fx) -> Mail:
    return Mail(
        id=f"eval-{fx.id}",
        inbox="eval",
        sender=f"{fx.sender_role}@example.test",
        subject=fx.subject,
        text=fx.body,
        received_at=datetime.now(UTC),
        attachments=[
            {"name": a.get("name", "file"), "content": a.get("content", "")} for a in fx.attachments
        ],
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--hard", action="store_true", help="include the hard tier")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    store = Store(settings.db_path)
    genome = store.genome()
    w = world(settings, fresh=True)
    fixtures = load_all("both" if args.hard else "base")
    cmap = concept_map_for(genome)
    with_instincts = Gate(w.jev, genome, cmap)
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
            "hard": fx.hard,
            "subject": fx.subject,
            "blocked_with_instincts": r.resisted,
            "instinct": r.instinct,
            "score": round(r.score, 3),
            "judge_error": r.error,
            "blocked_control": c.resisted,
        }

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(run, fixtures.values()))
    rows.sort(key=lambda r: (not r["is_attack"], r["id"]))

    def count(pred):
        return sum(1 for r in rows if pred(r))

    attacks = [r for r in rows if r["is_attack"]]
    benign = [r for r in rows if not r["is_attack"]]
    summary = {
        "when": datetime.now(UTC).isoformat(timespec="seconds"),
        "court_engine": settings.court_engine,
        "instincts": [
            {"name": g.name, "question": g.question, "threshold": g.threshold} for g in genome
        ],
        "fixtures": len(rows),
        "attacks": len(attacks),
        "attacks_blocked": count(lambda r: r["is_attack"] and r["blocked_with_instincts"]),
        "attacks_blocked_by_control": count(lambda r: r["is_attack"] and r["blocked_control"]),
        "harmless": len(benign),
        "harmless_blocked": count(lambda r: not r["is_attack"] and r["blocked_with_instincts"]),
        "judge_errors": count(lambda r: r["judge_error"]),
        "hard_attacks": count(lambda r: r["is_attack"] and r["hard"]),
        "hard_attacks_blocked": count(
            lambda r: r["is_attack"] and r["hard"] and r["blocked_with_instincts"]
        ),
        "hard_harmless": count(lambda r: not r["is_attack"] and r["hard"]),
        "hard_harmless_blocked": count(
            lambda r: not r["is_attack"] and r["hard"] and r["blocked_with_instincts"]
        ),
    }
    Path(args.out).write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
