# Runbook: deploy, run, recover, demo day

For Harsh and any agent operating the live family. Commands use `make`, the `sprite` CLI and the Courthouse admin routes. Never paste tokens into the repo or into chat logs.

## 1. First deploy of the Courthouse

One-time, on Harsh's laptop:

1. `gh auth login` (GitHub), `npx wrangler login` (Cloudflare, for the landing page and docs), and get a Sprites API token from the Sprites dashboard.
2. In the Sprites dashboard, connect each provider under Connectors (Jev/TypeSafe, Box, Pinecone, AgentMail, ElevenLabs, Ollama, Anthropic) and note each connection ID. Add a Custom API connector named `cloudflare` for `https://api.cloudflare.com` with a Cloudflare API token that can send email.
3. Create three AgentMail inboxes: the family's, plus friend and stranger test senders. In Cloudflare, turn on Email Service for `dualmindlab.tech` and verify the family inbox as a destination address, so Harsh's test emails can reach it.
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
