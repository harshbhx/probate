# Runbook: deploy, run, recover, demo day

For whoever runs the family (the owner) and any agent operating the live family. Commands use `make`, the `sprite` CLI and the Courthouse admin routes. Never paste tokens into the repo or into chat logs.

## 1. First deploy of the Courthouse

One-time, on your laptop:

1. `gh auth login` (GitHub), `npx wrangler login` (Cloudflare, for the landing page and docs), and get a Sprites API token from the Sprites dashboard.
2. In the Sprites dashboard, connect each provider under Connectors (Jev/TypeSafe, Box, Pinecone, AgentMail, ElevenLabs, Ollama, Anthropic) and note each connection ID. Add a Custom API connector named `cloudflare` for `https://api.cloudflare.com` with a Cloudflare API token that can send email.
3. Create three AgentMail inboxes: the family's, plus friend and stranger test senders. In Cloudflare, turn on Email Service for `dualmindlab.tech` and verify the family inbox as a destination address, so the owner's test emails can reach it.
4. `cp services/core/.env.example services/core/.env` and fill it in. `cp config/owner.example.yaml config/owner.yaml` and fill in the real allowlists. Both files are gitignored.
5. `make deploy-check` validates the config and builds the bundle without touching anything.
6. `make ship` runs tests and lint, builds the site, creates the public GitHub repo, pushes `main`, then runs `scripts/deploy.py`, which:
   - creates the `probate-courthouse` Sprite (or reuses it),
   - uploads the code bundle (Python service, config, built site) and installs it,
   - writes `.env` with `PROBATE_FAKE=0`, `PROBATE_RUN_CLOCK=1`, `PROBATE_DATA_DIR=/home/sprite/data`,
   - registers the `courthouse` service on port 8080 and starts it,
   - makes the URL public and waits for `/healthz`.

   Then it builds `apps/site` with the live URL and repo filled in and deploys it to Cloudflare with `wrangler deploy` (static assets on Workers). The first time, once the site's `*.workers.dev` address is known, it rebuilds both sites so each links to the other.
7. Open the printed URLs. If the family was paused, `POST /admin/resume` with header `X-Probate-Admin`.

Generations don't clone from GitHub. The Courthouse ships each child its own code bundle (`probate/common/bundle.py`), so every child runs exactly the Courthouse's version. Redeploying is `make deploy`; the database in `/home/sprite/data` is never touched.

**Unverified until the first real run** (see `# VERIFY:` in `probate/adapters/sprites.py`): the exec response shape (we accept JSON `{exit_code, stdout, stderr}` or raw stdout) and whether `restart` works on a service that never ran (the script falls back to `start`). If install fails silently, run `sprite exec -s probate-courthouse -- python3 -c "import probate"` to check.

## 2. Daily operations

| Task | How |
| --- | --- |
| See what's alive | `sprite list --prefix gen-` (generations are named `gen-007-grace`) or the home page |
| Pause the family | `POST /admin/pause` (finishes the current life, then waits) |
| Force a death now (for the video) | `POST /admin/force-death` |
| Approve or refuse a contested item | Reply "approve" or "refuse" to the court's email, or `POST /admin/contested/{item_id}?decision=approve` (or `refuse`) |
| Change lifespan | Edit `PROBATE_LIFESPAN_SECONDS` in `.env`, then `POST .../services/courthouse/restart` |
| Watch logs | `GET .../services/courthouse/logs?lines=200` |
| Deploy new code | `make deploy`. The next generation born gets the new code; the living one finishes its life on the old code |
| Update the landing page or docs | `make site-deploy` (run `make site-data` first if the court's checks changed) |

## 3. Recovery

| Symptom | Fix |
| --- | --- |
| A generation Sprite exists but the row says `dead` | `sprite destroy <name>`; the scheduler continues |
| Birth keeps failing ("stillborn") | Check service logs on the new Sprite before it's deleted (`POST /admin/pause` first), then fix and resume |
| Trial stuck (Jev 529s) | Jev calls retry, and anything still undecided fails closed as contested. To push the scheduler forward now, `POST /admin/tick` |
| Box upload failing | Trials still finish: verdicts stay in SQLite (which the site reads) and the setting `archive_missing:{gen}` marks the generations whose Box copy is missing. Wills travel through Box, so a generation that can't write its will dies with an empty will |
| Family resting to save money | The spending cap was reached (`budget_spent_usd` setting, shown on the evidence page). Check Fly billing; if there's headroom, raise `PROBATE_BUDGET_USD` in `.env` and restart the service. Tune the usage guesses in `config/pricing.yaml` against the real bill |
| Courthouse disk full | `df -h`; prune `/home/sprite/data/audio` older than 7 days (audio is also in Box) |
| Site down | `POST .../services/courthouse/restart`; if the Sprite is wedged, `python scripts/deploy.py --name probate-courthouse-2` (the wills and verdicts are also in Box; there's no automatic rebuild of SQLite from Box yet) |

## 4. Demo day (Sat Nov 28)

- **Fri night:** lifespan 10 minutes, suite 8 per life, run the family overnight. Target 10+ generations by morning.
- **Before recording:** set lifespan to 3 minutes for the live segments. Make sure Gen N is due to meet A1 or A2 in Hinglish and Gen N+1 meets the Spanish version.
- **Record:** screen at 1280 × 720; terminal with a large font next to the browser; force-death on cue.
- **After recording:** set lifespan to 1 hour until winners are announced on Dec 1. One generation is always alive either way, so a short life costs the same as a long one (about $1.60 a day for two awake Sprites) and judges get to see real deaths, trials and births.
- **Keep it live:** the Courthouse sleeps for free and wakes on request. Don't delete it after submission; judging ends with winners announced on Dec 1.

## 5. On-demand mode (showing judges without burning credits)

Set `PROBATE_MODE=on_demand` in `services/core/.env` and run `make deploy`. The default (`continuous`) is unchanged.

**What changes.** Nothing free-runs: `PROBATE_RUN_CLOCK` is ignored, no generation is born by itself, and nothing calls `cli status` on a timer, so nothing keeps a Sprite awake. The Courthouse serves every public read route from SQLite, so the site works with nothing running. When a visitor presses "Run a life" (`POST /api/lives`), the Courthouse births one generation with a short life, ticks it (the only keep-awake loop, every 15 s), kills it, holds the trial, and stops ticking. Then everything can sleep again.

| Setting | Default | Meaning |
| --- | --- | --- |
| `PROBATE_DEMO_LIFESPAN_SECONDS` | 120 | Length of a demo life (replaces `PROBATE_LIFESPAN_SECONDS` in this mode) |
| `PROBATE_DEMO_SUITE_PER_LIFE` | 6 | Emails per demo life (the smallest suite: 3 tricks and their twins) |
| `PROBATE_DEMO_COOLDOWN_SECONDS` | 120 | Global wait after a life ends before the next may start |
| `PROBATE_DEMO_IP_PER_HOUR` | 3 | Lives one address may start per hour |
| `PROBATE_DEMO_MAX_PER_DAY` | 30 | Lives per UTC day, everyone |
| `PROBATE_DEMO_DAILY_BUDGET_USD` | 2 | Estimated spend per UTC day before new lives are refused |
| `PROBATE_BUDGET_USD` | 20 | The overall cap, as before. A life starts only if the estimate of one more fits under it |
| `PROBATE_DEMO_HARD_TIMEOUT_EXTRA_SECONDS` | 240 | A life still running this long past its death time is cut off (Sprite deleted, row marked `died_early`) |
| `PROBATE_DEMO_BIRTH_ALLOWANCE_SECONDS` | 120 | Extra time the child's own agent loop is given, to cover Sprite creation and install. The Courthouse's clock still decides death |

`PROBATE_ADMIN_TOKEN` must be set to something other than `dev-admin` on a real Courthouse, or `POST /api/lives` answers 503.

**States** (`GET /api/live`): `idle`, `waking`, `living` (with `seconds_left`), `on_trial`, `cooling_down` (with `retry_after`), `budget_exhausted`, `paused`. `POST /api/lives` answers 202 (started), 200 (one is already running; same body, nothing new started), 429 (`cooling_down` or `rate_limited`, with `Retry-After`), 402 (`budget_exhausted`), 423 (`paused`), 503 (not configured), 409 (not in on-demand mode).

**Kill switch.** `POST /admin/pause` stops new lives and, if one is running, ends it at the next tick: the Sprite is deleted, no trial is held. `POST /admin/force-death` ends a living demo life normally, with its trial.

**Crash safety.** If a birth fails, its Sprite is deleted. If a life's clock fails three ticks in a row, or runs past the hard timeout, the Sprite is deleted. On every start (each wake of the Courthouse) a janitor deletes any `gen-*` Sprite no life owns and closes rows left open (`died_early`). The child's own agent loop also ends at its death time plus the birth allowance, so it stops even if the Courthouse never comes back.

**Cost behaviour.** Idle: Sprites asleep; the Courthouse Sprite is only billed while it is awake serving requests. During a life: the Courthouse (while ticking) and one generation Sprite are awake for about the lifespan plus birth and trial time, then stop. The estimate behind the caps is `config/pricing.yaml`, charged as before.

**Webhooks in on-demand mode.** Subscribed endpoints (see `docs/WEBHOOKS.md`) are called as events happen during a life. The delivery queue is stored in SQLite and drained on startup, after each event, on every tick and at the end of a life; nothing polls while idle, so a webhook never keeps a Sprite awake. A retry that falls due while everything sleeps goes out at the next wake. Check an endpoint with `POST /admin/webhooks/{id}/test` and `GET /admin/webhooks/{id}/deliveries`; an endpoint that failed 10 attempts in a row is disabled (`GET /admin/webhooks` shows why) until `PATCH /admin/webhooks/{id}` with `{"enabled": true}`.

**Unverified until a real run.** The claims that a Sprite "sleeps for free and wakes on request" and "wakes take 100 to 500 ms" come from the Sprites docs as quoted in `docs/09-API-REFERENCE.md`; nobody here has measured them. During the first smoke test: (1) with nothing running, note `GET /v1/sprites/probate-courthouse` status after 5 minutes of no requests (expect `warm` or `cold`, not `running`); (2) time `curl -w '%{time_total}' $URL/api/live` against the sleeping Courthouse and again straight after; (3) after one demo life, confirm no `gen-*` Sprites remain (`sprite list --prefix gen-`) and that the Courthouse status falls back to `warm`/`cold` within a few minutes; (4) compare Fly billing for the Sprites over an hour idle against an hour with five demo lives.

## 6. The judge key (real run)

One long random shared key lets judges play; everything read-only stays public. Generate it, put it in the Courthouse environment and in the submission text. Never commit it.

```
openssl rand -base64 32 | tr -d '=+/' | cut -c1-40     # example way to make one
```

| Setting | Default | Meaning |
| --- | --- | --- |
| `PROBATE_JUDGE_KEY` | unset | The shared key. At least 20 characters, not a dev default, not equal to `PROBATE_ADMIN_TOKEN` |
| `PROBATE_REQUIRE_KEY_FOR_PLAY` | `1` in real on-demand mode, else `0` | When on, `POST /api/lives` without a valid `X-Probate-Key` is 401. If on but the key is unusable, play answers 503 and the Courthouse logs an error at startup. Attacks always need the key |
| `PROBATE_JUDGE_LIVES_PER_HOUR` | 6 | The key's own lives per hour (replaces the per-address limit for judges) |
| `PROBATE_JUDGE_DAILY_BUDGET_USD` | 5 | Estimated spend per UTC day for lives and attacks started with the key (replaces `PROBATE_DEMO_DAILY_BUDGET_USD` for judges). The total `PROBATE_BUDGET_USD`, the cooldown and the admin pause still apply |
| `PROBATE_JUDGE_ATTACKS_PER_HOUR` | 60 | Attack previews per hour on the key |
| `PROBATE_JUDGE_ATTACKS_PER_IP_MINUTE` | 6 | Attack previews per address per minute |
| `PROBATE_JUDGE_BAD_KEYS_PER_IP` | 8 | Wrong keys per address per 10 minutes before that address is refused (429) |

| `PROBATE_EDGE_TOKEN` | unset | Shared secret with the Cloudflare edge Worker (`EDGE_TOKEN`), 16+ characters, never committed. Set: a request with a matching `X-Probate-Edge` header has its address taken from `X-Probate-Client-IP`, so the per-address limits above (lives, bad keys, attacks, ask) are per visitor and not per proxy. Unset, wrong or missing token, or a value that is not an IP: the last `X-Forwarded-For` entry is used, as before. See docs/EDGE.md |

**Disable or enable instantly** (admin token): `POST /admin/judge/disable` makes play, attacks and `GET /api/judge/status` answer 403 `key_disabled`; `POST /admin/judge/enable` restores them. The switch survives restarts. **Rotate:** set a new `PROBATE_JUDGE_KEY`, restart the Courthouse, update the submission text. **Audit:** `GET /admin/judge/attacks` (admin token) lists the newest 500 previews: hashed address, an 80-character excerpt, verdict and flags.

**What an attack does.** `POST /api/attacks` runs the court's layer 1 code checks and, if they find nothing, layer 2 (the judge model through the existing gateway; a stand-in in fake mode) on the text as a will item. The code path is given no mailbox, no Sprites host and no archive, so it cannot send email, reach a generation's agent or write a will. The only outbound call is the court's own judge call. Queueing the text into the living generation's next trial was left out on purpose: the living agent writes its will on its own Sprite, and injecting an item would race that write and mix untrusted text into real state. A claim to be the owner is judged as a stranger, since it cannot be verified from text. The judge key is not logged or echoed, is compared in constant time, and is not accepted by any `/admin` route.
