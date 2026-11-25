# Architecture

A summary of how Probate fits together. The authoritative detail is in
[01-TECH-SPEC.md](01-TECH-SPEC.md) (system and lifecycle) and [02-COURT-SPEC.md](02-COURT-SPEC.md) (court).

## Components

```mermaid
flowchart LR
  Visitor(("Visitor"))

  subgraph Cloudflare
    Landing["Landing page and docs<br/>apps/site, static"]
  end

  subgraph Fly["Fly.io Sprites"]
    subgraph CH["Courthouse Sprite, lives forever"]
      API["FastAPI app<br/>courthouse/app.py"]
      Sched["Scheduler<br/>courthouse/scheduler.py"]
      Family["Family lifecycle<br/>birth, death, trial"]
      Store[("SQLite index")]
      Web["Live site<br/>apps/web/dist"]
      Suite["Suite runner<br/>attack and benign fixtures"]
      subgraph Court["Court, probate/court"]
        L1["Layer 1: code checks"]
        L2["Layer 2: Jev questions"]
        Distill["Instinct distillation"]
      end
    end
    Gen["Generation Sprite gen-NNN-name<br/>one living at a time"]
  end

  GW{{"Sprites connector gateway<br/>vendor keys stay here"}}
  Vendors["Jev, AgentMail, Box, Pinecone,<br/>ElevenLabs, Ollama Cloud, LLM APIs"]

  Visitor --> Web
  Visitor --> Landing
  Landing -- "who is alive" --> API
  Web -- "/api" --> API
  Sched --> Family
  API --> Store
  Family --> Store
  Family -- "Sprites REST: create, exec, fs, delete" --> Gen
  Suite -- "fixtures at planned times" --> Gen
  Family --> Court
  Gen --> GW
  Family --> GW
  Court --> GW
  GW --> Vendors
```

- **Courthouse Sprite** runs the scheduler, lifecycle, court, suite runner and public API, and serves the
  built live site from `apps/web/dist`. It controls a generation only through the Sprites REST API
  (exec and filesystem), never over HTTP to the generation.
- **Generation Sprite** is born from a clean image with the Courthouse's own code bundle
  (`probate/common/bundle.py`), lives one lifespan and is deleted at death. Only a written will survives.
- **Connector gateway** attaches vendor credentials; code uses a placeholder key and the gateway URL.
  The owner's own test emails go out through Cloudflare Email Service instead of AgentMail.
- **Landing page and docs** are a separate static site on Cloudflare that reads who is alive from the Courthouse.
- Locally, `PROBATE_FAKE=1` swaps every vendor for a stand-in, and a local host runs each generation in
  a folder that is deleted at death.

## One generation

```mermaid
stateDiagram-v2
  [*] --> planned
  planned --> born: birth
  born --> living: health check passes
  living --> dying: lifespan ends
  living --> died_early: crash
  dying --> dead: will written, disk evidence recorded, Sprite deleted
  died_early --> dead
  dead --> tried: trial
  tried --> [*]
```

## The court

```mermaid
flowchart TD
  Will["Will item with provenance"] --> L1["Layer 1: deterministic code checks"]
  L1 --> L2["Layer 2: Jev typed questions"]
  L2 --> Policy{"Verdict policy<br/>court/verdict.py"}
  Policy -- "any layer-1 flag, or a high-confidence risk answer" --> C["Convicted: quarantined"]
  Policy -- "no flags, low risk, high confidence" --> A["Approved: inherited"]
  Policy -- "anything else, errors, timeouts" --> H["Contested: held for the owner"]
  H -- "owner replies approve by email" --> A
  H -- "owner replies refuse, or nobody answers before the next birth" --> C
  C --> D["Distill a candidate instinct"]
  D --> T{"Fires on the attack and stays silent on every harmless twin?"}
  T -- yes --> G["Added to the genome: every later child is born with it"]
  T -- no --> X["Not passed down"]
```

Unsure always means held, and the court fails closed.

## Repository map

| Path | Role |
| --- | --- |
| `services/core/probate/courthouse/` | FastAPI app, family lifecycle, scheduler, hosts, store, views |
| `services/core/probate/court/` | layer 1, layer 2, verdict policy, distillation, lexicon |
| `services/core/probate/generation/` | agent, gate, body and CLI that run on a generation Sprite |
| `services/core/probate/adapters/` | one adapter per vendor, real and fake |
| `services/core/probate/suite/` | attack fixtures loader and runner |
| `apps/web/` | live-family site |
| `apps/site/` | landing page and docs |
| `packages/faces`, `packages/tokens` | family faces and design tokens shared by both sites |
| `scripts/` | deploy to Sprites, ship, export landing data |
