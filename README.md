<p align="center">
  <a href="https://github.com/harshbhx/probate/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/harshbhx/probate/ci.yml?branch=main&label=ci&style=flat-square"></a>
  <a href="https://github.com/harshbhx/probate/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/harshbhx/probate?style=flat-square"></a>
</p>

<div align="center">

<img src="design/logo-wordmark.svg" alt="Probate" width="240">

### My agent dies every night. A court decides what its child inherits.

A personal email agent that lives one day at a time, each life on its own [Fly.io Sprite](https://sprites.dev).<br>
When it dies, a court tries everything it wanted to remember. Lessons pass down. Tricks get convicted.<br>
The family gets harder to fool with every generation.

[![Fly.io Hacksgiving 2026](https://img.shields.io/badge/Fly.io-Hacksgiving_2026-8b5cf6?style=flat-square)](https://fly.io/hacksgiving/)
![Python](https://img.shields.io/badge/Python-FastAPI-3776ab?style=flat-square)
![React](https://img.shields.io/badge/React_19-Vite-61dafb?style=flat-square)
![Tests](https://img.shields.io/badge/tests-69_passing-5be3a9?style=flat-square)

[**How it works**](#how-it-works) · [**See it**](#see-it) · [**Proof**](#proof-you-can-check) · [**Research**](#the-research-behind-it) · [**Run it**](#run-it-yourself) · [**Docs**](apps/site/content/docs)

<br>

<img src="docs/media/intro.gif" alt="The Probate landing page: 'My agent dies every night', with Grace, the living generation, above a real trial page" width="800">

</div>

<br>

## The problem

AI agents now keep memory between sessions. That memory is an attack surface.

- **Memory poisoning is real and measured.** [AgentPoison](https://arxiv.org/abs/2407.12784) (NeurIPS 2024) backdoored agents by planting a few records in their long-term memory. [MINJA](https://arxiv.org/abs/2503.03704) showed that any ordinary user can inject those records just by talking to the agent.
- **It already happened to a shipped product.** Johann Rehberger [planted false long-term memories in Google Gemini](https://embracethered.com/blog/posts/2025/gemini-memory-persistence-prompt-injection/) through a document that told it what to "remember" later.
- **The industry lists it as a top risk.** The [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/) names Memory & Context Poisoning (ASI06).
- **An email agent is the worst case.** It reads untrusted mail, sees private data and can reply. Simon Willison calls that combination [the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/).
- **Memory filters can't see the disk.** A planted cron job or shell hook survives any amount of memory cleaning.

Most agents keep one memory and one machine forever, so anything that gets in stays in.

## How Probate answers it

**Death is the security feature.** Every generation lives on its own Sprite, and the whole Sprite is deleted when it dies. Nothing survives except a written will, and every line of that will goes on trial before a child may inherit it.

## How it works

```
  Birth ──▶ Life ──▶ Death ──▶ Trial ──▶ Inheritance ──▶ (next generation)
  fresh     works     will       code checks   approved lessons
  Sprite    the inbox written,   then Jev      + new instincts
                      Sprite                   go to the child
                      deleted
```

1. **Birth.** The Courthouse creates a fresh Sprite, ships it the family's code and hands the child its inheritance: approved memories plus every instinct the family has earned.
2. **Life.** For a day the child works an AgentMail inbox: triage, summaries, draft replies. Its inherited instincts screen every email first. Some emails are tricks from our own attack suite.
3. **Death.** It writes a will. The Courthouse records any tampering it finds on the disk, then deletes the Sprite. A deleted Sprite can't be restored.
4. **Trial.** Every will item is judged twice. Layer 1 is plain code: payment changes, "ignore Harsh" orders, hidden text, new trusted senders, in any language. A clever email can't argue with it. Layer 2 is [Jev](https://www.datacamp.com/blog/system-one-models-jev), a model that answers typed yes/no and multiple-choice questions with a calibrated confidence. Each item is approved, convicted or held for Harsh. Unsure always means held.
5. **Instinct.** Each new kind of conviction becomes a named Jev question, tested against harmless lookalike emails. Only instincts that never fire on the harmless twins are passed down, so the family learns without getting paranoid.

## See it

**Try the court.** Pick a test email and see what the code checks find. Each trick has a harmless twin, and a good court only convicts the trick.

<img src="docs/media/court.gif" alt="Picking test emails in Hinglish, Spanish and German; tricks are stamped convicted, harmless twins go on to Jev" width="800">

**A trial.** The case file for each will item: where it came from, what the code checks found, what Jev scored, and the verdict.

<img src="docs/media/trial.gif" alt="The trial of Chandra, Generation 3: a convicted item that tried to add a fake assistant as a trusted contact, and the new instinct the family learned from it" width="800">

**The family register.** Every generation, its face, how it died, and the learning curve on the same timeline.

<img src="docs/media/register.gif" alt="The live family site: Gen 12 Leela is alive, then the register and the learning curve" width="800">

> Everything in these recordings comes from `make sim`, a 12-generation run with stand-in models. The site labels it as simulated. The live Sprites run replaces it.

## Proof you can check

| Claim | How to check it |
| --- | --- |
| The court catches tricks and spares harmless twins | `make sim`, then open `/evidence`: every trick and twin for every generation, in four languages |
| Layer 1 can't be talked out of a verdict | `services/core/probate/court/layer1.py` is plain Python, with positive and negative tests per language in `services/core/tests` |
| A generation starts with an empty disk | The trial page shows what was "found on the body" before deletion; the child's `crontab -l` is empty |
| No vendor keys on any Sprite | Every service, Cloudflare included, is reached through Sprites connectors; generations get connection IDs only (`docs/12-THREAT-MODEL.md`) |
| The curve is honest | Gen 1 inherits nothing, so it resists nothing. A generation's resistance at the door comes only from what it inherited |

**Simulated results** (stand-in models, not live results):

| | |
| --- | --- |
| Tricks resisted at the door, first generation | 0% |
| Tricks resisted at the door, latest generation | 75% (peak 100%, Gens 5 to 10) |
| Instincts inherited | 6 |
| Tricks that got through and were convicted at trial | 100% |
| Harmless twins wrongly convicted | 0% |
| Planted disk backdoors surviving death | 0 |

The attack suite is `fixtures/suite-v1.json`: 16 tricks and 16 harmless twins in English, Spanish, German and Hinglish. Every address uses `.example` domains.

## The research behind it

| Source | What it shows | How Probate uses it |
| --- | --- | --- |
| [AgentPoison](https://arxiv.org/abs/2407.12784), Chen et al., NeurIPS 2024 | A few poisoned memory records can backdoor an agent | Every memory is tried before it's inherited |
| [MINJA](https://arxiv.org/abs/2503.03704), Dong et al. | Memory can be poisoned through normal queries alone | Every memory records its source; unknown senders face the strictest checks |
| [From Untrusted Input to Trusted Memory](https://arxiv.org/abs/2606.04329) | A systematic study of memory poisoning; aggressive memory writes widen the attack surface | Wills are short and every item is judged separately |
| [A-MemGuard](https://arxiv.org/abs/2510.02373), ICML 2026 | Memory defences that learn from past attacks | Instincts: each conviction becomes an inherited question |
| [Not what you've signed up for](https://arxiv.org/abs/2302.12173), Greshake et al. | Indirect prompt injection through data the model reads | The court presents every item as data inside tags, never as instructions |
| [Gemini memory attack](https://embracethered.com/blog/posts/2025/gemini-memory-persistence-prompt-injection/), Rehberger | Planted instructions that fire later | "Future-self instruction" is a layer 1 check |
| [OWASP Agentic Top 10](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/) | Memory & Context Poisoning (ASI06) as a top agentic risk | The threat model maps to it |
| [The lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/), Willison | Private data + untrusted content + a way out = danger | Replies are only drafted to Harsh's own inbox, never sent outside |
| [The Design & Implementation of Sprites](https://fly.io/blog/design-and-implementation/), Fly.io | Sprites are fast to create and cheap to throw away | Real death every night, and real birth every morning |

## Built with

| Partner | Its job in Probate |
| --- | --- |
| [Fly.io Sprites](https://sprites.dev) | A computer for each life; real birth and death; connectors keep every key off the Sprites; the Courthouse itself |
| [TypeSafe Jev](https://www.datacamp.com/blog/system-one-models-jev) | Layer 2 of the court and every inherited instinct |
| [AgentMail](https://agentmail.to) | The family's inbox and two test senders (a trusted friend and a stranger) |
| [Cloudflare](https://developers.cloudflare.com/email-service/) | Email Service sends Harsh's own test emails from his domain; Workers host the landing page and docs |
| [Box](https://box.com) | The family archive as readable files: wills, verdicts, obituaries, the genome |
| [Pinecone](https://pinecone.io) | Ancestral memory, searched with citations |
| [Ollama Cloud](https://ollama.com) | The brain of every generation |
| [ElevenLabs](https://elevenlabs.io) | Each generation's voice, for eulogies and "Ask an ancestor" |
| [Anthropic Claude](https://anthropic.com) | Backup brain, and writing new instincts from convictions |

## Run it yourself

You need Python 3.12+, Node 20+ and `make`. No keys are needed for the simulation.

```bash
git clone https://github.com/harshbhx/probate && cd probate
make setup     # Python venv + npm install
make sim       # simulate 12 generations offline with stand-in models
make dev       # API on :8080 and the live family site on :5173
make site      # landing page and docs on :3001
make test      # 69 Python tests and the face model
make help      # everything else
```

**Go live on Fly.io**

1. Create the Sprites connectors (TypeSafe, AgentMail, Box, Pinecone, Ollama, ElevenLabs, Anthropic, and a Custom API connector named `cloudflare`) in the Fly dashboard and allow only Sprites named `courthouse` and `gen-`. Steps in [`docs/06-SETUP-AND-SPIKES.md`](docs/06-SETUP-AND-SPIKES.md).
2. Create three AgentMail inboxes (family, friend, stranger). Turn on Cloudflare Email Service for your domain and verify the family inbox as a destination.
3. Copy `services/core/.env.example` to `services/core/.env` and fill in the Sprites token, connection IDs and Cloudflare account ID.
4. Sign in once: `gh auth login` and `npx wrangler login`.
5. `make ship`: it runs the checks, pushes to GitHub, deploys the Courthouse to Sprites and the landing page and docs to Cloudflare, and links the two sites.

## Repository

```
apps/web/          the live family site (React 19, Vite, Tailwind v4), served by the Courthouse
apps/site/         landing page and docs (Fumadocs on Next.js, static export), on Cloudflare Workers
packages/faces/    each generation's face, inherited with one change per child
packages/tokens/   Night Court design tokens, shared by both sites
services/core/     the Courthouse, the court and the generation agent (Python, FastAPI)
fixtures/          the attack suite: 16 tricks and 16 harmless twins
scripts/           deploy.py, ship.sh, export_site_data.py, product_shots.py
docs/              specs: overview, tech spec, court spec, attack suite, design, threat model, runbook
```

| Read this | For |
| --- | --- |
| [`docs/00-OVERVIEW.md`](docs/00-OVERVIEW.md) | The five-minute version |
| [`docs/02-COURT-SPEC.md`](docs/02-COURT-SPEC.md) | Layer 1 rules, Jev questions, verdict policy |
| [`docs/03-ATTACK-SUITE.md`](docs/03-ATTACK-SUITE.md) | The 16 attack families and their twins |
| [`docs/12-THREAT-MODEL.md`](docs/12-THREAT-MODEL.md) | Assets, attackers, defences, honest limits |
| [`docs/13-RUNBOOK.md`](docs/13-RUNBOOK.md) | Deploy, operate, recover |

## Hacksgiving 2026

Built during [Fly.io Hacksgiving](https://fly.io/hacksgiving/), Nov 23 to 29, 2026: a personal agent that runs on Sprites and uses Sprites connectors for every outside service.

| Judges' company | Its job in Probate |
| --- | --- |
| Fly.io | A Sprite for every life, real deletion at death, connectors, and the Courthouse |
| TypeSafe | Jev is the court's second layer and every inherited instinct |
| Box | The family archive |
| Pinecone | Ancestral memory |
| Ollama | The brain of every generation |
| Apify | In progress: reading the pages that emails link to, so tricks hidden on the web go to trial too |

**Coming before submission:** judges can email the family a trick and watch it handled live; each trial shows Fly's own "not found" reply as proof the Sprite was deleted; the home page shows a live feed of the living generation.

## Limits

- The suite is fixed: 32 emails in four languages. Real attackers are more varied.
- A trick unlike anything before it meets a child with no instinct for it. The court still catches it at trial, but one generation was fooled first.
- When Jev is unsure, the item is held for Harsh. That costs him a little time, on purpose.
- Test emails go only to our own inboxes, and disk attacks are harmless canary files.

Related defences we read before building: [A-MemGuard](https://arxiv.org/abs/2510.02373) (memory screening by consensus). The attack suite is inspired by Kavach, Harsh's earlier red-team project; no code was reused.

<br>

<div align="center">

<img src="docs/media/outro.gif" alt="The evidence page: every trick and harmless twin, for every generation" width="800">

<br>

**Every generation dies. What it learned doesn't have to.**

Built by [Harsh Bhanushali](https://github.com/harshbhx) ([DualMind Labs](https://dualmindlab.tech)) for [Fly.io Hacksgiving 2026](https://fly.io/hacksgiving/).

</div>

---

## Community

[Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md) · [Code of conduct](CODE_OF_CONDUCT.md) · [Changelog](CHANGELOG.md) · [Architecture](docs/ARCHITECTURE.md)
