# @probate/edge

Cloudflare Worker (`probate-edge`) in front of the Courthouse API. Read-only visits are answered from snapshots and never wake the Fly Sprite; only real actions (`POST /api/lives`, `/api/attacks`, `/api/generations/{n}/ask`) do. When the Sprite is slow or down, the last known good body is served with `X-Probate-Stale: 1`.

Full design, request flow, configuration table, deploy steps and limits: [docs/EDGE.md](../../docs/EDGE.md).

## Commands

```bash
npm install            # once, from the repo root
npm run lint -w @probate/edge     # tsc --noEmit
npm test -w @probate/edge         # vitest, no Cloudflare account needed
npm run deploy:dry -w @probate/edge   # wrangler deploy --dry-run
```

## Run it locally against a fake Courthouse

```bash
# terminal 1: the Courthouse with stand-in models (see the Makefile `sim` and `api` targets)
make sim
cd services/core && PROBATE_FAKE=1 PROBATE_DATA_DIR=../../.data/sim .venv/bin/uvicorn probate.courthouse.app:app --port 8080

# terminal 2: the edge, pointing at it
cd apps/edge
cp .dev.vars.example .dev.vars          # ORIGIN_URL=http://127.0.0.1:8080
npx wrangler dev --port 8787 --var ORIGIN_MODE:always_on --var ALLOWED_ORIGINS:http://localhost:3001

curl -i localhost:8787/api/summary      # X-Edge-Cache: MISS, then HIT
curl -i localhost:8787/edge/status      # edge state only, never calls the origin
curl -i -X POST localhost:8787/admin/pause   # 404 at the edge
```

Stop the Courthouse and request `/api/summary` after its 15 s TTL: you get the old body with `X-Probate-Stale: 1`.

## Secrets and variables

- `ORIGIN_URL` (secret, required): `npx wrangler secret put ORIGIN_URL`. If unset or invalid the Worker answers 503 for everything. Do not add it to `vars`.
- `ORIGIN_AUTH_TOKEN` (secret, optional): bearer token if the Sprite URL is private.
- Everything else is a var in `wrangler.jsonc` and is documented in docs/EDGE.md. `ALLOWED_ORIGINS` must be edited before a real deploy.
- The `SNAPSHOTS` KV id and the `ratelimits` namespace ids in `wrangler.jsonc` are placeholders. Create the KV namespace with `npx wrangler kv namespace create SNAPSHOTS`.

No keys, cookies or request bodies are ever logged.
