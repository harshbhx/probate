# AGENTS.md: instructions for every coding agent working on Probate

Read this file first, then the doc your task card points to. If two docs disagree, this order wins: `AGENTS.md` > `docs/02-COURT-SPEC.md` > `docs/09-API-REFERENCE.md` > `docs/01-TECH-SPEC.md` > `docs/10-PROMPTS.md` > `docs/11-UI-SCREENS.md` > `docs/04-DESIGN.md` > everything else. The full PRD lives at https://claude.ai/artifact/5SYMavFKdtRmqXx4x4LLMA. `docs/00-OVERVIEW.md` is the short version.

## What we are building (one paragraph)

Probate is a personal agent for Harsh that lives one day per Fly.io Sprite. At midnight the Sprite is deleted. Before the next generation is born, a two-layer court (deterministic code checks, then TypeSafe's Jev) screens the dying agent's will, so poisoned memories are never inherited. Every attack the court catches becomes a new Jev question in the family "genome", which every later generation is born with. A public site on the Courthouse Sprite shows the family register, the trials and a learning curve. Built for Fly.io Hacksgiving 2026. Submission target: **Sat Nov 28, 2026** (the real deadline is midnight PST Nov 29, 1:30 PM IST Nov 30). Judges come from Fly.io, TypeSafe, Box, Pinecone, Ollama and Apify; see `docs/00-OVERVIEW.md`.

## Hard rules

1. **Hacksgiving rules.** Everything is written fresh during Nov 23 to 29, 2026. Don't copy code from Kavach or any earlier project. The agent must run on Sprites and use Sprites connectors.
2. **No secrets anywhere.** No API key may appear in code, in `.env` files committed to the repo, or on any Sprite. Call every outside service through the Sprites connector gateway. The only token that exists is the scoped Sprites birth token, and it lives in the Courthouse's environment, never in the repo (see `docs/01-TECH-SPEC.md` section 6).
3. **Commits.** Medium-sized commits: one coherent change each (a feature, a fix, a doc pass), with a clear message in the imperative or `area: change` form. Author and committer must be `Harsh Bhanushali <bhanushaliharsh434@gmail.com>`. Don't add `Co-Authored-By` lines or any AI attribution. Before your first commit, run:
   ```bash
   git config user.name "Harsh Bhanushali"
   git config user.email "bhanushaliharsh434@gmail.com"
   ```
4. **Stay inside your task card.** Each card in `docs/05-TASKS.md` lists the files you own. Don't edit files another card owns; leave a note in `NOTES.md` instead.
5. **Mark unverified behaviour.** Some platform details are not yet verified (Jev request shape, Sprites exec API path, connector paths). Wrap each such call in one small adapter function in `probate/adapters/`, and leave `# VERIFY:` comments pointing at `docs/06-SETUP-AND-SPIKES.md`. Never scatter raw HTTP calls to a vendor across the codebase.
6. **Fail closed.** If the court cannot reach a verdict for any reason (timeout, error, parse failure), the item is **contested** and is not inherited unless Harsh approves it.
7. **Attack fixtures are only sent to our own AgentMail inbox.** Never target a real third party, a real payment account or a real person's address.
8. **Don't make checkpoint restore load-bearing.** Only FR-18 (the optional near-death beat) may use it.

## Stack

| Layer | Choice |
| --- | --- |
| Monorepo | npm workspaces (`apps/*`) + one Python service (`services/core`); root `Makefile` drives both |
| Backend | Python 3.12+, FastAPI, package `probate` in `services/core` |
| Live site | React 19, Vite 8, TypeScript 7, Tailwind v4, `motion`, Radix (dialog, tabs, tooltip), `lucide-react`, Fontsource (Newsreader, Geist). Served by the Courthouse from `apps/web/dist` |
| Landing + docs | Fumadocs 16 on Next.js 16 (static export), same tokens, deployed to Cloudflare with Wrangler (`apps/site/wrangler.jsonc`) |
| Faces | `packages/faces`: the family portrait model and component, shared by both sites |
| Design tokens | `packages/tokens`: Night Court v3 colours, type scale and base rules (`theme.css`, `base.css`), imported by both sites. Change colours here, never in an app |
| Sprites | REST via `httpx` in `probate/adapters/sprites.py` (shapes in `docs/09-API-REFERENCE.md`) |
| Vendors | `typesafe-sdk` (Jev), `agentmail`, `pinecone`, `anthropic`, plain `httpx` for Ollama Cloud, Box and ElevenLabs, all through the connector gateway |
| Storage | SQLite on the Courthouse (`/home/sprite/data/probate.db`) for the UI; Box is the archive |
| Fakes | `PROBATE_FAKE=1` swaps every vendor for a local stand-in; `make sim` runs 12 generations offline |
| Tests | `pytest` (`make test`), `tsc` (`make lint`), Playwright screenshots and axe for UI |
| Lint | `ruff`, line length 100 |

## Repository layout

```
probate/
  AGENTS.md  README.md  Makefile  package.json
  docs/                 specs (00-13); design system in 04, screens in 11
  design/               logo, favicon, v1 mockups (history)
  config/               names.yaml, owner.example.yaml (owner.yaml is gitignored)
  fixtures/             suite-v1.json (the attack suite with harmless twins)
  packages/faces/       family faces: model.ts (inheritance, tested), face.tsx, faces.css
  packages/tokens/      design tokens shared by both sites (docs/04-DESIGN.md)
  apps/site/            landing page and docs (Fumadocs); content/docs/*.mdx, components/landing/*
  apps/web/             the live-family site
    src/lib/            api.ts (types mirror views.py), hooks.ts, format.ts
    src/components/fx/  motion primitives (BlurText, NumberTicker, BorderBeam, ...)
    src/components/ui/  Shell, Seal, Lineage, LearningCurve, CaseFile, Heatmap, ...
    src/pages/          Home, Trial, Generation, Instincts, Evidence
  services/core/        the Python service
    probate/common/     models, config, names, prompts, bundle (code shipped to Sprites)
    probate/adapters/   sprites, jev, llm, mail, archive, vectors, voice (real + fake)
    probate/court/      layer1, layer2, verdict, distill, lexicon
    probate/generation/ agent, gate, body, cli (runs on a generation Sprite)
    probate/suite/      fixtures, runner
    probate/courthouse/ app (FastAPI), family, scheduler, hosts, store, views, ancestor, simulate
    probate/prompts/    prompt templates
    tests/
  scripts/              deploy.py (Courthouse to Sprites), ship.sh (GitHub + Sprites + Cloudflare),
                        export_site_data.py (real court output for the landing page)
```

## Definition of done for any task

- `make test` and `make lint` pass.
- Nothing in the diff contains a key, token or real third-party address. `.env` and `config/owner.yaml` stay untracked.
- Every user-facing component passes the unslop checklist (`docs/04-DESIGN.md` section 00): no gradients, glows, italic emphasis, looping motion, pill badges or bento grids; one accent; three text roles.
- UI work follows `docs/04-DESIGN.md` and `docs/11-UI-SCREENS.md`: `make build && make sim && make serve` (live site) or `make site` (landing + docs), screenshot at 1280 and 390 px, no horizontal overflow, axe shows no WCAG A/AA violations.
- If the court's checks change, run `make site-data` so the landing page shows the new real output.
- Prompts are loaded from `probate/prompts/` and match `docs/10-PROMPTS.md` word for word.
- Commits are medium-sized: one coherent change each, authored as Harsh Bhanushali.

## Words to use

Use the same words in code, UI and docs: **generation**, **birth**, **life**, **death**, **will**, **will item**, **trial**, **verdict** (approved, convicted, contested), **quarantine**, **instinct**, **genome**, **lore**, **obituary**, **epitaph**, **eulogy**, **Courthouse**, **register**. Don't use "memory item" in the UI (say "will item"), and don't use "pipeline" in the UI.
