"""Draw docs/media/results.svg, the README's results chart. Standard library only.

    python scripts/make_results_chart.py

The numbers are typed in ROWS below on purpose: this chart shows what the README states, and the
README's numbers are the ones scripts/verify_real_run.py checks against the dataset (claims.json).
A row with done=False is drawn as an empty dashed track marked "running": no unfinished number is
ever drawn as a result. When a run finishes, set its hits and total, flip done, and re-run.
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "media" / "results.svg"

# (label, note, hits, total, done, colour key)
ROWS = [
    ("v1 real run, working gate", "generations 13 to 16, v1 rules (not comparable with v2)", 9, 18, True, "v1"),
    ("v2-h-inherit", "learning on, born from gen 14 Nadia", 10, 12, True, "inherit"),
    ("v2-h-control", "learning off", 0, 12, True, "control"),
    ("v2-h-fresh", "learning on, no inheritance", None, None, False, "fresh"),
    ("v2-main", "12 generations", None, None, False, "fresh"),
]
COLOURS = {"v1": "#959ca8", "inherit": "#5be3a9", "control": "#e0645c", "fresh": "#d9b46a"}

W, LEFT, BAR_W, ROW_H, TOP = 880, 250, 440, 62, 92


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    h = TOP + ROW_H * len(ROWS) + 70
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" '
        'role="img" aria-labelledby="t d" font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">',
        "<title id=\"t\">Attacks resisted at the door, by branch</title>",
        "<desc id=\"d\">v1 real run with a working gate: 9 of 18. v2-h-inherit: 10 of 12. "
        "v2-h-control: 0 of 12. v2-h-fresh and v2-main are still running, so no result is shown.</desc>",
        f'<rect width="{W}" height="{h}" rx="14" fill="#0e1014"/>',
        '<text x="28" y="40" fill="#f1ece0" font-size="20" font-weight="700">'
        "Attacks resisted at the door</text>",
        '<text x="28" y="64" fill="#959ca8" font-size="13">'
        "Small samples: evidence, not proof. Empty dashed bars are runs still in progress.</text>",
    ]
    for g in (0, 25, 50, 75, 100):
        x = LEFT + BAR_W * g / 100
        p.append(f'<line x1="{x}" y1="{TOP - 8}" x2="{x}" y2="{TOP + ROW_H * len(ROWS) - 14}" '
                 'stroke="#2a2f3a" stroke-width="1"/>')
        p.append(f'<text x="{x}" y="{TOP + ROW_H * len(ROWS) + 6}" fill="#959ca8" font-size="12" '
                 f'text-anchor="middle">{g}%</text>')
    for i, (label, note, hits, total, done, key) in enumerate(ROWS):
        y = TOP + i * ROW_H
        p.append(f'<text x="28" y="{y + 16}" fill="#f1ece0" font-size="15" font-weight="600">{esc(label)}</text>')
        p.append(f'<text x="28" y="{y + 34}" fill="#959ca8" font-size="11">{esc(note)}</text>')
        p.append(f'<rect x="{LEFT}" y="{y}" width="{BAR_W}" height="26" rx="5" fill="#161a21"/>')
        if done:
            w = BAR_W * hits / total
            if w > 0:
                p.append(f'<rect x="{LEFT}" y="{y}" width="{w:.1f}" height="26" rx="5" fill="{COLOURS[key]}"/>')
            p.append(f'<text x="{LEFT + BAR_W + 14}" y="{y + 19}" fill="#f1ece0" font-size="15" '
                     f'font-weight="600">{hits} of {total}</text>')
        else:
            p.append(f'<rect x="{LEFT + 1}" y="{y + 1}" width="{BAR_W - 2}" height="24" rx="5" fill="none" '
                     f'stroke="{COLOURS[key]}" stroke-width="1.5" stroke-dasharray="6 5"/>')
            p.append(f'<text x="{LEFT + BAR_W + 14}" y="{y + 19}" fill="#d9b46a" font-size="14">'
                     "running</text>")
    p.append("</svg>")
    OUT.write_text("\n".join(p) + "\n", encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
