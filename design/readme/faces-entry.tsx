import { renderToStaticMarkup } from 'react-dom/server';
import { FaceGlyph } from '../../packages/faces/src/face';
import { writeFileSync } from 'node:fs';
const out: Record<string, string> = {};
const instincts = [0, 2, 3, 4, 5, 5, 5, 5, 5, 5, 5, 6];
for (let g = 1; g <= 12; g++) {
  for (const life of ['alive', 'sealed'] as const) {
    for (const mood of ['idle', 'fooled', 'alert', 'happy'] as const) {
      const inner = renderToStaticMarkup(<FaceGlyph gen={g} life={life} mood={mood} instincts={instincts[g - 1]} />);
      out[`${g}-${life}-${mood}`] = `<svg viewBox="0 0 64 64" width="64" height="64" style="overflow:visible">${inner}</svg>`;
    }
  }
}
writeFileSync('faces.json', JSON.stringify(out));
console.log(Object.keys(out).length);
