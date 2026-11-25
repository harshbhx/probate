# Contributing to Probate

Thanks for taking a look. Probate is a hackathon project (Fly.io Hacksgiving 2026), so
the process is light, but a few rules keep it safe and easy to review.
Read [`AGENTS.md`](AGENTS.md) first: it holds the hard rules and the vocabulary the project uses.
If docs disagree, the order in `AGENTS.md` wins.

By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
To report a vulnerability, do not open an issue: see [SECURITY.md](SECURITY.md).

## Setup (Linux, macOS, WSL)

You need Python 3.11 or newer (CI uses 3.13), Node 22 with npm, and `make`.
On Windows, use WSL: the Makefile expects a POSIX shell and `services/core/.venv/bin/python`.

```bash
git clone https://github.com/harshbhx/probate.git
cd probate
make setup      # creates services/core/.venv, installs the Python package with dev tools, runs npm install
make help       # lists every target
```

Everything runs offline against local stand-ins for the vendors:

```bash
make sim        # simulate 12 generations into .data/sim (PROBATE_FAKE=1)
make dev        # API on :8080 and the live site on :5173 together
make site       # landing page and docs on :3001
make serve      # the built live site and the API on :8080, as the Courthouse serves it
```

You do not need any account or API key to work on the code, the court, or either site.
Deploy targets (`make deploy`, `make site-deploy`, `make ship`) need Sprites and Cloudflare
credentials and are for the maintainer.

## Tests and lint

```bash
make test       # pytest for services/core, and the faces model tests
make lint       # ruff, plus TypeScript checks for apps/web and apps/site
make build      # production build of the live site and the landing + docs
```

CI (`.github/workflows/ci.yml`) runs ruff, pytest, a 6-generation simulation, the faces tests,
the type checks and the build. A change is done when `make test` and `make lint` pass.

Extra rules from `AGENTS.md`:

- If you change the court's checks, run `make site-data` so the landing page shows the new real output.
- UI changes follow `docs/04-DESIGN.md` and `docs/11-UI-SCREENS.md`. Check 1280 px and 390 px
  widths for horizontal overflow. Colours live in `packages/tokens`, never in an app.
- Prompts live in `services/core/probate/prompts/` and match `docs/10-PROMPTS.md`.
- Vendor calls go through one adapter function in `services/core/probate/adapters/`,
  not scattered across the code. If the court cannot reach a verdict, it fails closed (contested).

## Branch and pull request flow

1. Fork the repo or create a branch from `main`: `feat/short-name`, `fix/short-name`, `docs/short-name`.
2. Keep each commit one coherent change.
3. Run `make test` and `make lint` locally.
4. Open a pull request against `main` and fill in the template. Link the issue it closes.
5. Keep the PR focused. Many PRs touch `README.md`, CI and the Makefile, so small, additive diffs merge fastest.
6. Wait for CI to pass and for a review. The maintainer merges.

## Commit style

Imperative or `area: change` form, for example `court: hold items that quote the owner's address`
or `docs: explain the birth token`. Common areas are `court`, `courthouse`, `adapters`, `web`,
`site`, `faces`, `tokens`, `docs`, `ci`, `deploy`.

## No secrets, ever

- Never commit keys, tokens, `.env` files or `config/owner.yaml` (both are gitignored).
  Use `services/core/.env.example` and `config/owner.example.yaml` as templates, with fake values.
- Vendors are reached through the Sprites connector gateway, so code must not hold vendor keys.
- Attack fixtures go only to our own inboxes. Never aim them at a real third party or a real person's address.
- If you committed a secret by accident, tell the maintainer privately (see [SECURITY.md](SECURITY.md)); rotating the key matters more than rewriting history.

## Licence

Probate is released under the [MIT License](LICENSE). By contributing you agree that your
contribution is licensed under the same terms.
