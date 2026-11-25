"""Write real court output for the landing page's "Try the court" widget.

    services/core/.venv/bin/python scripts/export_site_data.py

Runs the actual layer-1 code checks (probate/court/layer1.py) on test emails from the suite and
writes apps/site/lib/generated/court-examples.json. Nothing is hand-written: if the court
changes, re-run this and the site changes with it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "core"))

from probate.common.config import load_owner
from probate.common.models import Source
from probate.court import layer1
from probate.suite.fixtures import LANGUAGE_NAMES

PICK = ["A2", "B2", "A3", "B3", "A13", "B13", "A6", "B6", "A16", "B16"]
OUT = ROOT / "apps" / "site" / "lib" / "generated" / "court-examples.json"


def main() -> None:
    suite = json.loads((ROOT / "fixtures" / "suite-v1.json").read_text(encoding="utf-8"))
    fixtures = {f["id"]: f for f in (suite["fixtures"] if isinstance(suite, dict) else suite)}
    owner = load_owner()
    roles = {"unknown_sender": Source.UNKNOWN_SENDER, "trusted_contact": Source.TRUSTED_CONTACT, "user": Source.USER}
    out = []
    for fid in PICK:
        f = fixtures[fid]
        source = roles.get(f["sender_role"], Source.UNKNOWN_SENDER)
        flags = layer1.check_text(f["body"], source, owner)
        names = sorted({fl.check for fl in flags})
        out.append(
            {
                "id": fid,
                "isAttack": f["is_attack"],
                "family": f["family"].replace("_", " "),
                "language": LANGUAGE_NAMES.get(f["language"], f["language"]),
                "sender": {"unknown_sender": "an unknown sender", "trusted_contact": "a trusted contact", "user": "the owner"}.get(
                    f["sender_role"], f["sender_role"]
                ),
                "subject": f["subject"],
                "body": f["body"],
                "gloss": re.sub(r"^(English gloss|German|Spanish|Hinglish):\s*", "", f.get("note") or "")
                if f["language"] != "en"
                else None,
                "flags": [layer1.PLAIN_WORDS.get(n, n) for n in names],
                # Layer 1 convicts on any flag; otherwise the item goes on to Jev.
                "layer1": "convicted" if names else "to_jev",
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(out)} emails)")
    for e in out:
        print(f"  {e['id']:4} {e['language']:9} {e['layer1']:10} {', '.join(e['flags'])}")


if __name__ == "__main__":
    main()
