// Render the family's faces to PNG for scripts/make_gifs.py (it has no SVG renderer of its own).
//
//   node scripts/render_faces.mjs <out-dir> <family-data.json>
//
// One 160 px PNG per generation, drawn by the kinfaces package exactly as the site draws it: sealed (or unborn for a
// generation that was never born), with the instincts it was born with.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';

const [out, dataPath] = process.argv.slice(2);
if (!out || !dataPath) {
  console.error('usage: node scripts/render_faces.mjs <out-dir> <family-data.json>');
  process.exit(2);
}
const require = createRequire(new URL('../apps/site/package.json', import.meta.url));
const { faceSvg } = await import(new URL('../packages/faces/dist/index.js', import.meta.url));
const sharp = require('sharp');

mkdirSync(out, { recursive: true });
const { generations } = JSON.parse(readFileSync(dataPath, 'utf8'));
for (const g of generations) {
  const svg = faceSvg(
    { gen: g.gen },
    { life: g.state === 'died_early' ? 'unborn' : 'sealed', instincts: g.instinctsAtBirth, size: 160, background: '#14161b' },
  );
  const png = await sharp(Buffer.from(svg)).resize(160, 160).flatten({ background: '#0e1014' }).png().toBuffer();
  writeFileSync(join(out, `gen-${String(g.gen).padStart(2, '0')}.png`), png);
}
console.log(`rendered ${generations.length} faces to ${out}`);
