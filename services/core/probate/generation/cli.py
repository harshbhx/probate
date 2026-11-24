"""Control commands the Courthouse runs inside a generation Sprite through the exec API.

Each command prints exactly one JSON line. Usage: python -m probate.generation.cli <command>
Commands: status, baseline, will, evidence, stats, log
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from probate.adapters import world
from probate.common.models import Inheritance
from probate.generation.agent import GenerationAgent

WORKDIR = Path("/home/sprite/app")


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    inh = Inheritance.model_validate_json((WORKDIR / "inheritance.json").read_text())
    agent = GenerationAgent(inh, WORKDIR, world(), real_body=True)
    if cmd == "status":
        out = {"state": "living", "gen": inh.gen, "name": inh.name, "emails": agent.stats["emails"]}
    elif cmd == "baseline":
        out = agent.body.baseline()
        (WORKDIR / "baseline.json").write_text(json.dumps(out))
    elif cmd == "will":
        (WORKDIR / "STOP").write_text("dying")
        out = agent.write_will()
    elif cmd == "evidence":
        base = json.loads((WORKDIR / "baseline.json").read_text())
        out = agent.body.evidence(base)
    elif cmd == "stats":
        out = agent.stats
    elif cmd == "log":
        out = {"log": agent.life_log()}
    else:
        out = {"error": f"unknown command {cmd}"}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
