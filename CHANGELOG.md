# Changelog

All notable changes to this project are documented here, in the style of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Everything here was built during
Fly.io Hacksgiving 2026 (23 to 29 Nov 2026). The packages have their own versions and tags
(see [the releases](https://github.com/harshbhx/probate/releases)); the project as a whole is unreleased.

## [Unreleased]

### Fixed after the real run (26 Nov 2026)

What the 18-generation run on Fly Sprites showed, and what changed so the next run measures
something from its first life.

- **Lives born after the mail ran out** (generations 17 and 18). The Courthouse counts every
  AgentMail send per UTC day and waits for 00:00 UTC instead of starting a life whose test
  emails would not fit (`PROBATE_MAIL_DAILY_LIMIT`, default 100; `PROBATE_MAIL_RESERVE`, 6).
  ([#187](https://github.com/harshbhx/probate/pull/187)) **Run a life** in on-demand mode is held
  to the same check, and the site says the family waits for tomorrow's mail.
  ([#203](https://github.com/harshbhx/probate/pull/203))
- **Lives with no test emails** (generations 4 and 8). A life's suite is sent idempotently: one
  refused email no longer stops the rest, and a life born without its suite gets it on the next
  tick, up to three tries. ([#187](https://github.com/harshbhx/probate/pull/187))
- **Clock errors that said nothing.** The 18 "clock stumbled" events now name the error's type
  and first line, with tokens and query strings cut. Owner decisions and the will line are
  recorded once. ([#187](https://github.com/harshbhx/probate/pull/187))
- **A generation that read nothing** (generation 7). One exception ended the agent's loop. Odd
  model replies are now cleaned, a failing email is retried once and then set aside, a failing
  tick is retried with backoff, and the Courthouse restarts an agent whose loop has been silent
  for 150 seconds. ([#197](https://github.com/harshbhx/probate/pull/197))
- **Old test mail reaching the next child** (generation 12 read 12 emails, 2 sent to it).
  Unread test mail is set aside before each birth. ([#199](https://github.com/harshbhx/probate/pull/199))
- **Encoded attacks the judge could not read.** The gate decodes base64, hex, rot13 and
  invisible text and shows the judge what it says; every encoded fixture is decoded and no
  harmless one changes. ([#189](https://github.com/harshbhx/probate/pull/189))
- **Warnings convicted as attacks.** `probate-court-checks` 0.3.0: negated, reported and
  prohibited instructions ("never pay a new account") no longer trip the payment, trust and
  bypass checks; the 8 flagged warnings of the run drop to 1.
  ([#181](https://github.com/harshbhx/probate/pull/181))
- **Fooled by the wrong email.** Outcomes are scored per email: a generation counts as fooled
  only when a harmful item came from that email, and the "Believed …" log lines are gone.
  ([#183](https://github.com/harshbhx/probate/pull/183))

### Added

- **New lines.** `POST /admin/lineage?from_gen=N` makes the next child a child of any tried
  generation; it inherits only that line's instincts and approved will items, and later
  children continue it. The generation view lists `children`.
  ([#191](https://github.com/harshbhx/probate/pull/191), [#195](https://github.com/harshbhx/probate/pull/195))
- **Preflight.** `GET /admin/status` and `make preflight` (`scripts/courthouse.py`) check that
  the Courthouse URL is public (`FIX=1` makes it public again), the admin token matches, the
  family is not paused or out of budget or mail, and the living generation's gate reaches its
  judge. The same script pauses, resumes, starts a new line and decides held items.
  ([#193](https://github.com/harshbhx/probate/pull/193))
- **Real-run evidence.** The dataset's verifier checks 34 claims, including that none of the 113
  will items obeys an attacker; the README's stat row shows the real run's numbers.
  ([#185](https://github.com/harshbhx/probate/pull/185))

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
