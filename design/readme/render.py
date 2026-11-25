"""Render Probate's README animations.

    python3 render.py [intro lineage court curve architecture outro]

Each scene is an HTML file in scenes/ with a scripted timeline (Web Animations API). The
renderer pauses every animation, steps it to each frame's time, and screenshots it, so frames
are exact. ffmpeg turns the frames into a GIF. Tokens in the HTML:

    {{BASE}}            fonts, Night Court colours, faces.css, the timeline helper
    {{FACE:3-sealed-idle}}  a family face, rendered from packages/faces
    {{ICON:Gavel}}      a Lucide icon
    {{SEAL}}            the Probate seal, with classes for drawing it in

Needs Playwright with Chromium, ffmpeg, and the npm workspaces installed (for the fonts).
faces.json comes from faces-entry.tsx (the real packages/faces component):

    npx esbuild design/readme/faces-entry.tsx --bundle --platform=node --jsx=automatic \
      --outfile=/tmp/faces.cjs && (cd design/readme && node /tmp/faces.cjs)

curve.json is `generations` from GET /api/evidence after `make sim`; the curve scene was laid
out from it, so regenerate scenes/curve.html's points if the numbers change.
"""

import asyncio
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = REPO / "docs" / "media"
NM = REPO / "node_modules"
FACES = json.loads((HERE / "faces.json").read_text())
ICONS = json.loads((HERE / "icons.json").read_text())
WORK = pathlib.Path(tempfile.gettempdir()) / "probate-readme-anim"

# name: (width, height, duration ms, loop)  loop=False plays once and holds the last frame.
SCENES = {
    "intro": (1200, 520, 7000, False),
    "lineage": (1200, 600, 16000, True),
    "court": (1200, 580, 10000, True),
    "curve": (1200, 580, 7500, True),
    "architecture": (1200, 760, 22000, True),
    "outro": (1200, 440, 6000, False),
}
FPS = 25

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


def fill(html: str) -> str:
    base = BASE.replace("NM", str(NM)).replace("FACESCSS", (REPO / "packages/faces/src/faces.css").read_text())
    html = html.replace("{{BASE}}", base).replace("{{SEAL}}", SEAL).replace("{{SEAL_JS}}", SEAL_JS).replace("{{SEAL_CSS}}", SEAL_CSS)
    html = re.sub(r"\{\{FACE:([^}]+)\}\}", lambda m: FACES[m.group(1)], html)
    html = re.sub(r"\{\{ICON:([^}]+)\}\}", lambda m: ICONS[m.group(1)], html)
    return html


async def render(names: list[str]) -> None:
    WORK.mkdir(exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name in names:
            w, h, dur, loop = SCENES[name]
            page_file = WORK / f"{name}.html"
            page_file.write_text(fill((HERE / "scenes" / f"{name}.html").read_text()))
            pg = await b.new_page(viewport={"width": w, "height": h})
            await pg.goto(page_file.as_uri())
            await pg.evaluate("document.fonts.ready")
            await pg.wait_for_timeout(150)
            frames = WORK / f"frames-{name}"
            shutil.rmtree(frames, ignore_errors=True)
            frames.mkdir()
            n = dur * FPS // 1000 + 1
            for i in range(n):
                t = i * 1000 / FPS
                await pg.evaluate(f"document.getAnimations().forEach(a => {{ a.pause(); a.currentTime = {t}; }})")
                await pg.screenshot(path=str(frames / f"{i:04d}.png"))
            hold = 0.1 if loop else 1.0
            subprocess.run(
                [
                    "ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(frames / "%04d.png"),
                    "-vf", f"tpad=stop_mode=clone:stop_duration={hold},scale=960:-1:flags=lanczos,split[a][b];"
                    "[a]palettegen=max_colors=160:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle",
                    "-loop", "0" if loop else "-1", str(OUT / f"{name}.gif"),
                ],
                check=True,
            )
            size = (OUT / f"{name}.gif").stat().st_size // 1024
            print(f"{name}.gif  {n} frames  {size} KB")
            await pg.close()
        await b.close()


if __name__ == "__main__":
    asyncio.run(render(sys.argv[1:] or list(SCENES)))
