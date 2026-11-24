<p><img src="design/logo-wordmark.svg" alt="Probate" width="260"></p>

**My agent has a family tree. Every generation dies at midnight, and only the wisdom that survives the court gets passed down.**

Live register: `https://<courthouse>.sprites.app` · Video: `<link>` · Built for [Fly.io Hacksgiving 2026](https://fly.io/hacksgiving/)

> Draft README. Fill in the links, results and images on Nov 27 and 28. Outline: `docs/08-DEMO-AND-SUBMISSION.md` section 4.

## Why this needs Sprites

- **Real death.** Each generation lives on its own Fly.io Sprite, which is deleted when the generation dies. A deleted Sprite can't be restored, so nothing survives except the will.
- **Disk backdoors die with the body.** A memory filter can't see a planted cron job or shell hook. Deleting the computer removes them.
- **No keys on any Sprite.** Every outside service (Jev, Box, Pinecone, AgentMail, ElevenLabs, Ollama) is reached through Sprites connectors.

## How it works

1. **Birth.** A new generation is born on a fresh Sprite with a name, a voice, the approved will and the family genome.
2. **Life.** It works Harsh's inbox for a day. Every memory records where it came from. Its inherited instincts screen every email first.
3. **Death.** It writes its will to Box. The Courthouse records any disk tampering, then deletes the Sprite.
4. **Trial.** Every will item is judged twice: deterministic code checks, then Jev's typed questions with calibrated confidence. Verdict: approved, convicted or contested (fail closed).
5. **Instinct.** Each new scam the court catches becomes a Jev question that every later generation is born with.
6. **Inheritance.** Approved items go to the child and to Pinecone as ancestral memory.

## Results

_To fill in from `/evidence`: generations, resistance rate (Gen 1 vs latest), conviction rate, false conviction rate, backdoors surviving (0)._

## Who does what

| Partner | Job in Probate |
| --- | --- |
| Fly.io Sprites | Birth and death of real computers; connectors; the Courthouse sleeps and wakes for visitors |
| TypeSafe Jev | The court's second layer and the inherited instincts |
| Box | The family archive: wills, verdicts, quarantine, obituaries, genome |
| Pinecone | Ancestral memory with citations |
| Ollama Cloud | The brain of every generation |
| ElevenLabs | Each generation's voice |

## Threat model and limits

_To fill in from `docs/02-COURT-SPEC.md` and spike results: what the court can miss, token scope, canary-only disk tests, `.example` domains._

## Prior art

Anima-i (generational agents), A-MemGuard and MemSentry (memory screening), AgentGuard (guardrails from failures), AgentRewind (rollback). The attack suite is inspired by Kavach, Harsh's earlier red-team project; no code was reused.

## Run it yourself

See `docs/06-SETUP-AND-SPIKES.md` for connectors, and `docs/01-TECH-SPEC.md` section 11 for environment variables.

---

Built by Harsh Bhanushali (DualMind Labs) for Fly.io Hacksgiving 2026.
