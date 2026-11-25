// Pre-renders the family faces for the README scenes from the real faces package (kinfaces).
import { writeFileSync } from 'node:fs';
import { FACE_CSS, faceGlyphSvg } from '../../packages/faces/src/index';

const out: Record<string, string> = {};
const instincts = [0, 2, 3, 4, 5, 5, 5, 5, 5, 5, 5, 6];
for (let g = 1; g <= 12; g++) {
  for (const life of ['alive', 'sealed'] as const) {
    for (const mood of ['idle', 'fooled', 'alert', 'happy'] as const) {
      const inner = faceGlyphSvg(g, { life, mood, instincts: instincts[g - 1], animate: true });
      out[`${g}-${life}-${mood}`] = `<svg viewBox="0 0 64 64" width="64" height="64" style="overflow:visible">${inner}</svg>`;
    }
  }
}
writeFileSync('faces.json', JSON.stringify(out));
writeFileSync('faces.css', FACE_CSS);
console.log(Object.keys(out).length);
