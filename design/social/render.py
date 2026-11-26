"""Renders the GitHub social preview card (design/social-preview.png, 1280x640) from preview.html.

Run from the repo root after `npm install`: python design/social/render.py
Upload the PNG in GitHub: Settings > General > Social preview.
"""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
fonts = REPO / "node_modules/@fontsource-variable"
faces = json.loads((REPO / "design/readme/faces.json").read_text())
html = (HERE / "preview.html").read_text()
html = html.replace("{{NEWSREADER}}", (fonts / "newsreader/files/newsreader-latin-opsz-normal.woff2").as_uri())
html = html.replace("{{GEIST}}", (fonts / "geist/files/geist-latin-wght-normal.woff2").as_uri())
html = html.replace("{{FACESCSS}}", (REPO / "design/readme/faces.css").read_text())
html = html.replace("{{LOGO}}", (REPO / "design/logo-mark-night.svg").read_text())
row = [faces[f"{g}-sealed-idle"] for g in range(1, 7)] + [faces["7-alive-happy"]]
html = html.replace("{{FACES}}", "".join(f'<div class="f{" live" if i == 6 else ""}">{s}</div>' for i, s in enumerate(row)))
(HERE / ".preview.out.html").write_text(html)

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1280, "height": 640}, device_scale_factor=1)
    page.goto((HERE / ".preview.out.html").as_uri())
    page.wait_for_timeout(600)
    page.evaluate("document.getAnimations().forEach(a => { a.pause(); a.currentTime = 0; })")
    page.screenshot(path=str(REPO / "design/social-preview.png"))
    b.close()
(HERE / ".preview.out.html").unlink()
print("design/social-preview.png")
