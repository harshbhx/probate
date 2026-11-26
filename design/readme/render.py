"""Render Probate's README visuals: one design for every GIF and still.

    python3 render.py [banner stats lineage court curve architecture footer tryit memory]

The README uses seven of them (docs/media). The rest are spares in the brand kit (brand/visuals),
drawn in the same design for posts, slides and docs.

Every visual shares one frame (the seal and name, the section, step ticks, and the register line
along the bottom), one type scale and the Night Court colours, so the README reads as one piece.
Scenes are laid out at 960 px wide with no text under 12.5 px, because GitHub shows README images
at about 830 px.

Each scene is an HTML file in scenes/ with a scripted timeline (Web Animations API). The
renderer pauses every animation, steps it to each frame's time, and screenshots it, so frames
are exact. ffmpeg turns the frames into a GIF, and one frame is kept as a PNG poster for readers
who ask for reduced motion. Stills are rendered at 2x. Tokens in the HTML:

    {{BASE}}                fonts, Night Court colours, the frame, faces.css, the timeline helper
    {{HEAD:How it works}}   the frame's header, with the section name
    {{STEPS:4}}             step ticks at the top right; step(i, at) lights one
    {{NOTE:simulated}}      a short note at the top right instead of ticks
    {{REGISTER}}            the register line along the bottom: twelve generations, the last one alive
    {{FACE:3-sealed-idle}}  a family face, rendered from packages/faces
    {{ICON:Gavel}}          a Lucide icon
    {{SEAL}}                the Probate seal, with classes for drawing it in

Needs Playwright with Chromium, ffmpeg, and the npm workspaces installed (for the fonts).
faces.json and faces.css come from faces-entry.tsx (the real faces package, kinfaces):

    cd design/readme && npx esbuild faces-entry.tsx --bundle --platform=node \
      --outfile=/tmp/faces.cjs && node /tmp/faces.cjs

curve.json is `generations` from GET /api/evidence after `make sim`; the curve scene was laid
out from it, so regenerate scenes/curve.html's points if the numbers change.
"""

import asyncio
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
DRAFT = os.environ.get("PROBATE_README_OUT")  # set it to draft everything in one folder instead
DEST = {"readme": REPO / "docs" / "media", "brand": REPO / "brand" / "visuals"}
NM = REPO / "node_modules"
FACES = json.loads((HERE / "faces.json").read_text())
ICONS = json.loads((HERE / "icons.json").read_text())
WORK = pathlib.Path(tempfile.gettempdir()) / "probate-readme-anim"

# name: (width, height, duration ms, loop, device scale, poster ms, where it goes)
# duration 0 is a still (PNG at 2x). loop=False plays once and holds the last frame.
SCENES = {
    "banner": (960, 300, 4200, False, 4 / 3, 4200, "readme"),
    "stats": (960, 250, 0, False, 2, 0, "readme"),
    "tryit": (960, 468, 0, False, 2, 0, "brand"),
    "lineage": (960, 540, 15400, True, 1, 15400, "readme"),
    "court": (960, 540, 8600, True, 1, 8600, "readme"),
    "memory": (960, 540, 9800, True, 1, 9800, "brand"),
    "curve": (960, 540, 5600, True, 1, 5600, "readme"),
    "architecture": (960, 640, 22600, True, 1, 22600, "readme"),
    "footer": (960, 260, 4800, False, 4 / 3, 4800, "readme"),
}
FPS = 25
HOLD = 2.6  # seconds a looping scene rests on its last frame before it starts again

BASE = """
<style>
@font-face { font-family: 'Newsreader'; src: url('file://NM/@fontsource-variable/newsreader/files/newsreader-latin-opsz-normal.woff2') format('woff2'); font-weight: 200 800; }
@font-face { font-family: 'Geist'; src: url('file://NM/@fontsource-variable/geist/files/geist-latin-wght-normal.woff2') format('woff2'); font-weight: 100 900; }
@font-face { font-family: 'Geist Mono'; src: url('file://NM/@fontsource-variable/geist-mono/files/geist-mono-latin-wght-normal.woff2') format('woff2'); font-weight: 100 900; }
:root { --night:#08090c; --night2:#0e1014; --night3:#14161b; --night4:#1a1d23;
  --moon:#edeff3; --silver:#c3c8d1; --mist:#959ca8; --dim:#7e8592; --faint:#4a505b;
  --line:#1f2228; --line2:#2c3038; --gilt:#d9b46a; --life:#5be3a9; --verdict:#ff6b6b; --amber:#f2a93b; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 100%; height: 100%; overflow: hidden; background: var(--night); color: var(--moon);
  font-family: 'Geist', sans-serif; -webkit-font-smoothing: antialiased; }
.serif { font-family: 'Newsreader', serif; font-weight: 400; letter-spacing: -0.015em; }
.mono { font-family: 'Geist Mono', monospace; }
.abs { position: absolute; }
/* The frame every visual shares. */
.fr-head { position: absolute; left: 40px; top: 24px; display: flex; align-items: center; gap: 10px; }
.fr-head .fr-seal { width: 24px; height: 24px; }
.fr-head .fr-name { font: 400 19px/1 'Newsreader', serif; letter-spacing: -0.01em; color: var(--moon); }
.fr-head .fr-sec { margin-left: 4px; padding-left: 13px; border-left: 1px solid var(--line2); font-size: 14px; line-height: 18px; color: var(--mist); }
.fr-steps { position: absolute; right: 40px; top: 35px; display: flex; gap: 6px; }
.fr-steps i { position: relative; width: 20px; height: 3px; border-radius: 2px; background: var(--line2); overflow: hidden; }
.fr-steps i b { position: absolute; inset: 0; background: var(--gilt); opacity: 0; }
.fr-note { position: absolute; right: 40px; top: 27px; font: 13px/18px 'Geist Mono', monospace; color: var(--dim); }
.fr-note.sim { color: var(--amber); }
.fr-reg { position: absolute; left: 40px; right: 40px; bottom: 22px; height: 9px; }
.fr-reg::before { content: ''; position: absolute; left: 0; right: 0; top: 4px; height: 1px; background: var(--line); }
.fr-reg i { position: absolute; top: 0; width: 9px; height: 9px; margin-left: -4.5px; border-radius: 50%; background: var(--night); border: 1.25px solid var(--faint); }
.fr-reg i.live { background: var(--life); border-color: var(--life); }
.fr-foot { position: absolute; left: 40px; right: 40px; bottom: 46px; font-size: 13px; line-height: 18px; color: var(--dim); }
h1.t { position: absolute; left: 40px; top: 72px; font: 400 40px/1.1 'Newsreader', serif; letter-spacing: -0.02em; color: var(--moon); }
p.s { position: absolute; left: 40px; top: 126px; font-size: 16.5px; line-height: 22px; color: var(--mist); }
/* A verdict stamp: approved, convicted or contested. Colour only ever means a verdict. */
.vd { display: inline-block; border: 1.5px solid currentColor; border-radius: 6px; padding: 4px 9px; font: 600 12.5px/1 'Geist Mono', monospace; letter-spacing: .12em; }
.vd.conv { color: var(--verdict); } .vd.appr { color: var(--life); } .vd.cont { color: var(--amber); }
.hide { opacity: 0; }
svg { display: block; }
FACESCSS
</style>
<script>
// A tiny timeline: every call is a Web Animation, so the renderer can step it exactly.
const ALL = (s) => Array.from(document.querySelectorAll(s));
function A(sel, frames, at, dur, easing = 'cubic-bezier(.2,.7,.2,1)') {
  ALL(sel).forEach((el) => el.animate(frames, { delay: at, duration: dur, fill: 'forwards', easing }));
}
const fadeIn = (sel, at, dur = 500) => A(sel, [{ opacity: 0 }, { opacity: 1 }], at, dur, 'ease-out');
const fadeTo = (sel, at, to, dur = 500) => A(sel, [{ opacity: to }], at, dur, 'ease-in-out');
const rise = (sel, at, dur = 600, by = 12) =>
  A(sel, [{ opacity: 0, transform: `translateY(${by}px)` }, { opacity: 1, transform: 'none' }], at, dur);
const pop = (sel, at, dur = 380) =>
  A(sel, [{ opacity: 0, transform: 'scale(.6)' }, { opacity: 1, transform: 'scale(1.08)', offset: .7 }, { opacity: 1, transform: 'scale(1)' }], at, dur, 'ease-out');
const draw = (sel, at, dur = 600, easing = 'cubic-bezier(.4,0,.2,1)') =>
  A(sel, [{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], at, dur, easing);
const stamp = (sel, at, rot = -4) =>
  A(sel, [{ opacity: 0, transform: `rotate(${rot}deg) scale(1.9)` }, { opacity: 1, transform: `rotate(${rot}deg) scale(.96)`, offset: .75 }, { opacity: 1, transform: `rotate(${rot}deg) scale(1)` }], at, 320, 'cubic-bezier(.5,0,.75,0)');
const step = (i, at) => {
  A(`.fr-steps i:nth-child(${i}) b`, [{ opacity: 0 }, { opacity: 1 }], at, 300, 'ease-out');
  if (i > 1) A(`.fr-steps i:nth-child(${i - 1}) b`, [{ opacity: 0.45 }], at, 300, 'ease-out');
};
const type = (sel, at, dur = 700) =>
  A(sel, [{ clipPath: 'inset(0 100% 0 0)', opacity: 1 }, { clipPath: 'inset(0 0 0 0)', opacity: 1 }], at, dur, 'steps(28, end)');
const along = (sel, at, dur, easing = 'cubic-bezier(.45,0,.25,1)') =>
  A(sel, [{ offsetDistance: '0%' }, { offsetDistance: '100%' }], at, dur, easing);
</script>
"""

SEAL = """<svg class="seal" viewBox="0 0 64 64" width="100%" height="100%">
  <circle class="s-ring1 dr" cx="32" cy="32" r="29" fill="none" stroke="var(--gilt)" stroke-width="2.5" pathLength="1"/>
  <circle class="s-ring2 dr" cx="32" cy="32" r="24.5" fill="none" stroke="var(--gilt)" stroke-width="1" opacity="0.7" pathLength="1"/>
  <g fill="none" stroke="var(--moon)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
    <path class="s-b1 dr" d="M32 18.5 V24 H22.5 V30" pathLength="1"/>
    <path class="s-b2 dr" d="M32 24 H41.5 V30" pathLength="1"/>
    <path class="s-b3 dr" d="M22.5 36 V43" pathLength="1"/>
    <path class="s-b4 dr" d="M41.5 36 V38.5" pathLength="1"/>
  </g>
  <g fill="var(--moon)">
    <circle class="s-n1 nd" cx="32" cy="16" r="3.2"/><circle class="s-n2 nd" cx="22.5" cy="33" r="3.2"/>
    <circle class="s-n3 nd" cx="41.5" cy="33" r="3.2"/><circle class="s-n4 nd" cx="22.5" cy="46" r="3.2"/>
  </g>
  <path class="s-strike dr" d="M37.5 44.5 L45.5 40.5" stroke="var(--verdict)" stroke-width="2.6" stroke-linecap="round" pathLength="1"/>
</svg>"""

SEAL_JS = """
function drawSeal(at) {
  draw('.s-ring1', at, 700); draw('.s-ring2', at + 250, 600);
  A('.s-n1', [{ transform: 'scale(0)' }, { transform: 'scale(1.2)', offset: .7 }, { transform: 'scale(1)' }], at + 700, 260, 'ease-out');
  draw('.s-b1', at + 850, 380, 'ease-in-out'); draw('.s-b2', at + 900, 300, 'ease-in-out');
  A('.s-n2, .s-n3', [{ transform: 'scale(0)' }, { transform: 'scale(1.2)', offset: .7 }, { transform: 'scale(1)' }], at + 1200, 240, 'ease-out');
  draw('.s-b3', at + 1400, 220, 'ease-in-out'); draw('.s-b4', at + 1400, 160, 'ease-in-out');
  A('.s-n4', [{ transform: 'scale(0)' }, { transform: 'scale(1.2)', offset: .7 }, { transform: 'scale(1)' }], at + 1600, 240, 'ease-out');
  draw('.s-strike', at + 1950, 180, 'cubic-bezier(.7,0,.3,1)');
}
"""
SEAL_CSS = """
.seal .dr { stroke-dasharray: 1; stroke-dashoffset: 1; }
.seal .nd { transform-box: fill-box; transform-origin: center; transform: scale(0); }
"""


SEAL_STILL = SEAL.replace(' dr"', '"').replace(' nd"', '"').replace('class="seal"', 'class="fr-seal"')
REGISTER = '<div class="fr-reg">' + "".join(
    f'<i{" class=\"live\"" if g == 11 else ""} style="left:{g * 100 / 11:.3f}%"></i>' for g in range(12)
) + "</div>"


def head(section: str) -> str:
    sec = f'<span class="fr-sec">{section}</span>' if section else ""
    return f'<div class="fr-head">{SEAL_STILL}<span class="fr-name">Probate</span>{sec}</div>'


def fill(html: str) -> str:
    base = BASE.replace("NM", str(NM)).replace("FACESCSS", (HERE / "faces.css").read_text())
    html = html.replace("{{BASE}}", base).replace("{{SEAL}}", SEAL).replace("{{SEAL_JS}}", SEAL_JS).replace("{{SEAL_CSS}}", SEAL_CSS)
    html = re.sub(r"\{\{HEAD:([^}]*)\}\}", lambda m: head(m.group(1)), html)
    html = re.sub(r"\{\{STEPS:(\d+)\}\}", lambda m: '<div class="fr-steps">' + "<i><b></b></i>" * int(m.group(1)) + "</div>", html)
    html = re.sub(r"\{\{NOTE:([^}]*)\}\}", lambda m: f'<p class="fr-note{" sim" if "simulated" in m.group(1) else ""}">{m.group(1)}</p>', html)
    html = html.replace("{{REGISTER}}", REGISTER)
    html = re.sub(r"\{\{FACE:([^}]+)\}\}", lambda m: FACES[m.group(1)], html)
    html = re.sub(r"\{\{ICON:([^}]+)\}\}", lambda m: ICONS[m.group(1)], html)
    return html


async def seek(pg, t: float) -> None:
    """Pause every animation on the page at time t (ms)."""
    await pg.evaluate(f"document.getAnimations().forEach(a => {{ a.pause(); a.currentTime = {t}; }})")


async def render(names: list[str]) -> None:
    WORK.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name in names:
            w, h, dur, loop, dsf, poster, where = SCENES[name]
            out = pathlib.Path(DRAFT) if DRAFT else DEST[where]
            out.mkdir(parents=True, exist_ok=True)
            page_file = WORK / f"{name}.html"
            page_file.write_text(fill((HERE / "scenes" / f"{name}.html").read_text()))
            pg = await b.new_page(viewport={"width": w, "height": h}, device_scale_factor=dsf)
            await pg.goto(page_file.as_uri())
            await pg.evaluate("document.fonts.ready")
            await pg.wait_for_timeout(150)

            if not dur:  # a still
                await pg.screenshot(path=str(out / f"{name}.png"))
                print(f"{name}.png  {(out / f'{name}.png').stat().st_size // 1024} KB")
                await pg.close()
                continue
            frames = WORK / f"frames-{name}"
            shutil.rmtree(frames, ignore_errors=True)
            frames.mkdir()
            n = dur * FPS // 1000 + 1
            for i in range(n):
                await seek(pg, i * 1000 / FPS)
                await pg.screenshot(path=str(frames / f"{i:04d}.png"))
            await seek(pg, poster)
            await pg.screenshot(path=str(out / f"{name}.png"))
            hold = HOLD if loop else 1.0
            subprocess.run(
                [
                    "ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(frames / "%04d.png"),
                    "-vf", f"tpad=stop_mode=clone:stop_duration={hold},split[a][b];"
                    "[a]palettegen=max_colors=192:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle",
                    "-loop", "0" if loop else "-1", str(out / f"{name}.gif"),
                ],
                check=True,
            )
            size = (out / f"{name}.gif").stat().st_size // 1024
            print(f"{name}.gif  {n} frames  {size} KB")
            await pg.close()
        await b.close()


if __name__ == "__main__":
    asyncio.run(render(sys.argv[1:] or list(SCENES)))
