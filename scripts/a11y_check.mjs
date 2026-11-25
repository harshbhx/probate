// Repeatable axe-core pass against local builds. Not part of CI; see docs/ACCESSIBILITY.md.
//
//   node scripts/a11y_check.mjs --site http://127.0.0.1:4747 --web http://127.0.0.1:4848 \
//        [--axe path/to/axe.min.js] [--chrome path/to/chrome] [--json out.json] [--verbose]
//
// Needs Node 22+ (global WebSocket/fetch), a system Chrome, and axe-core. axe-core is not a repo
// dependency: install it anywhere (`npm i axe-core` in a scratch folder) and pass --axe, or set
// AXE_PATH. Serve apps/site/out and a static-preview build of apps/web with scripts/a11y_serve.mjs first
// (docs/ACCESSIBILITY.md has the whole recipe).
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const args = Object.fromEntries(
  process.argv.slice(2).reduce((a, v, i, all) => (v.startsWith('--') ? [...a, [v.slice(2), all[i + 1]?.startsWith('--') || all[i + 1] === undefined ? true : all[i + 1]]] : a), []),
);
const site = args.site || 'http://127.0.0.1:4747';
const web = args.web || 'http://127.0.0.1:4848';
const axePath = args.axe || process.env.AXE_PATH;
const chromePath =
  args.chrome ||
  process.env.CHROME_PATH ||
  ['C:/Program Files/Google/Chrome/Application/chrome.exe', '/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find(existsSync);
if (!axePath || !existsSync(axePath)) throw new Error('Pass --axe <path to axe.min.js> (or AXE_PATH); install axe-core outside the repo.');
if (!chromePath) throw new Error('Chrome not found; pass --chrome.');
const axeSource = readFileSync(axePath, 'utf8');

const PAGES = [
  [site, '/', 'landing /'],
  [site, '/docs', 'docs /docs'],
  [site, '/docs/journey', 'docs /docs/journey'],
  [site, '/docs/for-judges', 'docs /docs/for-judges'],
  [site, '/docs/reference/api', 'docs /docs/reference/api'],
  [web, '/', 'web /'],
  [web, '/trial/3', 'web /trial/3'],
  [web, '/gen/3', 'web /gen/3'],
  [web, '/instincts', 'web /instincts'],
  [web, '/evidence', 'web /evidence'],
  [web, '/judges', 'web /judges (locked)'],
  [web, '/judges', 'web /judges (key refused)', () => typeKey('bad')],
  [web, '/judges', 'web /judges (unlocked)', () => typeKey('good')],
];
const VIEWPORTS = [
  { name: 'mobile 390x844', width: 390, height: 844, mobile: true, dsf: 2 },
  { name: 'desktop 1440x900', width: 1440, height: 900, mobile: false, dsf: 1 },
];

const port = 9600 + Math.floor(Math.random() * 300);
const profile = mkdtempSync(join(tmpdir(), 'a11y-'));
const chrome = spawn(chromePath, ['--headless=new', `--remote-debugging-port=${port}`, '--hide-scrollbars', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let targets;
for (let i = 0; i < 60; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.length) break; } catch { /* retry */ }
  await sleep(250);
}
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map();
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d.result ?? d.error); pending.delete(d.id); } };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(`page script failed: ${r.exceptionDetails.exception?.description ?? r.exceptionDetails.text}`);
  return r.result?.value;
};

// Judges page states: needs the stand-in judge API from scripts/a11y_serve.mjs (key "good" unlocks).
async function typeKey(key) {
  await ev(`document.getElementById('judge-key').focus()`);
  await send('Input.insertText', { text: key });
  await ev(`document.querySelector('form button[type=submit]').click()`);
  await sleep(1200);
}

const results = [];
try {
  await send('Page.enable');
  for (const vp of VIEWPORTS) {
    await send('Emulation.setDeviceMetricsOverride', { width: vp.width, height: vp.height, deviceScaleFactor: vp.dsf, mobile: vp.mobile });
    await send('Emulation.setTouchEmulationEnabled', { enabled: vp.mobile });
    for (const [base, path, label, setup] of PAGES) {
      await send('Storage.clearDataForOrigin', { origin: new URL(base).origin, storageTypes: 'all' }); // forget any judge key
      await send('Page.navigate', { url: base + path });
      await sleep(2500);
      if (await ev(`/Not in the register|could not be found|404/i.test(document.body.innerText.slice(0,400))`)) throw new Error(`${label} rendered a not-found page; is the server mapping /x to x.html?`);
      if (setup) await setup();
      // Scroll through once so reveal-on-scroll content is painted, and finish at the bottom so the pinned
      // statement (lit by scroll position) is in its final state when axe measures colour.
      await ev(`(async()=>{const h=document.documentElement.scrollHeight;for(let y=0;y<h;y+=400){scrollTo(0,y);await new Promise(r=>setTimeout(r,40));}scrollTo(0,h);await new Promise(r=>setTimeout(r,800));})()`);
      await send('Runtime.evaluate', { expression: axeSource });
      if ((await ev('typeof axe')) !== 'object') throw new Error(`axe did not load on ${label}`);
      const out = await ev(`axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}}).then(r=>r.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n=>({target:n.target.join(' '),summary:n.failureSummary.slice(0,240)}))})))`);
      if (!Array.isArray(out)) throw new Error(`axe returned nothing on ${label}`);
      results.push({ page: label, viewport: vp.name, violations: out ?? [] });
      const nodes = (out ?? []).reduce((a, v) => a + v.nodes.length, 0);
      console.log(`${vp.name.padEnd(17)} ${label.padEnd(26)} rules=${(out ?? []).length} nodes=${nodes}`);
      if (args.verbose) for (const v of out ?? []) { console.log(`   [${v.impact}] ${v.id}: ${v.help}`); for (const n of v.nodes.slice(0, 5)) console.log(`      ${n.target}\n         ${n.summary}`); }
    }
  }
} finally {
  chrome.kill();
  await sleep(500);
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignore */ }
}
const total = results.reduce((a, r) => a + r.violations.reduce((b, v) => b + v.nodes.length, 0), 0);
console.log(`TOTAL violating nodes: ${total}`);
if (typeof args.json === 'string') writeFileSync(args.json, JSON.stringify(results, null, 1));
process.exit(total ? 1 : 0);
