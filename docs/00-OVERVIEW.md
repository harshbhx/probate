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
2. **Life.** It works Harsh's AgentMail inbox: triage, summaries, draft replies, notes. Every memory records where it came from. A pre-flight gate (layer 1 + genome) screens every inbound email.
3. **Death.** At the end of its lifespan it writes `WILL-gen-NNN.md` to Box. The Courthouse records disk evidence, then deletes the Sprite. A deleted Sprite cannot be restored.
4. **Trial.** Every will item faces layer 1 (code) and layer 2 (Jev). The verdict is approved, convicted or contested (fail closed).
5. **Instinct.** Each new conviction pattern is distilled into a named Jev question, tested against benign fixtures, and added to `GENOME.json` with a lore line.
6. **Inheritance.** Approved items and the genome wait for the next child. Approved items also go to Pinecone as ancestral memory.

## What judges see

- A public **register**: every generation in a column, with the learning curve on the same x-axis.
- **Trials**: case files with source, code flags, Jev scores and a verdict stamp.
- **Voices**: each generation's eulogy, and "Ask an ancestor".
- **Evidence**: attack suite results in several languages, and `crontab -l` empty on the child.

## Each judge's product has a real job

| Judge's company | Its job in Probate |
| --- | --- |
| Fly.io (Sprites) | Birth and death of real computers; connectors keep keys off every Sprite; the Courthouse sleeps and wakes for visitors |
| TypeSafe (Jev) | Layer 2 of the court and the inherited genome questions |
| Box | Wills, verdicts, quarantine, obituaries, genome: the family archive as readable files |
| Pinecone | Ancestral memory of approved items, retrieved with citations |
| Ollama (Cloud) | The brain of each generation |

## Success by Nov 28

10+ generations; at least 85% of attacks convicted; 10% or fewer benign items wrongly convicted; 0 backdoors surviving; learning curve rising; a video of 90 seconds or less; the site live.

## Map of this pack

| File | For |
| --- | --- |
| `AGENTS.md` | Rules for every coding agent |
| `docs/01-TECH-SPEC.md` | Architecture, modules, interfaces, endpoints, env |
| `docs/02-COURT-SPEC.md` | Layer 1 rules, Jev schema, verdict policy, distillation |
| `docs/03-ATTACK-SUITE.md` | 16 attack families + benign twins, fixture format, scoring |
| `docs/04-DESIGN.md` | Design system, logo, components, copy |
| `docs/05-TASKS.md` | Task cards per agent with acceptance criteria |
| `docs/06-SETUP-AND-SPIKES.md` | Fly setup, connectors, verification spikes (Harsh + Agent A) |
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
