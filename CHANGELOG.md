# Changelog

All notable changes to this project are documented here, in the style of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). There are no tagged releases yet;
everything below is unreleased and was built during Fly.io Hacksgiving 2026 (from 25 Nov 2026).

## [Unreleased]

### Added

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
- **Decisions by email.** Harsh decides held items by replying to the court's email.
- **Mail routing.** Harsh's own test emails are sent from his domain through Cloudflare Email
  Service; everyone else goes through AgentMail.
- **Docs.** Product docs and specs (`docs/00` to `docs/13`), threat model, runbook, README with
  recordings, research links, proof table and run guide, and a hackathon section naming the judges.

### Changed

- Life and trial events stay on the generation's own clock.
- Pausing stops new births; the living generation still finishes and stands trial.
- The family keeps Harsh's first address first and always trusts his sender.
- Deploy requires the Cloudflare account ID, and starts the service when there is nothing to restart.

### Fixed

- A Box outage no longer stalls the family.
- The web app no longer crashes when opening `/trial`.
- Mobile layout: bottom tabs, overflow and accessibility fixes.

[Unreleased]: https://github.com/harshbhx/probate/commits/main
