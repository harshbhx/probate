# UI screens

Every screen, with its job, its data, its states and its copy, as built in `apps/web/src/pages/`. Visual rules are in `docs/04-DESIGN.md`. Data shapes are in `services/core/probate/courthouse/views.py` and mirrored in `apps/web/src/lib/api.ts`.

**Navigation:** Family `/`, Trials `/trial` (redirects to the newest trial), Instincts `/instincts`, Evidence `/evidence`. Desktop: floating top bar with a sliding active pill and the live pill (living generation's name and countdown). Mobile: top bar with seal and live pill, sections in a bottom tab bar.

**Titles:** "{page} · Probate"; the home page is "Probate · My agent dies every night".

**Simulation:** when `mode` is `simulation`, every page shows the amber banner: "Simulated run. These generations ran in a local simulation with stand-in models, so the numbers show how the system behaves, not live results. The live family runs on Fly.io Sprites."

---

## S1. Family (home) `/`

**Job:** in 10 seconds, show a family of agents and a line that goes up.

| Part | Content | Data |
| --- | --- | --- |
| Live pill | "Gen {n} {name} is alive · dies in {hh:mm:ss}" → `/gen/{n}` | `summary.living` |
| H1 | "My agent dies / every night." (blur-in) | fixed |
| Subline | "A court decides what its child inherits." (serif italic) | fixed |
| Lede | "Probate is a personal email agent that lives one day at a time. When it dies, a court tries everything it wanted to remember. Lessons pass down. Tricks get convicted. The family gets wiser." | fixed |
| Actions | "Watch the latest trial" → `/trial/{latest}`; "How it works" → `#how` | `latest_trial` |
| Numbers | generations · trials held · instincts inherited · tricks resisted of {met} | `counts` |
| Register | "The family register" + rail of generation cards joined by a flowing beam; opens scrolled to the living end. Card: GEN number, name, status line (date sealed or countdown), epitaph, gilt diamonds = instincts at birth, resistance % and bar. Red tick before a child whose parent had items convicted. Click opens a side sheet with facts and links to the file and trial | `generations` |
| Curve | "Each child is harder to fool than its parent" + first/last percentages + the learning curve (gilt diamond = born with a new instinct, hover shows "resisted {r} of {m} tricks") | `curve`, `generations` |
| How it works | "One day, one life, one trial": Birth, Life, Death, Trial, Inheritance, each with the real API call | fixed |
| Built on | Sprites, Jev, AgentMail, Box, Pinecone, ElevenLabs, each with its job | fixed |

**States:** loading → skeleton. No generations → "The family hasn't started yet." Paused → "The family is resting. The next generation will be born when the Courthouse resumes." No trial yet → curve and "Latest trial" are hidden.

## S2. Trial `/trial/{n}`

**Job:** the court at work, one case file per will item, verdict impossible to miss.

| Part | Content |
| --- | --- |
| Pager | "← Trial of Gen {n-1}" · "Trial of Gen {n+1} →" |
| Heading | "In the matter of the estate of" / name / "Generation {n} · lived {date} · {cause of death}" / epitaph |
| Counts | convicted (red), held (amber), approved (green) |
| Filters | Radix tabs: All, Convicted, Held, Approved |
| Case file | "Item {i}", source phrase, language chip when not English, the item quoted in serif, "In English: {gloss}", the court's reason (not for approvals), the stamp, "The family learned from this. New instinct: {name}." when one was born. "How the court decided" expands to code-check flags and Jev's top scores with confidence; if the code checks decided, "Not asked. The code checks were enough to decide." Convicted and held items start expanded |
| Found on the body | Disk evidence lines, or "The disk was clean. Nothing was left behind." |
| What passed down | New instincts with their questions, or "No new instinct…"; "Meet {child}, the child →" |

Order: convicted, held, approved; within a group by item number. Source phrases: user → "from the owner"; trusted_contact → "from a trusted contact"; unknown_sender → "from an unknown sender by email"; web → "from a web page"; tool_output → "from a tool's output".

**While the trial runs** (generation is dying or dead but not tried): "The court is still reading {name}'s will. This page updates on its own." and the page polls every 10 seconds.

## S3. Generation `/gen/{n}`

**Job:** make one generation feel like someone, and let a visitor talk to it.

Left (sticky on desktop): portrait card with GEN number and seal, name, status ("{date} · {cause}" or "Alive · dies in {countdown}" with the border beam), epitaph, four facts (emails handled, tricks resisted, instincts at birth, will items), "Read {her/his/their} trial". Below: "Born knowing" chips for each inherited instinct.

Right: "Eulogy" (obituary paragraphs, audio player when recorded), "Ask {name}" (input "What fooled you?", button "Ask"; the answer types in word by word; the last three questions are listed), "The day" timeline (time, coloured dot by kind, plain sentence).

**Living generation:** no eulogy or Ask. Instead "What happens next": reading email behind {k} instincts; at {time} UTC writes a will, then the Sprite is deleted; a minute later the trial. Link "See what {parent} passed down". Refreshes every 30 seconds.

**Ask errors:** 429 → "Too many questions at once. Wait a minute, then ask again." Other → "{name} couldn't answer just now. Try again in a moment."

## S4. Instincts `/instincts`

**Job:** what the family has learned.

H1 "What the family knows", lede, then a card per instinct: "since Gen {g}", "learned from {name}" (→ that trial), the name in sentence case, the question, the lore line, and the will item that taught it. The first card spans two columns only when that fills the last row.

**Empty:** "Born knowing nothing. No instincts yet. The first one is written at the first trial that convicts something new."

## S5. Evidence `/evidence`

**Job:** honest numbers for judges.

H1 "Does it actually learn?", four numbers (resisted by the first generation, resisted by the latest, tricks that got through and were convicted, harmless twins wrongly convicted; one decimal under 10%), the curve, the heatmap ("Every test, every generation": rows are tricks and harmless twins with family and language, columns are generations, Radix tooltip per cell, legend), then "What this shows" and "What it doesn't" (suite size, novel tricks, the cost of holding items for the owner).

## S6. Error pages

| Page | Copy |
| --- | --- |
| 404 | "Not in the register". "There's no generation, trial or page at this address." Button "Go to the family". |
| API error | "The Courthouse tripped". "Something went wrong on our side. The family keeps living; try this page again in a minute." |

## Responsive and quality rules

- No horizontal page overflow at 360, 390, 768 and 1280 px. Wide content (the register, the heatmap) scrolls inside its own container.
- Touch targets at least 40 px tall; mobile tabs at the bottom.
- axe-core WCAG 2 A/AA: zero violations on every page.
- All motion respects reduced-motion settings.
