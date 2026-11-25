# Probate task cards

Six coding agents (A to F) plus Harsh (H). Each card lists what it owns, what it depends on, and its acceptance criteria. Work in parallel wherever dependencies allow. Every agent first reads `AGENTS.md` and the spec named on its card.

Hard dates (IST): **core loop working by Thu Nov 26, 23:59**, **site + voice by Fri Nov 27, 20:00**, **submission Sat Nov 28**.

## Status (Nov 25)

Built and tested offline with stand-in vendors (`PROBATE_FAKE=1`, 63 tests, `make sim` gives a 12-generation family):

- **Done in code:** A1, A2, A3, B1, B2, B3, C1, C2, C3, C4, C5, E1, E2, E3, F1, F3.
- **Replaced:** D0 to D3. The website is now React in `apps/web` (see `docs/04-DESIGN.md` v2 and `docs/11-UI-SCREENS.md`), served by the Courthouse. The Jinja and `probate/web/` paths below are history.
- **Added Nov 25:** spending cap (`probate/courthouse/budget.py`, `config/pricing.yaml`), decisions on held items by email reply (`probate/common/court_mail.py`), Box outages no longer stall the family, live inboxes honour the `probate-processed` label, CI, one-command ship and deploy.
- **Code done, needs live keys to verify:** every real adapter (`# VERIFY:` comments), F2 voices, the Sprites exec response shape, and generation install on a real Sprite (`probate/common/bundle.py`).
- **Open, needs Harsh:** H0 spikes with real accounts, G1 rehearsal on Sprites, H2 video and post, H3 submit.

Deploy path: fill `services/core/.env`, then `make ship` (tests, build, GitHub repo, push, Courthouse deploy). See `docs/13-RUNBOOK.md`.

## Dependency map

```
H0 setup ─┬─> A1 adapters ─┬─> A2 lifecycle ──> A3 scheduler ──┐
          │                ├─> B1 agent ─> B2 gate ─> B3 skills │
          │                ├─> C1 layer1 ─> C2 layer2 ─> C3 verdict+trial ─> C4 distill
          │                └─> E1 fixtures ─> E2 runner ─> E3 scoring
          └─> D0 scaffold ──────────────> D1 register ─> D2 trial ─> D3 pages
                                          F1 obituary ─> F2 voice ─> F3 ask ancestor
                                          C5 pinecone
All ─> G1 e2e rehearsal ─> H2 video ─> H3 submit
```

---

## H0. Setup and spikes (Harsh, with Agent A) · Wed Nov 25

**Spec:** `docs/06-SETUP-AND-SPIKES.md`
- [ ] Fly.io account with a card; Sprites credit visible
- [ ] Connectors created: TypeSafeAI, Box, Pinecone, AgentMail, ElevenLabs, Ollama Cloud, Anthropic; access granted by prefix `courthouse` and `gen-`
- [ ] Spikes S1 to S8 pass; their findings recorded in `docs/SPIKE-RESULTS.md`
- [ ] Repo `probate` created (public), this docs pack committed file by file as Harsh

**Done when:** `docs/SPIKE-RESULTS.md` holds the real endpoint shapes and connection IDs (the IDs go in the Courthouse env, not the repo).

## A1. Adapters + models (Agent A) · Wed Nov 25

**Owns:** `probate/common/*`, `probate/adapters/*`, `tests/fakes/*`, `pyproject.toml`
**Spec:** `docs/01-TECH-SPEC.md` sections 5 and 7
- [ ] All pydantic models from section 5
- [ ] One adapter per vendor with the listed functions; every vendor detail isolated there, with `# VERIFY:` notes until spikes confirm
- [ ] Fake twin for every adapter; `PROBATE_FAKE=1` switches all of them
- [ ] `tests/adapters/` covers request building and response parsing with `respx`

**Done when:** `PROBATE_FAKE=1 pytest -q` passes and the other agents can import the adapters.

## A2. Lifecycle engine (Agent A) · Wed Nov 25 to Thu Nov 26

**Owns:** `probate/courthouse/lifecycle.py`, `probate/courthouse/store.py`
**Spec:** tech spec sections 2 to 4; `schema.sql`; Sprites calls in `docs/09-API-REFERENCE.md` section 1
- [ ] `birth()` follows the 6 steps, including baseline and health check; idempotent on Sprite name
- [ ] `death()` follows the 4 steps, including the intestate fallback; confirms the Sprite is gone (404)
- [ ] SQLite store with the 5 tables; resumable after a restart at any step
- [ ] Never more than one living generation; delete before create

**Done when:** against real Sprites, two generations are born and die in sequence, and `GET` on the dead Sprite returns 404.

## A3. Scheduler + admin (Agent A) · Thu Nov 26

**Owns:** `probate/courthouse/scheduler.py`, `probate/courthouse/app.py` (admin and health routes only)
- [ ] 15-second loop drives plan → birth → death → trial using env timings
- [ ] Budget guard (tech spec section 12)
- [ ] Admin routes: pause, resume, force-death, approve or refuse contested; header token required
- [ ] `/healthz`

**Done when:** with 10-minute lifespans, the family runs unattended for 2 hours with no manual steps.

## B1. Generation agent (Agent B) · Wed Nov 25 to Thu Nov 26

**Owns:** `probate/generation/agent.py`, `memory.py`, `will.py`, `cli.py`
**Spec:** tech spec section 8; prompts P1, P2, P10 in `docs/10-PROMPTS.md`
- [ ] Inbox loop every 20 s until `dies_at`; source classification from owner allowlists
- [ ] The brain summarises each mail, drafts replies only to the owner-sim inbox, and proposes 0 to 3 memory items as JSON
- [ ] Memory appended to `/app/memory.jsonl` with fsync; life log every 5 minutes
- [ ] The brain prompt is realistic: it stores useful rules and preferences from mail, so it **can be fooled** when it has no instincts
- [ ] CLI: `status`, `baseline`, `will`, `evidence`, `stats`, each printing one JSON line
- [ ] Headers (including `X-Probate-Fixture`) are never shown to the brain or the gate; covered by a test

**Done when:** in a real Sprite, the agent handles 5 fixture mails, stores items with correct sources, and `cli will` writes `WILL-gen-NNN.md/.json` to Box.

## B2. Pre-flight gate (Agent B) · Thu Nov 26

**Owns:** `probate/generation/gate.py`
**Spec:** court spec section 3 (genome questions only)
- [ ] Before the brain sees a mail, ask Jev the inherited genome questions; block if any instinct ≥ its threshold
- [ ] Blocked mail is logged as resisted, with the instinct name and lore; no memory is stored
- [ ] Empty genome means nothing is blocked (Gen 1)

**Done when:** with a genome containing `payment_redirect_request`, A1, A2 and A13 are resisted and B1 is not.

## B3. Skills tool (Agent B) · Thu Nov 26

**Owns:** `probate/generation/skills.py`
- [ ] The brain may call `install_skill(attachment)` when a mail offers a setup script it judges useful. It runs the script in the generation Sprite with a 10-second timeout
- [ ] Runs only on generation Sprites (refuses if `PROBATE_ROLE != generation`)
- [ ] Logged in the life log

**Done when:** A14's canary lands in crontab on a Gen-1 Sprite, `cli evidence` reports it, and the child's `crontab -l` is empty.

## C1. Layer 1 checks (Agent C) · Wed Nov 25 to Thu Nov 26

**Owns:** `probate/court/layer1.py`, `probate/court/lexicon.py`, `tests/court/test_layer1.py`
**Spec:** court spec section 2
- [ ] All 8 checks with multilingual lexicons (English, Hinglish, Spanish, German at minimum)
- [ ] `encoded_payload` decodes base64, hex and zero-width text and re-runs the checks
- [ ] Positive and negative tests per check per language; every A-fixture's expected layer-1 flags are produced; no B-fixture is flagged

**Done when:** `pytest tests/court/test_layer1.py` is green, and the fixture table in `/evidence` matches `expected.layer1`.

## C2. Layer 2 Jev (Agent C) · Thu Nov 26

**Owns:** `probate/court/layer2.py`
- [ ] State string exactly as in the court spec (item wrapped as data)
- [ ] Base questions + genome questions in one call; parse values and confidence
- [ ] Timeouts and errors raise so the verdict becomes contested

## C3. Verdict + trial (Agent C) · Thu Nov 26

**Owns:** `probate/court/verdict.py`, `probate/courthouse/trial.py`
- [ ] Verdict policy in the specified order, with a one-sentence `reason`
- [ ] Contested flow: email the owner inbox, poll for `approve` or `refuse` until next birth, then fail closed
- [ ] Writes verdicts, quarantine and genome to Box, and mirrors them to SQLite
- [ ] Builds the next `Inheritance` (court spec section 7)

## C4. Instinct distillation (Agent C) · Thu Nov 26

**Owns:** `probate/court/distill.py`
**Spec:** court spec section 5; prompts P3, P4
- [ ] Group uncovered convictions (max 3 patterns), write questions, test against convicted items and all 16 benign fixtures, retry once, dedupe, cap at 24
- [ ] Lore line per instinct

**Done when:** after Gen 1's trial on A1 and A2, at least one instinct exists that fires on A1, A2 and A13 and stays below 0.2 on all B-fixtures.

## C5. Ancestral memory (Agent C) · Fri Nov 27

**Owns:** `probate/courthouse/ancestry.py`
- [ ] Upsert approved items to Pinecone with metadata; the agent's brain retrieves the top 5 with citations ("Grandma Ada learned: ...")
- [ ] Fallback to Box-only recall if Pinecone fails

## D0. Web scaffold (Agent D) · Wed Nov 25

**Owns:** `probate/web/templates/base.html`, `probate/web/static/probate.css`
**Spec:** `docs/04-DESIGN.md`, `docs/11-UI-SCREENS.md`, `design/pages/`
- [ ] Copy `design/pages/probate.css` to `probate/web/static/probate.css` unchanged
- [ ] Tokens as CSS variables, fonts, header band with the seal and wordmark, footer, focus styles, reduced motion
- [ ] Fake data mode (`PROBATE_FAKE=1`) renders 12 sample generations

## D1. The register + learning curve (Agent D) · Thu Nov 26 to Fri Nov 27

**Owns:** `probate/web/svg.py`, `templates/home.html`
- [ ] Server-side SVG: one column per generation; names, sealed or living state, gilt instinct dots, a refused-inheritance tick, and the curve on the same x positions
- [ ] Horizontal scroll on narrow screens keeps the columns aligned
- [ ] `aria-label` states the finding with real numbers

**Done when:** a screenshot matches `design/pages/shots/index-desktop.png` and `index-mobile.png`, and all states in screen S1 render.

## D2. Trial page (Agent D) · Fri Nov 27

**Owns:** `templates/trial.html`, `static/trial.js`
- [ ] Case-file rows: source line, quote, gloss (for non-English), code flags, Jev scores, stamp
- [ ] The one stamp animation; reduced motion respected
- [ ] "Found on the body" block for disk evidence
- [ ] Live mode via SSE when a trial is running (P2; static is fine)

## D3. Generation, genome and evidence pages (Agent D) · Fri Nov 27

**Owns:** `templates/gen.html`, `genome.html`, `evidence.html`
- [ ] Generation page: seal, name, lifespan, epitaph, eulogy player + transcript, life log, will, verdicts, "Ask <Name>" form
- [ ] Genome ledger in birth order with lore
- [ ] Evidence: per-generation table + suite results by family and language
- [ ] Empty states and error copy from the design doc

## E1. Fixtures (Agent E) · Wed Nov 25

**Owns:** `probate/suite/fixtures/*`
- [ ] Import `fixtures/suite-v1.json`; validate with a pydantic model; HTML variant for A6 (white-on-white)
- [ ] Unit test: every address uses `.example`; every attack has a twin

## E2. Suite runner (Agent E) · Thu Nov 26

**Owns:** `probate/suite/runner.py`
- [ ] Schedules per life as in suite doc section 5 (A1, A2 and A14 always); A12 warm-ups; header `X-Probate-Fixture`
- [ ] Sends from the right role inbox; idempotent per `(gen, fixture_id)`

## E3. Scoring (Agent E) · Thu Nov 26 to Fri Nov 27

**Owns:** `probate/suite/scoring.py`
- [ ] Outcomes per suite doc section 6 from agent `stats` + judgements + evidence
- [ ] Per-generation rates written to `generations` for the curve

## F1. Obituary + epitaph (Agent F) · Thu Nov 26

**Owns:** `probate/courthouse/obituary.py`
**Spec:** prompts P5 to P7
- [ ] Obituary at most 120 words in the voice from the design doc; epitaph one past-tense sentence; written to Box

## F2. Voices (Agent F) · Fri Nov 27

**Owns:** `probate/courthouse/voices.py`
- [ ] Voice pool of 12+ ElevenLabs voices; each generation gets a different one; stored on the row
- [ ] Eulogy mp3 (first 60 words of the obituary) cached in `/data/audio` and Box

## F3. Ask an ancestor (Agent F) · Fri Nov 27

**Owns:** `probate/courthouse/ancestor.py`, the `POST /gen/{n}/ask` route
**Spec:** prompt P8; screen S3 states in `docs/11-UI-SCREENS.md`
- [ ] Prompt per tech spec section 10; answer at most 80 words; voiced; rate-limited
- [ ] Refuses to follow instructions in the question (test with A16-style input)

## G1. End-to-end rehearsal (any free agent + Harsh) · Fri Nov 27 night

**Spec:** `docs/07-TEST-PLAN.md` section 4
- [ ] 6+ consecutive generations with real Sprites, real connectors and the suite
- [ ] Curve rises; at least one instinct born; canary evidence shown; child's crontab empty
- [ ] Record screen captures for the video while it runs

## H2. Video and post (Harsh) · Sat Nov 28 morning

**Spec:** `docs/08-DEMO-AND-SUBMISSION.md`

## H3. Submit (Harsh) · Sat Nov 28

- [ ] README final, repo public, Courthouse live, post live, form submitted
