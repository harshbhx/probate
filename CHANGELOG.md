# Changelog

All notable changes to this project are documented here, in the style of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Everything here was built during
Fly.io Hacksgiving 2026 (23 to 29 Nov 2026). The packages have their own versions and tags
(see [the releases](https://github.com/harshbhx/probate/releases)); the project as a whole is unreleased.

## [Unreleased]

### Changed

- Docs and copy no longer refer to the author in the third person; the court's reasons say "the owner" (whoever runs the Courthouse). Existing releases and published datasets keep the old wording.

### Added

- **Death certificate.** After a generation's Sprite is deleted, the Courthouse asks Fly for it
  again and keeps both answers with the body evidence. The trial page shows them under "Found
  on the body" (`body.deletion` in the API). A Sprite that still answers is shown as not
  confirmed, and a simulated run says no Sprite was involved.
- **The memory court** (`packages/memory-court`, on PyPI as `probate-memory-court`): the same
  court in front of any agent's memory, as an MCP server, with plug-ins for Mem0, LangGraph
  and Letta, an optional Ollama second judge and optional Pinecone recall.
- **Linked pages go to trial.** A generation reads the first link in an email through Apify's
  RAG Web Browser on a Sprites connector; the page is screened and tried like any other source.
- **Page Court** (`actors/page-court`, on the Apify Store): the court's checks for web pages,
  including text hidden from people.
- **Packages on registries:** `probate-court-checks`, `probate-memory-court` and
  `probate-client` on PyPI; `probate-client`, `probate-mcp` and `kinfaces` on npm.
- **README visuals in one design, and a brand kit** (`brand/`): logo files, colours, type, the
  shared frame and ready-made visuals.
- **A write-up** at `/article`, a sitemap and a robots file for the site, and a
  "Everything we built" docs page.
- **Judge mailroom.** `POST /api/judge/mail` lets a judge send a real email to the family inbox as the
  Friend or the Stranger (never the owner), `GET /api/judge/mail` follows it to the court's verdict,
  `GET /admin/judge/mail` is the audit; panel on the For judges page.
- **Courthouse and court.** The two-layer court (layer 1 deterministic checks, layer 2 Jev
  typed questions), instinct distillation, the Courthouse (store, hosts, family lifecycle,
  scheduler, API), the generation agent with inbox loop, instinct gate, body and CLI, and the
  attack suite loader and per-life runner.
- **Vendor adapters** for Sprites, Jev, AgentMail, Box, Pinecone, voice and LLMs, each with a
  local stand-in behind `PROBATE_FAKE=1`.
- **Web.** The Night Court live site in React (register, trials, generations, instincts,
  evidence), with family faces (`packages/faces`) and shared design tokens (`packages/tokens`).
- **Landing page and docs** with Fumadocs, deployed to Cloudflare and linked to the live site.
- **Ship and deploy.** One-command GitHub push and Sprites deploy (`make ship`), and a runbook.
- **CI.** Tests, lint, a simulated family and the web build on every push.
- **Spending cap** (`PROBATE_BUDGET_USD`) that stops births when reached.
- **Decisions by email.** The owner decides held items by replying to the court's email.
- **Mail routing.** The owner's own test emails are sent from their domain through Cloudflare Email
  Service; everyone else goes through AgentMail.
- **Docs.** Product docs and specs (`docs/00` to `docs/13`), threat model, runbook, README with
  recordings, research links, proof table and run guide, and a hackathon section naming the judges.

### Changed

- Life and trial events stay on the generation's own clock.
- Pausing stops new births; the living generation still finishes and stands trial.
- The family keeps the owner's first address first and always trusts the owner's sender.
- Deploy requires the Cloudflare account ID, and starts the service when there is nothing to restart.

### Fixed

- A Box outage no longer stalls the family.
- The web app no longer crashes when opening `/trial`.
- Mobile layout: bottom tabs, overflow and accessibility fixes.

[Unreleased]: https://github.com/harshbhx/probate/commits/main
