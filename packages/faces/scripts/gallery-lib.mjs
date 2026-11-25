// Builds gallery.svg from the package itself: twelve generations of the default family,
// each with the one change it inherited. Static (no animation), so it renders anywhere.
import { faceGlyphSvg, inheritedChange, traitsFor } from "../dist/index.js";

const COLS = 6;
const ROWS = 2;
const CELL_W = 150;
const CELL_H = 170;
const PAD = 20;

export function buildGallery({ generations = COLS * ROWS, family } = {}) {
  const width = PAD * 2 + COLS * CELL_W;
  const height = PAD * 2 + 40 + ROWS * CELL_H;
  const cells = [];
  for (let i = 0; i < generations; i++) {
    const gen = i + 1;
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    const x = PAD + col * CELL_W;
    const y = PAD + 40 + row * CELL_H;
    const change = inheritedChange(gen, family) ?? "the founder";
    const t = traitsFor(gen, family);
    const glyphSvg = faceGlyphSvg(family ?? gen, family ? { gen } : {});
    const alt = `Generation ${gen}: ${change}`;
    cells.push(
      `<g transform="translate(${x} ${y})" role="img" aria-label="${alt}">` +
        `<rect x="6" y="0" width="${CELL_W - 12}" height="${CELL_H - 12}" rx="14" fill="#121826" stroke="#232C40"/>` +
        `<g transform="translate(${(CELL_W - 12) / 2 + 6 - 36} 14) scale(1.125)">${glyphSvg}</g>` +
        `<text x="${CELL_W / 2}" y="108" text-anchor="middle" font-size="13" font-weight="600" fill="#E6EAF2" font-family="ui-sans-serif, system-ui, sans-serif">Gen ${gen}</text>` +
        `<text x="${CELL_W / 2}" y="126" text-anchor="middle" font-size="10.5" fill="#8C95AB" font-family="ui-sans-serif, system-ui, sans-serif">${change}</text>` +
        `<text x="${CELL_W / 2}" y="140" text-anchor="middle" font-size="9" fill="#5E6882" font-family="ui-monospace, monospace">${t.head} / ${t.crown}</text>` +
        `</g>`,
    );
  }
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" ` +
    `aria-label="Twelve generations of one family of generated faces. Each generation changes exactly one trait of its parent.">` +
    `<title>kinfaces: twelve generations</title>` +
    `<rect width="${width}" height="${height}" rx="18" fill="#0A0E17"/>` +
    `<text x="${PAD + 6}" y="${PAD + 18}" font-size="15" font-weight="600" fill="#E6EAF2" font-family="ui-sans-serif, system-ui, sans-serif">kinfaces: 12 generations, one inherited change each</text>` +
    cells.join("") +
    `</svg>\n`
  );
}
