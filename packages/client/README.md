# probate-client

A small typed client for the [Probate](https://github.com/harshbhx/probate) Courthouse public API.
No runtime dependencies. It uses the global `fetch`, so it runs on Node 18+, browsers and Workers.

Not yet published to npm. Until then, build it from the repo (`npm ci && npm run build -w probate-client`).

```sh
npm install probate-client
```

## Use

```ts
import { ProbateClient, ApiError } from "probate-client";

const probate = new ProbateClient({ baseUrl: "https://your-courthouse.example" });

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

## Develop

```sh
npm ci
npm run lint -w probate-client
npm test -w probate-client   # needs services/core/.venv (pip install -e '.[dev]'), or set PROBATE_PYTHON
```

MIT licensed.
