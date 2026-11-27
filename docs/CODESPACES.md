# Run it in a Codespace

Nothing to install: [open the repo in a Codespace](https://codespaces.new/harshbhx/probate?quickstart=1).
Every vendor is a stand-in (`PROBATE_FAKE=1`), so no keys are needed and nothing leaves the Codespace.

## What happens

1. The container is built from Python 3.13 plus Node 22, the same versions CI uses.
2. `.devcontainer/post-create.sh` runs once and logs each step: toolchain check, Python venv at
   `services/core/.venv`, `npm ci`, `make sim` (12 generations with stand-in models) and a build of the live site.
3. On attach, `make serve` starts the live family on port 8080 and the browser tab opens.

First creation takes about 5 to 8 minutes, mostly `npm ci`.

## Ports

| Port | What | Started by |
| --- | --- | --- |
| 8080 | Live family (simulated) | automatic (`make serve`) |
| 5173 | Website with hot reload | `make dev` or `make web` |
| 3001 | Landing page and docs | `make site` |

## Machine size

The default 2-core, 8 GB machine is enough. The Next.js build of the landing page and docs
(`make build`, `make site`) is the heaviest step; a 4 GB machine can run out of memory.

## If it stops

- Read the last `==>` line in the creation log (Command Palette, "Codespaces: View Creation Log").
- "Wrong Node version": this repo needs Node 22.22 or newer (some dependencies require it).
  Run "Codespaces: Rebuild Container" so the Node 22 feature resolves to the latest 22.x.
- Re-run the setup any time: `bash .devcontainer/post-create.sh`, then `make serve`.
- Locally, `.nvmrc` selects Node 22 (`nvm use`).
