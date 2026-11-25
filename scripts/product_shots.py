"""Capture the landing page's product shots from the live site running locally.

    make sim && make serve      # the simulated family on http://localhost:8080
    python scripts/product_shots.py

Writes 2x WebP screenshots to apps/site/public/product/. They show a simulated run, and the
landing page says so under each one. Needs Playwright (pip install playwright; playwright
install chromium) and Pillow.
"""

import asyncio
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parent.parent / "apps/site/public/product"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"

# name, path, top of the crop and its height in CSS pixels at a 1280 px wide window
SHOTS = [
    ("trial", "/trial/1", 0, 860),
    ("register", "/", 1230, 600),
    ("curve", "/evidence", 600, 560),
    ("heatmap", "/evidence", 1150, 700),
    ("instincts", "/instincts", 206, 1080),
    ("generation", "/gen/3", 0, 1060),
    ("living", "/gen/12", 0, 1000),
]


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 860}, device_scale_factor=2, reduced_motion="reduce"
        )
        page = await ctx.new_page()
        for name, path, top, height in SHOTS:
            await page.goto(BASE + path, wait_until="networkidle")
            await page.wait_for_timeout(1200)
            png = await page.screenshot(
                clip={"x": 0, "y": top, "width": 1280, "height": height},
                full_page=True,
                animations="disabled",
            )
            img = Image.open(io.BytesIO(png)).convert("RGB")
            img.save(OUT / f"{name}.webp", quality=82, method=6)
            print(f"{name}: {img.width}x{img.height}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
