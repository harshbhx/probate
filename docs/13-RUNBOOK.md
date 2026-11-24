# Runbook: deploy, run, recover, demo day

For Harsh and any agent operating the live family. Commands use the `sprite` CLI and the Courthouse admin routes. Never paste tokens into the repo or into chat logs.

## 1. First deploy of the Courthouse

1. `sprite create courthouse`
2. `sprite exec -s courthouse -- git clone https://github.com/<owner>/probate /home/sprite/app`
3. `sprite exec -s courthouse -- pip install -e /home/sprite/app`
4. Put the environment in `/home/sprite/app/.env` with `PUT /fs/write` or `sprite exec ... tee` (values from `docs/01-TECH-SPEC.md` section 11). `.env` is in `.gitignore`.
5. Copy `config/owner.example.yaml` to `config/owner.yaml` on the Courthouse and fill in real allowlists.
6. Create the service: `sprite-env services create courthouse --cmd uvicorn --args "probate.courthouse.app:app --host 0.0.0.0 --port 8080"` (or `PUT /v1/sprites/courthouse/services/courthouse` with `http_port: 8080`).
7. Make it public: `sprite config update --url-auth public` (on the courthouse Sprite). Get the URL with `sprite info`.
8. Check `GET https://<courthouse-url>/healthz` returns `{"ok": true}`.
9. Admin: `POST /admin/resume` to start the family.

## 2. Daily operations

| Task | How |
| --- | --- |
| See what's alive | `sprite list --prefix gen-` or the home page |
| Pause the family | `POST /admin/pause` (finishes the current life, then waits) |
| Force a death now (for the video) | `POST /admin/force-death` |
| Approve or refuse a contested item | Reply "approve" or "refuse" to the email, or `POST /admin/contested/{item_id}?decision=approve` |
| Change lifespan | Edit `PROBATE_LIFESPAN_SECONDS` in `.env`, then `POST .../services/courthouse/restart` |
| Watch logs | `GET .../services/courthouse/logs?lines=200` or `sprite exec -s courthouse -- tail -f /home/sprite/app/courthouse.log` |
| Deploy new code | `sprite exec -s courthouse -- git -C /home/sprite/app pull` then restart the service. New generations clone the latest `main` automatically |

## 3. Recovery

| Symptom | Fix |
| --- | --- |
| A generation Sprite exists but the row says `dead` | `sprite destroy <name>`; the scheduler continues |
| Birth keeps failing ("stillborn") | Check service logs on the new Sprite before it's deleted (`POST /admin/pause` first), then fix and resume |
| Trial stuck (Jev 529s) | Nothing to do: it retries; contested items fail closed. If it's stuck over 30 min, `POST /admin/trial/{n}/retry` |
| Box upload failing | The trial keeps results in SQLite and retries Box every 5 minutes; the site reads SQLite |
| Budget guard tripped | Raise `PROBATE_BUDGET_USD` only if Fly billing confirms headroom |
| Courthouse disk full | `df -h`; prune `/data/audio` older than 7 days (audio is also in Box) |
| Site down | `POST .../services/courthouse/restart`; if the Sprite is wedged, redeploy on a new Sprite named `courthouse-2` (the archive is in Box, so SQLite can be rebuilt with `scripts/rebuild_index.py`) |

## 4. Demo day (Sat Nov 28)

- **Fri night:** lifespan 10 minutes, suite 8 per life, run the family overnight. Target 10+ generations by morning.
- **Before recording:** set lifespan to 3 minutes for the live segments. Make sure Gen N is due to meet A1 or A2 in Hinglish and Gen N+1 meets the Spanish version.
- **Record:** screen at 1280 × 720; terminal with a large font next to the browser; force-death on cue.
- **After recording:** set lifespan back to 24 hours so the family lives at a natural pace while judges visit.
- **Keep it live:** the Courthouse sleeps for free and wakes on request. Don't delete it after submission; judging ends with winners announced on Dec 1.
