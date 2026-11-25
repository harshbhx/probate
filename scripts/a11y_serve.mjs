// Tiny local servers for scripts/a11y_check.mjs (not part of CI; see docs/ACCESSIBILITY.md).
//
//   node scripts/a11y_serve.mjs --site apps/site/out --web <assembled web dir> [--site-port 4747] [--web-port 4848]
//
// site: static export, with /x served from x.html like the real host (Cloudflare Pages does).
// web:  the Vite build with SPA fallback, plus a stand-in judge API so the Judges page can be shown locked,
//       refused and unlocked: GET /api/live answers {state:"idle"}, and GET /api/judge/status accepts the key
//       "good" and refuses anything else. Reads of everything else come from the snapshot's <route>.json files.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, all) => (v.startsWith('--') ? [...a, [v.slice(2), all[i + 1]]] : a), []));
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp', '.woff2': 'font/woff2', '.txt': 'text/plain', '.xml': 'application/xml' };
const isFile = (f) => fs.existsSync(f) && fs.statSync(f).isFile();
const send = (res, code, file) => {
  res.writeHead(code, { 'content-type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
};
const json = (res, code, body) => {
  res.writeHead(code, { 'content-type': 'application/json' });
  res.end(JSON.stringify(body));
};
// The URL path, normalised so ".." cannot climb out of the folder, and never a malformed escape.
const resolve = (root, url) => {
  let p;
  try {
    p = decodeURIComponent(url.split('?')[0]);
  } catch {
    p = '/';
  }
  return path.posix.normalize('/' + p).replace(/\/$/, '');
};
// A file is only served when it really lives inside the folder being served.
const within = (root, f) => {
  const r = path.resolve(f);
  return r === root || r.startsWith(root + path.sep);
};

if (args.site) {
  const root = path.resolve(args.site);
  http
    .createServer((req, res) => {
      const p = resolve(root, req.url);
      const f = [path.join(root, p), path.join(root, p + '.html'), path.join(root, p, 'index.html')].filter((c) => within(root, c)).find(isFile);
      f ? send(res, 200, f) : send(res, 404, path.join(root, '404.html'));
    })
    .listen(+(args['site-port'] || 4747), '127.0.0.1');
}
if (args.web) {
  const root = path.resolve(args.web);
  http
    .createServer((req, res) => {
      const p = resolve(root, req.url);
      if (p === '/api/live') return json(res, 200, { state: 'idle' });
      if (p === '/api/judge/status') {
        return req.headers['x-probate-key'] === 'good'
          ? json(res, 200, { valid: true, requires_key: true, lives: { per_hour: 3, used_this_hour: 0, remaining_this_hour: 3, next_available_in: 0 }, budget: { daily_cap_usd: 5, used_today_usd: 0.4, remaining_today_usd: 4.6 }, attacks: { per_hour: 20, today: 1 } })
          : json(res, 401, { error: 'invalid_key' });
      }
      const f = path.join(root, p);
      within(root, f) && isFile(f) ? send(res, 200, f) : send(res, 200, path.join(root, 'index.html'));
    })
    .listen(+(args['web-port'] || 4848), '127.0.0.1');
}
console.log('serving', args.site ? `site :${args['site-port'] || 4747}` : '', args.web ? `web :${args['web-port'] || 4848}` : '');
