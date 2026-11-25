// Runs after `next build` (npm "postbuild"). Turns the static export into something a strict Content Security
// Policy can protect, without changing what the pages do:
//
//  1. Suspense boundaries that React streamed out of order (<template id="B:n"> + a hidden <div id="S:n"> + an
//     inline $RC() call) are put back in place, the same markup React writes for an in-order boundary. This is
//     what keeps the lazily hydrated landing sections visible without JavaScript.
//  2. The per-page inline scripts (the flight data and the chunk bootstrap) are moved into one small external
//     file per page, loaded with `defer` (so it runs before DOMContentLoaded, in the original order). With no
//     inline script left that differs per page, the CSP needs no nonce and no per-page hash.
//  3. The few inline scripts that are identical on many pages (theme, dismissed banner) stay inline and are
//     allowed by sha256 in script-src.
//  4. Next writes its prefetch segments as __next.a/b/c.txt but requests __next.a.b.c.txt: write the dotted
//     copy too, so prefetching and client navigation stop answering 404.
//  5. <link rel=preload> for the Latin web fonts the pages paint with, and the CSP written into out/_headers.
//
// Usage: node scripts/postbuild.mjs [outDir]   (default ./out)
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const out = path.resolve(process.argv[2] ?? 'out');
if (!fs.existsSync(path.join(out, 'index.html'))) throw new Error(`no export found in ${out}`);

const sha = (s, enc = 'hex') => createHash('sha256').update(s).digest(enc);
const htmlFiles = [];
(function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p);
    else if (e.name.endsWith('.html')) htmlFiles.push(p);
  }
})(out);

// ---- 4. dotted prefetch segment copies
let dotted = 0;
(function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (!e.isDirectory()) continue;
    if (e.name.startsWith('__next.')) {
      (function copy(sub, rel) {
        for (const f of fs.readdirSync(sub, { withFileTypes: true })) {
          const fp = path.join(sub, f.name);
          if (f.isDirectory()) copy(fp, `${rel}.${f.name}`);
          else {
            const target = path.join(dir, `${rel}.${f.name}`);
            if (!fs.existsSync(target)) {
              fs.copyFileSync(fp, target);
              dotted++;
            }
          }
        }
      })(p, e.name);
    } else if (e.name !== '_next') walk(p);
  }
})(out);

// ---- fonts to preload: the Latin faces the CSS declares
const mediaDir = path.join(out, '_next/static/media');
const mediaFiles = fs.existsSync(mediaDir) ? fs.readdirSync(mediaDir) : [];
const fontUrl = (prefix) => {
  const f = mediaFiles.find((n) => n.startsWith(prefix) && n.endsWith('.woff2'));
  return f ? `/_next/static/media/${f}` : null;
};
const FONTS = [fontUrl('geist-latin-wght-normal'), fontUrl('newsreader-latin-opsz-normal')].filter(Boolean);
const FONT_LINKS = FONTS.map((u) => `<link rel="preload" href="${u}" as="font" type="font/woff2" crossorigin=""/>`).join('');

// ---- 1-3, 5 per page
const KEEP_INLINE = new Map(); // base64 sha256 -> script text kept inline
// Tolerant of case and of whitespace or attributes in the closing tag (`</SCRIPT >`), so no inline script slips past the CSP step.
const RE_SCRIPT = /<script\b([^>]*)>([\s\S]*?)<\/script\s*[^>]*>/gi;
const RE_MOVE = /^\s*(\(self\.__next_f|self\.__next_f|\(globalThis\["TURBOPACK"\])/;
const MARK = '\u0000MOVED\u0000';
let outlined = 0;
let external = 0;

for (const file of htmlFiles) {
  let html = fs.readFileSync(file, 'utf8');

  // 1. put out-of-order Suspense boundaries back in place (the fallback, if any, is replaced by the content)
  const contents = new Map();
  html = html.replace(
    /<div hidden id="S:(\d+)">([\s\S]*?)<\/div><script>(?:(?!<\/script>)[\s\S])*?\$RC\("B:\1","S:\1"\)<\/script>/g,
    (_m, n, content) => {
      contents.set(n, content);
      return '';
    },
  );
  for (const [n, content] of contents) {
    const open = `<!--$?--><template id="B:${n}"></template>`;
    const start = html.indexOf(open);
    if (start < 0) throw new Error(`${file}: no placeholder for boundary B:${n}`);
    // find the matching <!--/$-->, skipping nested boundaries in the fallback
    const tok = /<!--\$[?!]?-->|<!--\/\$-->/g;
    tok.lastIndex = start + open.length;
    let depth = 1;
    let end = -1;
    for (let t; (t = tok.exec(html)); ) {
      depth += t[0] === '<!--/$-->' ? -1 : 1;
      if (depth === 0) {
        end = t.index + t[0].length;
        break;
      }
    }
    if (end < 0) throw new Error(`${file}: boundary B:${n} is not closed`);
    html = html.slice(0, start) + `<!--$-->${content}<!--/$-->` + html.slice(end);
    outlined++;
  }
  if (/\$RC\(|<template id="B:/.test(html)) throw new Error(`${file}: unresolved Suspense boundary left`);
  html = html.replace(/<script>requestAnimationFrame\(function\(\)\{\$RT=performance\.now\(\)\}\);?<\/script>/, '');

  // 2 + 3. inline scripts
  const moved = [];
  html = html.replace(RE_SCRIPT, (m, attrs, body) => {
    if (/\ssrc=/.test(attrs)) return m;
    const type = /\stype="([^"]*)"/.exec(attrs)?.[1];
    if (type && !/^(text|application)\/javascript$|^module$/.test(type)) return m; // data blocks are not executed
    if (RE_MOVE.test(body)) {
      moved.push(body);
      return MARK;
    }
    KEEP_INLINE.set(sha(body, 'base64'), body);
    return m;
  });
  if (moved.length) {
    const code = moved.join(';\n');
    const name = `${sha(code).slice(0, 16)}.js`;
    fs.mkdirSync(path.join(out, '_next/static/inline'), { recursive: true });
    fs.writeFileSync(path.join(out, '_next/static/inline', name), code);
    let placed = false;
    html = html.split(MARK).join('\u0001').replace(/\u0001/g, () => {
      if (placed) return '';
      placed = true;
      return `<script src="/_next/static/inline/${name}" defer=""></script>`;
    });
    external++;
  }

  // 5. font preload
  if (FONT_LINKS && !html.includes('rel="preload" href="/_next/static/media/')) {
    html = /<meta charSet="utf-8"\/>/.test(html)
      ? html.replace(/<meta charSet="utf-8"\/>/, (m) => `${m}${FONT_LINKS}`)
      : html.replace('<head>', () => `<head>${FONT_LINKS}`);
  }

  fs.writeFileSync(file, html);
}

// ---- CSP
const origin = (u) => {
  try {
    return u ? new URL(u).origin : '';
  } catch {
    return '';
  }
};
const live = origin(process.env.NEXT_PUBLIC_LIVE_URL);
const hashes = [...KEEP_INLINE.keys()].sort().map((h) => `'sha256-${h}'`);
const csp = [
  `default-src 'self'`,
  `script-src 'self' ${hashes.join(' ')}`.trim(),
  `style-src 'self' 'unsafe-inline'`, // React and the scroll effects write style="" attributes, which cannot be hashed
  `img-src 'self' data: blob:`,
  `font-src 'self'`,
  // The footer asks the live family who is alive. The Cloudflare tag manager (Zaraz) that the zone injects
  // sends Google Analytics hits from the browser, so its hosts are allowed here too.
  `connect-src 'self'${live ? ` ${live}` : ''} https://stats.g.doubleclick.net https://www.google-analytics.com https://region1.google-analytics.com https://analytics.google.com https://www.google.com/ads/ga-audiences`,
  `media-src 'self'`,
  `manifest-src 'self'`,
  `worker-src 'self' blob:`,
  `object-src 'none'`,
  `base-uri 'self'`,
  `form-action 'self'`,
  `frame-ancestors 'none'`,
].join('; ');

const headersFile = path.join(out, '_headers');
let headers = fs.readFileSync(headersFile, 'utf8');
if (!headers.includes('__CSP__')) throw new Error('out/_headers has no __CSP__ placeholder');
headers = headers.replace('__CSP__', () => csp);
const longest = Math.max(...headers.split('\n').map((l) => l.length));
if (longest > 2000) throw new Error(`a _headers line is ${longest} characters; Cloudflare allows 2000`);
fs.writeFileSync(headersFile, headers);

console.log(
  `postbuild: ${htmlFiles.length} pages, ${outlined} suspense boundaries inlined, ${external} pages with an external bootstrap, ` +
    `${dotted} prefetch segment copies, ${hashes.length} inline script hash(es), CSP ${csp.length} chars`,
);
