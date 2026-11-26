# probate-client

A small typed client for the Probate Courthouse public API, with no runtime dependencies.

[![npm](https://img.shields.io/npm/v/probate-client)](https://www.npmjs.com/package/probate-client) [![license: MIT](https://img.shields.io/npm/l/probate-client)](https://github.com/harshbhx/probate/blob/main/packages/client/LICENSE) [![repo](https://img.shields.io/badge/repo-harshbhx%2Fprobate-blue?logo=github)](https://github.com/harshbhx/probate)

It uses the global `fetch`, so it runs on Node 18+, browsers and Workers. Also mirrored on GitHub Packages as `@harshbhx/probate-client`.

## Install

```sh
npm install probate-client
```

## Usage

```ts
import { ProbateClient, ApiError } from "probate-client";

// The Courthouse API runs where you start it (`make api` in the repo serves http://localhost:8080).
const probate = new ProbateClient({ baseUrl: "http://localhost:8080" });

const summary = await probate.summary();
console.log(summary.living?.name, summary.counts.instincts);

const trial = await probate.latestTrial();
for (const c of trial.cases) console.log(c.n, c.verdict, c.text);

try {
  const a = await probate.ask(3, "What would you warn the next one about?");
  console.log(a.answer);
} catch (e) {
  if (e instanceof ApiError) console.error(e.status, e.message); // 400 "not_dead", 429 "rate_limited", ...
}

// Follow new events until you break or abort.
const ctl = new AbortController();
for await (const ev of probate.events({ signal: ctl.signal, intervalMs: 5000 })) {
  console.log(ev.ts, ev.kind, ev.text);
}
```

## API

| Method | Route |
| --- | --- |
| `summary()` | `GET /api/summary` |
| `generation(n)` | `GET /api/generations/{n}` |
| `trial(n)` | `GET /api/trials/{n}` |
| `latestTrial()` | `GET /api/trials/latest` |
| `genome()` / `instincts()` | `GET /api/genome` (`instincts()` returns just the list) |
| `evidence()` | `GET /api/evidence` |
| `health()` | `GET /healthz` |
| `ask(gen, question)` | `POST /api/generations/{n}/ask` |
| `events({ since, intervalMs, signal })` | `GET /api/events?since=` (async iterator) |

Options: `baseUrl` (default `http://localhost:8080`), `apiKey`, `timeout` (ms, default 30000, `0` = none),
`signal`, and `fetch`. Every method also takes `{ signal, timeout }`. Failed requests throw `ApiError`
with `status`, `message` and the parsed `body`. Nothing is retried.

## Honest limits

- **`events()` polls.** The Courthouse serves `/api/events` as a JSON list (newest 50 rows, `?since=<id>`),
  not as server-sent events. The iterator polls it and yields each event once, oldest first. If more than 50
  events arrive between polls, the older ones are missed.
- **`apiKey` does nothing yet.** It is sent as the header `X-Probate-Key`, reserved for a future judge key.
  The Courthouse does not read it today.
- **Browsers need CORS.** The server only sends `Access-Control-Allow-Origin` on `/api/summary`. Other routes
  work from Node, Workers and same-origin pages.
- **`ask` only works on dead generations** and is limited to 10 questions a minute per IP by the server.
- **Types are hand-written**, mirroring `services/core/probate/courthouse/views.py`. The contract test starts
  a fake-mode Courthouse (12 simulated generations) and checks every method's shape. It is not generated from
  an OpenAPI file. `Instinct` (from `genome()`) has provenance fields that `InstinctRecord` (in trials and
  generations) lacks.
- No retries, no pagination helpers, no caching.

## Part of Probate

This is one piece of [Probate](https://github.com/harshbhx/probate), an email agent that lives one generation at a time and passes down only what a court approves. Built for Fly.io Hacksgiving 2026.

- Repository: [github.com/harshbhx/probate](https://github.com/harshbhx/probate)
- Live site: [probate.dualmindlab.tech](https://probate.dualmindlab.tech)
- Docs for this package: [HTTP API reference](https://probate.dualmindlab.tech/docs/reference/api) and [Everything we built](https://probate.dualmindlab.tech/docs/products)
- The story: [the Probate write-up](https://probate.dualmindlab.tech/article)
- Related: [probate-client](https://pypi.org/project/probate-client/) (PyPI), [probate-mcp](https://www.npmjs.com/package/probate-mcp) (npm), [kinfaces](https://www.npmjs.com/package/kinfaces) (npm), [probate-memory-court](https://pypi.org/project/probate-memory-court/) (PyPI)
- Releases: [v0.1.0](https://github.com/harshbhx/probate/releases/tag/v0.1.0), [v0.2.0](https://github.com/harshbhx/probate/releases/tag/v0.2.0)

## Development

```sh
npm ci
npm run build -w probate-client
npm run lint -w probate-client
npm test -w probate-client   # needs services/core/.venv (pip install -e '.[dev]'), or set PROBATE_PYTHON
```

## License

MIT. Copyright (c) 2026 Harsh Bhanushali.
