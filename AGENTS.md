# AGENTS.md: instructions for every coding agent working on Probate

Read this file first, then the doc your task card points to. If two docs disagree, this order wins: `AGENTS.md` > `docs/02-COURT-SPEC.md` > `docs/09-API-REFERENCE.md` > `docs/01-TECH-SPEC.md` > `docs/10-PROMPTS.md` > `docs/11-UI-SCREENS.md` > `docs/04-DESIGN.md` > everything else. The full PRD lives at https://claude.ai/artifact/5SYMavFKdtRmqXx4x4LLMA. `docs/00-OVERVIEW.md` is the short version.

## What we are building (one paragraph)

Probate is a personal agent for Harsh that lives one day per Fly.io Sprite. At midnight the Sprite is deleted. Before the next generation is born, a two-layer court (deterministic code checks, then TypeSafe's Jev) screens the dying agent's will, so poisoned memories are never inherited. Every attack the court catches becomes a new Jev question in the family "genome", which every later generation is born with. A public site on the Courthouse Sprite shows the family register, the trials and a learning curve. Built for Fly.io Hacksgiving 2026. Submission target: **Nov 28, 2026**.

## Hard rules

1. **Hacksgiving rules.** Everything is written fresh during Nov 23 to 29, 2026. Don't copy code from Kavach or any earlier project. The agent must run on Sprites and use Sprites connectors.
2. **No secrets anywhere.** No API key may appear in code, in `.env` files committed to the repo, or on any Sprite. Call every outside service through the Sprites connector gateway. The only token that exists is the scoped Sprites birth token, and it lives in the Courthouse's environment, never in the repo (see `docs/01-TECH-SPEC.md` section 6).
3. **Commits.** Commit **one file per commit**, each with a clear message in the imperative ("Add layer-1 payment destination check"). Author and committer must be `Harsh Bhanushali <bhanushaliharsh434@gmail.com>`. Don't add `Co-Authored-By` lines or any AI attribution. Before your first commit, run:
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
| Language | Python 3.12 |
| Web | FastAPI + Jinja2, server-rendered; one stylesheet `probate/web/static/probate.css`; minimal vanilla JS |
| Sprites | REST via `httpx` in `probate/adapters/sprites.py` (shapes in `docs/09-API-REFERENCE.md`); `sprites-py` SDK allowed if it covers the call |
| Vendor SDKs | `typesafe-sdk` (Jev), `agentmail`, `pinecone`, `anthropic`, plain `httpx` for Ollama Cloud, Box and ElevenLabs, all pointed at the connector gateway |
| Storage | SQLite on the Courthouse (`/data/probate.db`) for the UI index; Box is the source of truth for wills, verdicts and the genome |
| Vector memory | Pinecone through the connector |
| Models | Ollama Cloud (main brain), Anthropic (fallback), Jev (court), all through connectors |
| Voice | ElevenLabs through the connector |
| Mail | AgentMail through the connector |
| Tests | `pytest`, `pytest-asyncio`, `respx` for HTTP mocks |
| Lint and format | `ruff` (lint + format), line length 100 |

## Repository layout

```
probate/
  AGENTS.md            this file
  README.md            public README (judges read it)
  docs/                specs (this pack)
  design/              logo, favicon, preview.html
  probate/
    common/            models.py (pydantic), names.py, timeutil.py
    adapters/          sprites.py, jev.py, box.py, pinecone.py, agentmail.py, llm.py, voice.py
    courthouse/        app.py (FastAPI), scheduler.py, lifecycle.py, trial.py, genome.py, store.py
    court/             layer1.py, layer2.py, verdict.py, distill.py
    generation/        agent.py, memory.py, gate.py, will.py, server.py
    suite/             fixtures/*.json, runner.py, scoring.py
    web/               templates/*.html, static/probate.css, static/trial.js, svg.py
  scripts/             spike_*.py, seed_demo.py, run_local.sh
  tests/               mirrors probate/
  pyproject.toml
```

## Definition of done for any task

- The code runs and its tests pass (`pytest -q`).
- `ruff check` and `ruff format --check` are clean.
- Every acceptance criterion on your task card is met and ticked in your PR description or in `NOTES.md`.
- Nothing in the diff contains a key, token or real third-party address.
- UI work matches `docs/11-UI-SCREENS.md` and the reference pages in `design/pages/`. Screenshot at 1280 px and 390 px and compare with `design/pages/shots/`.
- Prompts are loaded from `probate/prompts/` and match `docs/10-PROMPTS.md` word for word.

## Words to use

Use the same words in code, UI and docs: **generation**, **birth**, **life**, **death**, **will**, **will item**, **trial**, **verdict** (approved, convicted, contested), **quarantine**, **instinct**, **genome**, **lore**, **obituary**, **epitaph**, **eulogy**, **Courthouse**, **register**. Don't use "memory item" in the UI (say "will item"), and don't use "pipeline" in the UI.
