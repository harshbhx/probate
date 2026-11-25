"""Rebuild data/attack_suite.jsonl from source/suite-v1.json.

    python datasets/probate-attack-suite/build.py [--check]

Standard library only. All file I/O is UTF-8 (fixture A6 contains zero-width characters).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source" / "suite-v1.json"
OUT = HERE / "data" / "attack_suite.jsonl"


def twin_of(fid: str) -> str:
    return ("B" if fid.startswith("A") else "A") + fid[1:]


def rows() -> list[dict]:
    suite = json.loads(SOURCE.read_text(encoding="utf-8"))
    out = []
    for f in suite["fixtures"]:
        exp = f.get("expected", {})
        out.append(
            {
                "id": f["id"],
                "twin_id": twin_of(f["id"]),
                "family": f["family"],
                "language": f["language"],
                "is_attack": f["is_attack"],
                "sender_role": f["sender_role"],
                "subject": f["subject"],
                "body": f["body"],
                "attachments": f.get("attachments", []),
                "note": f.get("note", ""),
                "expected_verdict": exp.get("verdict", ""),
                "expected_layer1": exp.get("layer1", []),
                "expected_model_flags": exp.get("jev", []),
                "expected_disk": exp.get("disk", []),
                "suite_version": suite["version"],
            }
        )
    return out


def render() -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows())


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current.replace("\r\n", "\n") != text:
            print("attack_suite.jsonl is out of date")
            return 1
        return 0
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {OUT} ({len(text.splitlines())} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
