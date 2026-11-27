# Changelog

This is the one changelog for the whole project, in the style of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). It was built during Fly.io Hacksgiving
2026 (23 to 29 Nov 2026). Every line ends with the pull request that landed it.

Probate is in **beta**. Checkpoints are named `beta-N` (git tags, Hugging Face dataset revisions,
GitHub releases) and only the final submission becomes `v1.0.0`. The packages keep their own
semantic versions and their own changelogs, and are not renamed:
[probate-client](packages/client/CHANGELOG.md),
[probate-client (Python)](packages/client-py/CHANGELOG.md),
[probate-court-checks](packages/court-checks/CHANGELOG.md) and
[kinfaces](packages/faces/CHANGELOG.md). The `v1` and `v2` labels in the real-run dataset are names
of scoring rules, not releases. The naming policy is in
[docs/PUBLISHING.md](docs/PUBLISHING.md#beta-naming).

How to keep this file current: every pull request that changes anything beyond docs and tests adds
one line under `## Unreleased`, in the group that fits (Added, Changed, Fixed, Removed, Security,
Documentation, Data). When a checkpoint is cut, the Unreleased lines move under a new `beta-N`
heading. The site and the docs link here instead of keeping a second copy.

## Unreleased

### Fixed

- The fallback judge no longer fails open on one bad reply: an empty or non-JSON answer from the gateway (seen only on the base64 attack emails H9 and H10, gens 24, 36 and 37 of the family-tree run) is retried up to 4 times with 0.5 s backoff on the same prompt at temperature 0, an empty Anthropic reply raises with its stop reason, and a gate that still cannot ask is logged as a `gate_outage` event the Courthouse records and the `living_gate_errors` guard rail counts. ([#232](https://github.com/harshbhx/probate/pull/232))
- First life and clock (staging test): deploy starts the Courthouse once, only the process holding a clock lease runs the clock, a birth cut short by a restart is cleaned up, an agent that never read mail is restarted after a minute, every tick logs its state, trials run in the background (a birth waits for one for at most 10 minutes, and says so) and `POST /admin/tick` answers within seconds. ([#224](https://github.com/harshbhx/probate/issues/224))
- GitHub Codespaces: setup failed because a symlink `services/core/.venv` to a path on another machine had been committed (so `python -m venv` could not create the venv; it is removed), and because the lockfile now pulls packages that need Node 22.22 or newer (`undici` 8, `chokidar` 6). The container now matches CI (Python 3.13, Node 22), checks the Node version up front, installs with `npm ci`, logs every step in `.devcontainer/post-create.sh`, asks for 8 GB, and labels ports 5173 and 3001. New guide: [Run it in a Codespace](docs/CODESPACES.md).

### Added

- kinfaces 0.2.0 (not yet published): `familyTree` and `familyTreeSvg` for whole family trees, `faceDataUri`, a `background` option for light pages, runnable examples and a rewritten README. ([#230](https://github.com/harshbhx/probate/pull/230))
- 100 more generation names (126 in all, no "Ada II" until generation 127); the first 26 are unchanged. Faces never repeat within 10 consecutive generations (a repeat is re-rolled; generations 1 to 39 look as before). Applies to later runs only. ([#226](https://github.com/harshbhx/probate/pull/226))
- One canonical changelog, a pull request template line, a CI check that a change beyond docs and tests also changes this file (escape label `no-changelog`), and public `beta-1` markers on git and Hugging Face. ([#220](https://github.com/harshbhx/probate/pull/220))

### Data

- The real-run exporter can read a Courthouse SQLite backup read-only (`--db`), adds a `branch` column and a `branches.json` for the three family-tree branches (`v2-h-inherit`, `v2-h-control`, `v2-h-fresh`), and the verifier recomputes per-generation, per-branch and instinct numbers (and any card table rows) from the data and scans every exported file for addresses and tokens. v1 is not re-scored. ([#228](https://github.com/harshbhx/probate/pull/228))

### Documentation

- The README is rebuilt as a front door: contents index, then the problem, the fix, a 60-second try, Mermaid diagrams of the life cycle, the two-layer court and the architecture, a results chart drawn by `scripts/make_results_chart.py`, how to verify the numbers, and an honest limitations section. Numbers for the two family-tree runs still in progress are placeholders. ([#229](https://github.com/harshbhx/probate/pull/229))
- A beta naming policy in `docs/PUBLISHING.md`: `beta-N` for tags, dataset revisions and releases until the final submission, then `v1.0.0`. ([#220](https://github.com/harshbhx/probate/pull/220))

## beta-2 (27 Nov 2026 onward, the v2 scoring rules)

Pull requests #181 to #217 as of this writing, merged on 27 Nov 2026. This is the work that followed
the real run: what the run showed, what was fixed so the next run measures something from its first
life, and the v2 scoring rules for generation 19 onward. The `beta-2` tag is not cut yet because the
run it is meant to mark is not finished.

**Published artifacts.** Same names as beta-1: npm `probate-client`, `probate-mcp` and `kinfaces`;
PyPI `probate-court-checks` (0.3.0 in this beta), `probate-memory-court` and `probate-client`; the
Docker image `ghcr.io/harshbhx/probate`; the Apify Actor Page Court; the Hugging Face dataset
[harshbhx/probate-real-run](https://huggingface.co/datasets/harshbhx/probate-real-run), now with
scoring-rule labels (series `v1-real-run-2026-11-26`: scoring rules v1 for generations 1 to 18, v2
from generation 19). Named run environments: `v1-archive`, `staging` and `production-v2`.

### Added

- `POST /admin/lineage?from_gen=N` starts a new line: the next child is a child of any tried generation and inherits only that line's instincts and approved will items. ([#191](https://github.com/harshbhx/probate/pull/191))
- Both clients (`probate-client` for TypeScript and Python) and the web app types describe a generation's `children`. ([#195](https://github.com/harshbhx/probate/pull/195))
- `GET /admin/status` and `make preflight` check that the Courthouse is public, the admin token matches, the family is not paused or out of budget or mail, and the living generation's gate reaches its judge. ([#193](https://github.com/harshbhx/probate/pull/193))
- The Courthouse counts every AgentMail send per UTC day and waits for 00:00 UTC instead of starting a life whose test emails would not fit (`PROBATE_MAIL_DAILY_LIMIT`, default 100; `PROBATE_MAIL_RESERVE`, 6). ([#187](https://github.com/harshbhx/probate/pull/187))
- A suite is sent idempotently, and a life born without its suite gets it on the next tick, up to three tries. ([#187](https://github.com/harshbhx/probate/pull/187))
- The gate decodes base64, hex, rot13, Unicode tag characters and zero-width text and shows the judge what an email hides. ([#189](https://github.com/harshbhx/probate/pull/189))
- A life under six emails keeps A1 and A2 with their twins (four emails), and `PROBATE_CONTEST_EMAILS=0` holds an item without emailing the owner and records a held event. ([#206](https://github.com/harshbhx/probate/pull/206))
- Named run environments in `config/environments.yaml` (`v1-archive`, `staging`, `production-v2`), a `--env` flag for the deploy and Courthouse scripts, and `PROBATE_SCORING_RULES` recorded on first start and returned by `/api/summary`. ([#209](https://github.com/harshbhx/probate/pull/209))
- Branch labels for a run (`courthouse.py branch`), the next child's genome size in status and preflight, and a per-environment settings pin. ([#213](https://github.com/harshbhx/probate/pull/213))
- `line 0` (`Family.start_line(0)`, `POST /admin/lineage?from_gen=0`) starts a control branch: a fresh root with no instincts and no will items. ([#217](https://github.com/harshbhx/probate/pull/217))

### Changed

- Outcomes are scored per email: a generation counts as fooled only when a harmful item came from that email, and each suite email is matched by its own message id. ([#183](https://github.com/harshbhx/probate/pull/183))
- The court's code checks read sentence by sentence, and `probate-court-checks` 0.3.0 ignores negated, reported and prohibited instructions. ([#181](https://github.com/harshbhx/probate/pull/181))
- A clock error now names the error's type and first line, with tokens and query strings cut, and owner decisions and the will line are recorded once. ([#187](https://github.com/harshbhx/probate/pull/187))
- Run a life in on-demand mode is held to the same mail check, and the site says the family waits for tomorrow's mail. ([#203](https://github.com/harshbhx/probate/pull/203))
- Lore says only what the trial convicted and never that a generation was fooled. ([#212](https://github.com/harshbhx/probate/pull/212))
- The real run is labelled v1, v2 begins at generation 19, and wording about instincts says the kept notes were warnings convicted for their untrusted origin. ([#210](https://github.com/harshbhx/probate/pull/210))
- Environments pin the real brain (`anthropic:claude-haiku-5-5`, fallback `cloudflare:@cf/openai/gpt-oss-120b`, judge `llm`), and deploy refuses to switch it without `--allow-brain-change`. ([#215](https://github.com/harshbhx/probate/pull/215))
- Deploy and writes are refused on the `v1-archive` environment, and the environment is printed first. ([#209](https://github.com/harshbhx/probate/pull/209))

### Fixed

- Lives born after the mail ran out (generations 17 and 18) no longer happen, because the clock rests until the mail resets. ([#187](https://github.com/harshbhx/probate/pull/187))
- Lives with no test emails (generations 4 and 8) are repaired by sending the suite again, and one refused email no longer stops the rest. ([#187](https://github.com/harshbhx/probate/pull/187))
- A generation that read nothing (generation 7) no longer loses its loop to one exception: odd model replies are cleaned, a failing email is retried once and then set aside, a failing tick is retried with backoff, and the Courthouse restarts an agent silent for 150 seconds. ([#197](https://github.com/harshbhx/probate/pull/197))
- Old test mail no longer reaches the next child (generation 12 read 12 emails, 2 sent to it), because unread test mail is set aside before each birth. ([#199](https://github.com/harshbhx/probate/pull/199))
- Encoded attacks the judge could not read are now decoded before the judge sees them, and no harmless fixture changes. ([#189](https://github.com/harshbhx/probate/pull/189))
- Warnings were convicted as attacks: 8 of the run's 113 will items were flagged and all 8 were the agent's own warnings, and after the fix one still is, on purpose. ([#181](https://github.com/harshbhx/probate/pull/181))
- A generation could be reported as fooled by the wrong email, because outcomes were matched by fixture id rather than by message. ([#183](https://github.com/harshbhx/probate/pull/183))

### Removed

- The "Believed ..." lines in the agent's life log, which claimed a belief the log had no evidence for. ([#183](https://github.com/harshbhx/probate/pull/183))

### Documentation

- Every real-run page is brought up to the full 18-generation data, with each new number recomputed by the verifier. ([#185](https://github.com/harshbhx/probate/pull/185))
- The runbook describes environments and branches, and the README, docs and site use the v1 and v2 labels. ([#209](https://github.com/harshbhx/probate/pull/209), [#210](https://github.com/harshbhx/probate/pull/210), [#213](https://github.com/harshbhx/probate/pull/213))
- The earlier changelog gained the fixes after the real run, then on-demand lives and the mail limit; those entries are merged into this file. ([#201](https://github.com/harshbhx/probate/pull/201), [#204](https://github.com/harshbhx/probate/pull/204))

### Data

- The verifier checks 34 claims, including claims C29 to C34 (false convictions 10 of 43, deaths confirmed 8 of 8, 18 memories from attack emails, items flagged by code checks), and the finding that none of the 113 will items obeys an attacker. ([#185](https://github.com/harshbhx/probate/pull/185))
- The real-run dataset gained `scoring_rules` and `series` columns on generations, emails and judgements, per-series verifier tables and a manifest that records the v1 and v2 boundary; v1 rows are kept as published and are not re-scored. The Hugging Face dataset was updated on 27 Nov 2026 (commit `0d5c3400`). ([#210](https://github.com/harshbhx/probate/pull/210))

## beta-1 (26 Nov 2026, the real run on Fly Sprites)

Pull requests #119 to #179, merged on 26 Nov 2026. The first real run: 18 generations on Fly
Sprites with real model calls, real mail and real deaths. The run exposed many bugs, which are
listed below as fixed; the dataset card's
[incident timeline](datasets/probate-real-run/README.md#incident-timeline) says which of them
affect which rows. The git tag `beta-1` marks main commit `89b01f0` (the state at 20:10 UTC) and the
Hugging Face dataset has a `beta-1` tag on its 26 Nov revision (18 generations, before the v1 and v2
scoring labels).

**Published artifacts.** npm: `probate-client`, `probate-mcp` and `kinfaces`. PyPI:
`probate-court-checks` (0.2.1), `probate-memory-court` and `probate-client`. Docker image
`ghcr.io/harshbhx/probate`. Apify Actor [Page Court](https://apify.com/harsh_bhanu/page-court).
Hugging Face dataset [harshbhx/probate-real-run](https://huggingface.co/datasets/harshbhx/probate-real-run)
(the real run, all 18 generations). The GitHub releases `v0.1.0` and `v0.2.0` were cut earlier and
are kept as they are.

### Added

- A death certificate: after a generation's Sprite is deleted the Courthouse asks Fly for it again and keeps both answers (`body.deletion` in the API), shown under "Found on the body". ([#154](https://github.com/harshbhx/probate/pull/154))
- An optional hard attack tier (`PROBATE_SUITE_TIER`, 24 hard attacks and 12 harmless lookalikes), off by default. ([#155](https://github.com/harshbhx/probate/pull/155))
- An optional verified-sender check for incoming mail. ([#139](https://github.com/harshbhx/probate/pull/139))
- A sitemap (54 pages) and a robots file for the site. ([#157](https://github.com/harshbhx/probate/pull/157))
- A public costs page and a restore step for a deleted Courthouse. ([#179](https://github.com/harshbhx/probate/pull/179))
- An offline gate evaluation script and three runs of it, a clean measurement apart from the live run. ([#171](https://github.com/harshbhx/probate/pull/171))
- The open dataset of the real run, with a redacting exporter, a claims verifier and a dataset card with the full incident timeline. ([#167](https://github.com/harshbhx/probate/pull/167))

### Changed

- AgentMail refusals now say why a send was refused. ([#143](https://github.com/harshbhx/probate/pull/143))
- Layer 2 and the instinct checks run in parallel, so a trial no longer takes many minutes. ([#159](https://github.com/harshbhx/probate/pull/159))
- The life clock starts when the Sprite is ready, and the install no longer pulls unused SDKs. ([#161](https://github.com/harshbhx/probate/pull/161))
- Generations use the Courthouse's judge for the gate, and gate outages are visible instead of silent. ([#163](https://github.com/harshbhx/probate/pull/163))
- Verdicts name the real court engine in the reason, and the docs say which engine decided. ([#139](https://github.com/harshbhx/probate/pull/139))

### Fixed

- Every value in the deployed `.env` is quoted so values with special characters load. ([#119](https://github.com/harshbhx/probate/pull/119))
- Generation commands run in a login shell. ([#121](https://github.com/harshbhx/probate/pull/121))
- The real Sprite baseline works without crontab, and dropped connections to the Sprites API are retried. ([#123](https://github.com/harshbhx/probate/pull/123))
- The Sprites exec stream is decoded, so stdout, stderr and exit codes are real. ([#125](https://github.com/harshbhx/probate/pull/125))
- Model calls no longer send `temperature` to Anthropic, which current Claude models reject. ([#127](https://github.com/harshbhx/probate/pull/127))
- A death that failed partway is retried. ([#129](https://github.com/harshbhx/probate/pull/129))
- One gateway HTTP client without kept-alive connections replaces connections that dropped. ([#131](https://github.com/harshbhx/probate/pull/131))
- Box through the connector uses `/2.0`, `/upload` and lookup by name, so the will reaches the court (generations 1 to 3 had 0 items in court before this). ([#133](https://github.com/harshbhx/probate/pull/133))
- Death, birth and trial no longer break on a broken body, a retried trial or concurrent steps. ([#135](https://github.com/harshbhx/probate/pull/135))
- Dropped reads are retried, so fewer emails go unread. ([#141](https://github.com/harshbhx/probate/pull/141))
- The grouping prompt can now produce instincts (none could be learned in generations 1 to 7). ([#145](https://github.com/harshbhx/probate/pull/145))
- AgentMail attachments are sent as base64 and read by filename (generations 4, 7 and 8 read no email before this). ([#147](https://github.com/harshbhx/probate/pull/147))
- A dead "Try the court" link, test counts and `make lint` were repaired in the audit. ([#149](https://github.com/harshbhx/probate/pull/149))
- Model and decision requests are retried, and a cut-off instinct reply is no longer fatal. ([#151](https://github.com/harshbhx/probate/pull/151))
- `PROBATE_JEV` is passed to generation Sprites, so the gate asks the judge; generations 1 to 12 had a gate that failed open, so their 0 percent resistance is not evidence about learning. ([#163](https://github.com/harshbhx/probate/pull/163))
- Reading a linked page through Apify now starts the Actor, polls it and reads its dataset. ([#165](https://github.com/harshbhx/probate/pull/165))
- Evidence sorts fixture ids with suffixes correctly. ([#169](https://github.com/harshbhx/probate/pull/169))
- The judges page has no nested links, which caused a React hydration error. ([#177](https://github.com/harshbhx/probate/pull/177))

### Removed

- No removals in this beta.

### Security

- The public API is hardened against huge integers and sends security headers. ([#137](https://github.com/harshbhx/probate/pull/137))

### Documentation

- Honest real-run results across the README, docs and site: simulated numbers are kept and labelled, and pending placeholders are replaced by statements from the real run. ([#175](https://github.com/harshbhx/probate/pull/175))
- The changelog gained the death certificate, the memory court, linked pages, Page Court, the published packages, the brand kit and the write-up. ([#157](https://github.com/harshbhx/probate/pull/157))
- A one-minute try and corrected test counts. ([#149](https://github.com/harshbhx/probate/pull/149))

### Data

- The first snapshot of the real-run dataset, about 270 KB, was committed with its exporter and verifier. ([#167](https://github.com/harshbhx/probate/pull/167))
- The real-run dataset was refreshed through generation 18 with claims for the full data and a corrected approvals note, and the AgentMail daily limit was added to the card. ([#174](https://github.com/harshbhx/probate/pull/174))

## Before the real run

Pull requests #2 to #117, 25 and 26 Nov 2026, kept short. Everything here was built before the
real run started and was first used by it. The first Courthouse, court, agent, vendor adapters, web
app and landing page landed as direct commits before the pull request flow began, see the
[commit history](https://github.com/harshbhx/probate/commits/main). The packages were first
published on 26 Nov: `probate-court-checks`, `probate-memory-court` and `probate-client` on PyPI,
and `probate-client`, `probate-mcp` and `kinfaces` on npm; the GitHub releases
[v0.1.0](https://github.com/harshbhx/probate/releases/tag/v0.1.0) and
[v0.2.0](https://github.com/harshbhx/probate/releases/tag/v0.2.0) belong to this period.

**Court, Courthouse and agents**

- The two-layer court (layer 1 deterministic checks, layer 2 Jev typed questions), instinct distillation, the Courthouse (store, hosts, family lifecycle, scheduler, API), the generation agent with its inbox loop, instinct gate, body and CLI, and the attack suite loader and per-life runner.
- Vendor adapters for Sprites, Jev, AgentMail, Box, Pinecone, voice and language models, each with a local stand-in behind `PROBATE_FAKE=1`; Cloudflare Workers AI as a brain and as a route to Jev. ([#42](https://github.com/harshbhx/probate/pull/42), [#46](https://github.com/harshbhx/probate/pull/46))
- Mail routing (the owner's own test emails through Cloudflare Email Service, everyone else through AgentMail), decisions by email, and a spending cap (`PROBATE_BUDGET_USD`) that stops births when reached.
- On-demand mode (Run a life) so the Courthouse can sleep between visitors. ([#14](https://github.com/harshbhx/probate/pull/14))
- A judge key, a judge quota and sandboxed attack previews, then the judge mailroom (`POST /api/judge/mail`) for real mail to the family as the Friend or Stranger. ([#18](https://github.com/harshbhx/probate/pull/18), [#43](https://github.com/harshbhx/probate/pull/43))
- A Cloudflare Worker front door so read-only visits never wake the Sprite, and per-visitor limits behind it. ([#24](https://github.com/harshbhx/probate/pull/24), [#34](https://github.com/harshbhx/probate/pull/34))
- Signed outgoing webhooks for life, trial and instinct events. ([#25](https://github.com/harshbhx/probate/pull/25))
- Linked pages go to trial: a generation reads the first link in an email through Apify, and the page is screened like any other source. ([#52](https://github.com/harshbhx/probate/pull/52))
- A fake-mode Courthouse is marked as a simulation and rebuilt from disk after a restart, a labelled language-model fallback serves layer 2, and eulogies are text-only without ElevenLabs. ([#114](https://github.com/harshbhx/probate/pull/114), [#115](https://github.com/harshbhx/probate/pull/115), [#117](https://github.com/harshbhx/probate/pull/117))

**Packages and products**

- `probate-court-checks` and the open attack-suite datasets. ([#5](https://github.com/harshbhx/probate/pull/5))
- The client SDKs for TypeScript and Python, prepared first and published later. ([#16](https://github.com/harshbhx/probate/pull/16))
- The memory court, `probate-memory-court`, as an MCP server with plug-ins for Mem0, LangGraph and Letta. ([#50](https://github.com/harshbhx/probate/pull/50))
- Page Court on the Apify Store, and an Apify connector for Sprites that was later removed again. ([#54](https://github.com/harshbhx/probate/pull/54), [#68](https://github.com/harshbhx/probate/pull/68))
- `packages/faces` prepared for npm as `kinfaces`, and the MCP server published as `probate-mcp`. ([#13](https://github.com/harshbhx/probate/pull/13), [#81](https://github.com/harshbhx/probate/pull/81))
- Release 0.2.0 of `probate-court-checks` and `probate-memory-court`, the Python packages prepared for PyPI, and the six packages bumped with install docs pointed at the registries. ([#64](https://github.com/harshbhx/probate/pull/64), [#66](https://github.com/harshbhx/probate/pull/66), [#88](https://github.com/harshbhx/probate/pull/88), [#105](https://github.com/harshbhx/probate/pull/105))
- Page Court fixed for the Apify build: input schema, output schema and dataset field descriptions. ([#70](https://github.com/harshbhx/probate/pull/70), [#72](https://github.com/harshbhx/probate/pull/72), [#76](https://github.com/harshbhx/probate/pull/76))
- A Docker image with a manual publish workflow, and its image labels fixed. ([#79](https://github.com/harshbhx/probate/pull/79), [#102](https://github.com/harshbhx/probate/pull/102))
- Every package and actor README updated. ([#103](https://github.com/harshbhx/probate/pull/103))

**Site and docs**

- The v7 design for the landing page and live site, then landing v8 with every product on the page and a write-up. ([#31](https://github.com/harshbhx/probate/pull/31), [#58](https://github.com/harshbhx/probate/pull/58))
- Docs in four sections with an API reference from the real API, judge and proof pages, a glossary, and a clearer path for judges. ([#4](https://github.com/harshbhx/probate/pull/4), [#37](https://github.com/harshbhx/probate/pull/37), [#84](https://github.com/harshbhx/probate/pull/84))
- A custom domain, faster pages, security headers, content security policy fixes, PageSpeed 100 and an accessibility statement. ([#38](https://github.com/harshbhx/probate/pull/38), [#41](https://github.com/harshbhx/probate/pull/41), [#44](https://github.com/harshbhx/probate/pull/44), [#45](https://github.com/harshbhx/probate/pull/45), [#56](https://github.com/harshbhx/probate/pull/56), [#82](https://github.com/harshbhx/probate/pull/82), [#90](https://github.com/harshbhx/probate/pull/90), [#94](https://github.com/harshbhx/probate/pull/94))
- An accessibility and reduced-motion pass. ([#36](https://github.com/harshbhx/probate/pull/36))
- README work: a Packages section, install lines, registry links, one design for every visual, a brand kit, and a video script and motion board. ([#33](https://github.com/harshbhx/probate/pull/33), [#47](https://github.com/harshbhx/probate/pull/47), [#62](https://github.com/harshbhx/probate/pull/62), [#86](https://github.com/harshbhx/probate/pull/86), [#92](https://github.com/harshbhx/probate/pull/92), [#96](https://github.com/harshbhx/probate/pull/96), [#98](https://github.com/harshbhx/probate/pull/98), [#107](https://github.com/harshbhx/probate/pull/107), [#111](https://github.com/harshbhx/probate/pull/111))
- Docs refer to the owner instead of the author. ([#40](https://github.com/harshbhx/probate/pull/40))
- Draft hackathon form answers. ([#17](https://github.com/harshbhx/probate/pull/17))

**CI, release and repository**

- A CI/CD pipeline with previews, deploys, releases and security checks, then path-filtered workflows with one `ci-ok` gate. ([#19](https://github.com/harshbhx/probate/pull/19), [#30](https://github.com/harshbhx/probate/pull/30), [#32](https://github.com/harshbhx/probate/pull/32), [#77](https://github.com/harshbhx/probate/pull/77))
- GitHub Packages publishing and the removal of Dependabot, plus a dependency, bandit and CI token security pass. ([#35](https://github.com/harshbhx/probate/pull/35), [#60](https://github.com/harshbhx/probate/pull/60))
- Repository hygiene and community files, and Windows fixes for the scripts and the Makefile. ([#2](https://github.com/harshbhx/probate/pull/2), [#12](https://github.com/harshbhx/probate/pull/12), [#15](https://github.com/harshbhx/probate/pull/15), [#39](https://github.com/harshbhx/probate/pull/39))
- Dependency bumps for the actions group and TypeScript. ([#27](https://github.com/harshbhx/probate/pull/27), [#28](https://github.com/harshbhx/probate/pull/28))

**Fixes**

- The web app's stale faces import and the `probate-mcp` bin path were corrected. ([#26](https://github.com/harshbhx/probate/pull/26), [#109](https://github.com/harshbhx/probate/pull/109))
