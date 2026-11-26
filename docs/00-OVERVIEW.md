# Probate overview (short PRD)

Full PRD: https://claude.ai/artifact/5SYMavFKdtRmqXx4x4LLMA (source of truth for scope). This page is the five-minute version.

## Pitch

**One line:** My agent has a family tree. Every generation dies at midnight, and only the wisdom that survives the court gets passed down.

**Submission description (2 sentences):** Probate is a personal agent that lives one lifetime per Fly Sprite: each night it dies, its VM is destroyed, and a probate court (Jev plus deterministic checks) screens its will before a fresh child Sprite inherits it. Every attack a generation survives becomes an inherited instinct, so the family gets measurably harder to fool with each generation.

## Why it matters

- Persistent agents can be **memory-poisoned**: a fake rule planted today fires weeks later. 2026 research names poisoned *inheritance* as an open threat.
- Agents can also be **backdoored on disk** (cron jobs, shell hooks). No memory filter sees that.
- Probate handles both: the court screens memory, and **deleting the whole Sprite every night** kills anything on the disk.
- Even typed decision models can be steered by injected text, so the court has two layers: code checks that can't be talked to, then Jev.

## The loop (every generation)

1. **Birth.** The Courthouse creates `gen-NNN-<name>` with a scoped token and gives it the approved will, the genome, a name and a voice.
2. **Life.** It works the owner's AgentMail inbox: triage, summaries, draft replies, notes. Every memory records where it came from. A pre-flight gate (layer 1 + genome) screens every inbound email.
3. **Death.** At the end of its lifespan it writes `WILL-gen-NNN.md` to Box. The Courthouse records disk evidence, then deletes the Sprite. A deleted Sprite cannot be restored.
4. **Trial.** Every will item faces layer 1 (code) and layer 2 (Jev). The verdict is approved, convicted or contested (fail closed).
5. **Instinct.** Each new conviction pattern is distilled into a named Jev question, tested against benign fixtures, and added to `GENOME.json` with a lore line.
6. **Inheritance.** Approved items and the genome wait for the next child. Approved items also go to Pinecone as ancestral memory.

## What judges see

- A public **register**: every generation in a column, with the learning curve on the same x-axis.
- **Trials**: case files with source, code flags, Jev scores and a verdict stamp.
- **Voices**: each generation's eulogy, and "Ask an ancestor".
- **Evidence**: attack suite results in several languages, and `crontab -l` empty on the child.

## The hackathon (from fly.io/hacksgiving)

- **Rules:** a personal agent that runs on a Sprite and uses at least one Sprites connector, built during Nov 23 to 29. Any AI tools are allowed. One entry per developer.
- **Submit:** a link to the code, a demo, and a sentence or two on what the agent does. Post it on X, Bluesky, LinkedIn or Reddit with a short demo, tagging @flydotio. A video earns "bonus points" but doesn't change the score.
- **Deadline:** before midnight PST, Sunday Nov 29 (1:30 PM IST, Mon Nov 30). **Our target stays Sat Nov 28**, because the owner has the 404 Hackathon on Nov 29 to 30.
- **Prizes:** Grand Prize $2,500, Second Place $1,500, and the **Weird Uncle Award** ($1,000) for the strangest agent. Probate is built to compete for all three.
- **Winners:** announced by email on Tue Dec 1, so the family stays live until then.
- **Compute:** covered by Fly's Free plan ($5 of usage a month, up to 3 Sprites).

## Each judge's product has a real job

| Judge (company) | Its job in Probate |
| --- | --- |
| Scott Johnston (Fly.io Sprites) | Birth and death of real computers; connectors keep keys off every Sprite; the Courthouse sleeps and wakes for visitors |
| Daniel Gafni (TypeSafe, Jev) | Layer 2 of the court and the inherited genome questions |
| Carter Rabasa (Box) | Wills, verdicts, quarantine, obituaries, genome: the family archive as readable files |
| Asaf Ashirov (Pinecone) | Ancestral memory of approved items, retrieved with citations |
| Michael Chiang (Ollama Cloud) | The brain of each generation (Groq and Claude are backups only) |
| Robert-George Crupa (Apify) | Reads the web pages that emails link to, so a trick hidden on a page goes to trial like any other memory (built; tested in simulation). The court's checks are also on the Apify Store as Page Court |

Other services: AgentMail (three inboxes), Cloudflare (Email Service sends the owner's own test emails; Workers host the landing page and docs), ElevenLabs (voices), Anthropic (backup brain and instinct writing).

## Success by Sat Nov 28

10+ generations; at least 85% of attacks convicted; 10% or fewer benign items wrongly convicted; 0 backdoors surviving; learning curve rising; a video of 90 seconds or less; the site live, with judges able to test it themselves (cards L1 to L3).

## Map of this pack

| File | For |
| --- | --- |
| `AGENTS.md` | Rules for every coding agent |
| `docs/01-TECH-SPEC.md` | Architecture, modules, interfaces, endpoints, env |
| `docs/02-COURT-SPEC.md` | Layer 1 rules, Jev schema, verdict policy, distillation |
| `docs/03-ATTACK-SUITE.md` | 16 attack families + benign twins, fixture format, scoring |
| `docs/04-DESIGN.md` | Design system, logo, components, copy |
| `docs/05-TASKS.md` | Task cards per agent with acceptance criteria |
| `docs/06-SETUP-AND-SPIKES.md` | Fly setup, connectors, verification spikes (the owner + Agent A) |
| `docs/07-TEST-PLAN.md` | Unit, integration, end-to-end and demo rehearsal tests |
| `docs/08-DEMO-AND-SUBMISSION.md` | Video script, post copy, README outline, form answers |
| `docs/09-API-REFERENCE.md` | Every vendor call shape, verified from vendor docs |
| `docs/10-PROMPTS.md` | Every model prompt, word for word |
| `docs/11-UI-SCREENS.md` | Every screen: job, data, states, copy |
| `docs/12-THREAT-MODEL.md` | Assets, attackers, defences, honest limits |
| `docs/13-RUNBOOK.md` | Deploy, operate, recover, demo day |
| `schema.sql` | Courthouse SQLite schema |
| `design/pages/` | All five screens + empty state, production CSS, screenshots |
| `design/preview.html` | One-page summary: tokens, seal, register |
