"""Render the README's and the video's GIFs from the real run's data. Offline: Pillow plus node (sharp).

    python scripts/make_gifs.py

Reads apps/site/lib/generated/family-data.json (make it with scripts/make_site_data.py), has
scripts/render_faces.mjs draw the family's faces with the kinfaces package, and writes into docs/media/ (the README's
folder) and apps/site/public/media/ (the /data page):

    family-growing.gif      faces appearing generation by generation, a resistance bar per branch
    resistance-curves.gif   each branch's running share of attacks resisted, drawing itself

Each is 800 px wide, a 12 second loop and under 2.5 MB. A last-frame PNG (family-growing-still.png and so on) is
written to the site folder for readers who ask for reduced motion. Colours are the site's tokens.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "apps" / "site" / "lib" / "generated" / "family-data.json"
OUT_DIRS = [ROOT / "docs" / "media", ROOT / "apps" / "site" / "public" / "media"]
MAX_BYTES = 2_500_000

W, H = 800, 450
SS = 2  # draw at 2x, shrink with a smooth filter
FRAME_MS = 100
FRAMES = 106  # 105 frames of 100 ms, then a 1.5 s hold on the last: a 12 second loop

BG = "#0e1014"
PANEL = "#14161b"
LINE = "#2c3038"
MOON = "#edeff3"
SILVER = "#c3c8d1"
MIST = "#959ca8"
GILT = "#d9b46a"
LIFE = "#5be3a9"
AMBER = "#f2a93b"
COLORS = {
    "v1": "#959ca8",
    "v2-first-generation": "#959ca8",
    "v2-h-inherit": "#5be3a9",
    "v2-h-control": "#e0645c",
    "v2-h-fresh": "#d9b46a",
    "v2-main": "#7fb2ff",
}
LABELS = {
    "v1": "v1",
    "v2-first-generation": "v2 gen 19",
    "v2-h-inherit": "v2-h-inherit",
    "v2-h-control": "v2-h-control",
    "v2-h-fresh": "v2-h-fresh",
    "v2-main": "v2-main",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    f = ImageFont.load_default(size=size * SS)
    if bold:
        with contextlib.suppress(
            OSError, ValueError
        ):  # the bundled font has no variations in some builds
            f.set_variation_by_name("Bold")
    return f


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", (W * SS, H * SS), BG)
    return im, ImageDraw.Draw(im)


def text(d: ImageDraw.ImageDraw, xy, s: str, f, fill=MOON, anchor="la") -> None:
    d.text((xy[0] * SS, xy[1] * SS), s, font=f, fill=fill, anchor=anchor)


def finish(im: Image.Image) -> Image.Image:
    return im.resize((W, H), Image.LANCZOS)


def save_gif(frames: list[Image.Image], name: str) -> None:
    # One shared palette keeps colours steady from frame to frame and the file small.
    base = frames[-1].quantize(
        colors=48, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    )
    pal = [f.quantize(palette=base, dither=Image.Dither.NONE) for f in frames]
    durations = [FRAME_MS] * len(pal)
    durations[-1] = FRAME_MS * 15  # linger on the full picture before the loop restarts
    tmp = ROOT / "scripts" / f".{name}.tmp.gif"
    pal[0].save(
        tmp,
        save_all=True,
        append_images=pal[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=1,
    )
    size = tmp.stat().st_size
    if size > MAX_BYTES:
        tmp.unlink()
        raise SystemExit(f"{name}.gif is {size} bytes, over the {MAX_BYTES} byte limit")
    for out in OUT_DIRS:
        out.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp, out / f"{name}.gif")
        if (
            out.parent.name == "public"
        ):  # the still is only for the site's reduced-motion readers
            frames[-1].save(out / f"{name}-still.png", optimize=True)
    tmp.unlink()
    print(f"{name}.gif: {size / 1e6:.2f} MB, {len(frames)} frames")


def header(d, title: str, sub: str) -> None:
    text(d, (28, 22), title, font(26, True), MOON)
    text(d, (28, 56), sub, font(15), MIST)


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def family_growing(data: dict, faces: Path) -> None:
    gens = data["generations"]
    rows = [
        ("v1", "v1 (older rules)"),
        ("v2-first-generation", "v2 first"),
        ("v2-h-inherit", "v2-h-inherit"),
        ("v2-h-control", "v2-h-control"),
        ("v2-h-fresh", "v2-h-fresh"),
        ("v2-main", "v2-main"),
    ]
    by_row = {k: [g for g in gens if g["branch"] == k] for k, _ in rows}
    pngs = {
        g["gen"]: Image.open(faces / f"gen-{g['gen']:02d}.png").convert("RGB")
        for g in gens
    }
    top, row_h = 92, 56
    label_x, strip_x = 28, 160
    bar_x, bar_w = 640, 80
    start, per = 5, 2  # frame a generation first appears, frames per generation
    frames = []
    for f in range(FRAMES - 1):
        im, d = canvas()
        header(
            d,
            "The family, in numbers",
            "49 generations, one face each, by branch. Bar: attacks resisted at the door.",
        )
        shown = [g for g in gens if start + (g["gen"] - 1) * per <= f]
        for r, (key, label) in enumerate(rows):
            y = top + r * row_h
            d.line(
                [(28 * SS, (y - 8) * SS), ((W - 28) * SS, (y - 8) * SS)],
                fill=LINE,
                width=SS,
            )
            text(d, (label_x, y + 17), label, font(15, True), COLORS[key], "lm")
            step = min(38, (bar_x - strip_x - 12) // len(by_row[key]))
            face = step - 2
            for i, g in enumerate(by_row[key]):
                x = strip_x + i * step
                born_at = start + (g["gen"] - 1) * per
                cx, cy = (x + face / 2) * SS, (y + face / 2) * SS
                if born_at <= f:
                    k = min(1.0, (f - born_at + 1) / 2)
                    sz = int(face * SS * (0.55 + 0.45 * ease(k)))
                    pic = pngs[g["gen"]].resize((sz, sz), Image.LANCZOS)
                    im.paste(pic, (int(cx - sz / 2), int(cy - sz / 2)))
                    if f - born_at < 2:
                        d.ellipse(
                            [
                                cx - sz / 2 - 3 * SS,
                                cy - sz / 2 - 3 * SS,
                                cx + sz / 2 + 3 * SS,
                                cy + sz / 2 + 3 * SS,
                            ],
                            outline=GILT,
                            width=2 * SS,
                        )
                    if g["judgeOutages"]:
                        d.ellipse(
                            [
                                cx + (face / 2 - 3) * SS,
                                cy - (face / 2 + 2) * SS,
                                cx + (face / 2 + 4) * SS,
                                cy - (face / 2 - 5) * SS,
                            ],
                            fill=AMBER,
                        )
                else:
                    d.ellipse(
                        [
                            cx - face / 2 * SS,
                            cy - face / 2 * SS,
                            cx + face / 2 * SS,
                            cy + face / 2 * SS,
                        ],
                        outline=LINE,
                        width=SS,
                    )
            rr = [
                g for g in by_row[key] if g in shown and g["gateWorking"]
            ]  # v1: only lives with a working gate
            met = sum(g["met"] for g in rr)
            res = sum(g["resisted"] for g in rr)
            d.rounded_rectangle(
                [bar_x * SS, (y + 11) * SS, (bar_x + bar_w) * SS, (y + 23) * SS],
                radius=6 * SS,
                fill=PANEL,
            )
            if met:
                w = max(int(bar_w * res / met), 4)
                d.rounded_rectangle(
                    [bar_x * SS, (y + 11) * SS, (bar_x + w) * SS, (y + 23) * SS],
                    radius=6 * SS,
                    fill=COLORS[key],
                )
                text(
                    d,
                    (bar_x + bar_w + 10, y + 17),
                    f"{res} of {met}",
                    font(14, True),
                    MOON,
                    "lm",
                )
        # footer key
        fy = H - 26
        d.ellipse([28 * SS, (fy - 4) * SS, 36 * SS, (fy + 4) * SS], fill=AMBER)
        text(d, (42, fy), "judge outage (gens 24, 36, 37)", font(13), MIST, "lm")
        text(d, (290, fy), "dark face: gen 42, never born", font(13), MIST, "lm")
        text(
            d,
            (W - 28, fy),
            "v1 bar: gens 13 to 18 only. Evidence, not proof",
            font(13),
            MIST,
            "rm",
        )
        frames.append(finish(im))
    # the final frame, in full
    frames.append(frames[-1])
    save_gif(frames, "family-growing")


def curves(data: dict) -> None:
    order = ["v2-h-inherit", "v2-h-control", "v2-h-fresh", "v2-main"]
    series = {}
    for b in data["branches"]:
        pts, met, res = [], 0, 0
        for r, m in b["perGeneration"].values():
            if m == 0:
                continue  # a life that never met an attack (generation 42)
            met += m
            res += r
            pts.append(res / met)
        series[b["branch"]] = (pts, b["resisted"], b["met"])
    left, right, top, bot = 92, 210, 104, H - 62
    n = max(len(p) for p, _, _ in series.values())
    px = lambda i: left + (W - left - right) * i / (n - 1)
    py = lambda v: bot - (bot - top) * v
    start, end = 6, 90
    frames = []
    for f in range(FRAMES - 1):
        im, d = canvas()
        header(
            d,
            "Resistance, branch by branch",
            "Share of attacks resisted so far, life by life (v2, hard attacks).",
        )
        for v in (0, 0.5, 1):
            d.line(
                [(left * SS, py(v) * SS), ((W - right) * SS, py(v) * SS)],
                fill=LINE,
                width=SS,
            )
            text(d, (left - 12, py(v)), f"{int(v * 100)}%", font(14), MIST, "rm")
        for i in range(0, n, 2):
            text(d, (px(i), bot + 14), str(i + 1), font(13), MIST, "mm")
        text(d, (left, bot + 38), "Life number within the branch", font(13), MIST)
        t = ease((f - start) / (end - start))
        for key in order:
            pts, res, met = series[key]
            color = COLORS[key]
            reach = t * (len(pts) - 1)
            xy = []
            for i, v in enumerate(pts):
                if i <= reach:
                    xy.append((px(i), py(v)))
            if int(reach) + 1 < len(pts) and reach > int(reach):
                i0 = int(reach)
                fr = reach - i0
                xy.append((px(i0 + fr), py(pts[i0] + (pts[i0 + 1] - pts[i0]) * fr)))
            if len(xy) >= 2:
                d.line(
                    [(x * SS, y * SS) for x, y in xy],
                    fill=color,
                    width=4 * SS,
                    joint="curve",
                )
            if xy:
                for x, y in xy[:-1] if len(xy) > 1 else []:
                    d.ellipse(
                        [(x - 3) * SS, (y - 3) * SS, (x + 3) * SS, (y + 3) * SS],
                        fill=color,
                    )
                x, y = xy[-1]
                d.ellipse(
                    [(x - 6) * SS, (y - 6) * SS, (x + 6) * SS, (y + 6) * SS],
                    fill=color,
                    outline=BG,
                    width=2 * SS,
                )
        # end labels, spread so they never overlap
        ends = []
        for key in order:
            pts, res, met = series[key]
            reach = t * (len(pts) - 1)
            i = min(int(reach), len(pts) - 1)
            fr = reach - i
            v = pts[i] if i == len(pts) - 1 else pts[i] + (pts[i + 1] - pts[i]) * fr
            ends.append([key, py(v)])
        ends.sort(key=lambda e: e[1])
        for j in range(1, len(ends)):
            if ends[j][1] - ends[j - 1][1] < 38:
                ends[j][1] = ends[j - 1][1] + 38
        for key, y in ends:
            pts, res, met = series[key]
            lx = W - right + 18
            text(d, (lx, y - 8), LABELS[key], font(15, True), COLORS[key], "lm")
            if t >= 1:
                text(d, (lx, y + 11), f"{res} of {met}", font(14), MOON, "lm")
        text(
            d,
            (W - 28, H - 24),
            "v2-main ran on newer code; evidence, not proof",
            font(13),
            MIST,
            "rm",
        )
        frames.append(finish(im))
    frames.append(frames[-1])
    save_gif(frames, "resistance-curves")


def main() -> int:
    if not DATA.exists():
        print("run python scripts/make_site_data.py first", file=sys.stderr)
        return 1
    data = json.loads(DATA.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["node", str(ROOT / "scripts" / "render_faces.mjs"), tmp, str(DATA)],
            check=True,
        )
        family_growing(data, Path(tmp))
    curves(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
