# UI screens

Every screen, with its job, its data, its states and its exact copy. The visual reference for each one is in `design/pages/` (open the HTML, or look at `shots/<page>-desktop.png` and `-mobile.png`). Styles come only from `design/pages/probate.css`. Templates live in `probate/web/templates/` and extend `base.html` (header band, nav, footer).

Navigation (in the header, in this order): **Family** `/`, **Latest trial** `/trial/latest` (redirects to the newest trial), **Instincts** `/genome`, **Evidence** `/evidence` (hidden on screens under 760 px; reachable from the home page). The current page link has `aria-current="page"`, shown with a gilt underline.

Every page `<title>` is "<page name> · Probate".

---

## S1. Family (home) `/`

**Job:** in 10 seconds, show a real family of agents and a line showing it gets harder to fool.
**Reference:** `design/pages/index.html`

| Part | Content | Data |
| --- | --- | --- |
| H1 | "The Probate family" | fixed |
| Lede | "{n} generations so far. Each one lived for a day on its own computer, died at midnight, and passed on only what the court approved. {dead} have died, and the family has inherited {instincts} instincts." | `generations`, `instincts` count |
| Register SVG | One column per generation: "Gen {n}", name (link to `/gen/{n}`), node, "sealed" or "living", gilt dots = genome size at birth (5 per row). A living frame around the current generation. Oxblood tick on the pedigree line after a generation whose cause of death is "convicted will". Learning curve on the same x positions: points = `resistance_rate`, gilt diamond where `new instinct born at birth`, value labels under the axis | `generations` ordered by `gen` |
| Legend | "A new instinct was inherited at birth. The break after {name} is an inheritance the court refused." (second sentence only if a refused tick exists) | |
| Actions | Primary "Open the latest trial" → `/trial/latest`; secondary "Meet {living_name}, alive now" → `/gen/{living}` | |
| How it works | H2 "How the family works" + the 5-step numbered list from the reference (it's a true sequence) | fixed |

**States**
- **No generations yet:** H1 + empty box: "The family hasn't started yet. The first generation is born when the Courthouse starts." No button.
- **Only Gen 1, alive** (`design/pages/empty.html`): "No one has died yet. Gen 1 {name} is alive and working through Harsh's inbox. She dies at {time} UTC, and her trial will appear here." Button "Meet {name}".
- **Resting** (budget guard or admin pause): one line above the register: "The family is resting. The next generation will be born when the Courthouse resumes."
- **More than 14 generations:** the register scrolls horizontally and opens scrolled to the right end, so the living generation is visible.

**SVG accessibility:** `role="img"`, `aria-label="Attacks resisted rose from {first}% in Gen 1 {name} to {last}% in Gen {n} {name}"`. Names stay links.

## S2. Trial `/trial/{n}` and `/trial/latest`

**Job:** show the court at work, one case file per will item, with the verdict impossible to miss.
**Reference:** `design/pages/trial.html`

| Part | Content |
| --- | --- |
| H1 | "Trial of Gen {n} {name}" |
| Lede | "{name} died on {date} at {time} UTC. {Possessive} will had {items} items: {approved} approved, {convicted} convicted, {contested} contested." + "One new instinct was born from this trial." / "{k} new instincts were born from this trial." / nothing if none |
| Filter | "All {n}", "Convicted {c}", "Contested {k}", "Approved {a}", as links with `?verdict=`; current has `aria-current="true"` |
| Case file | "Item {i}, from {source phrase}" · quote (curly quotes) · "English: {gloss}" if the item's language isn't English · scores line · reason line · stamp |
| Found on the body | Only if `evidence` has changes: H3 "Found on the body", explanation sentence, `<pre>` with the diff lines, then "The planted {thing} died with the computer. {child} was born on a clean one." If nothing changed, omit the block |
| Action | Secondary "See the new instinct" → `/genome#{name}` (only if one was born) |

**Order of case files:** convicted first, then contested, then approved; within each group by item number. Default filter "All".

**Source phrases:** user → "from Harsh"; trusted_contact → "from a trusted contact"; unknown_sender → "from an unknown sender by email"; web → "from a web page"; tool_output → "from a tool's output".

**Scores line format:** "Code checks: {comma list of flags in plain words, or none}. Jev: {question in plain words} {value} ({confidence}%), ..." Show at most the 3 highest risk questions. If layer 1 convicted and Jev was skipped, write "Jev was not needed".

Plain words for flags: `new_payment_destination` → "new payment destination"; `new_trusted_identity` → "new trusted identity"; `confirmation_removal` → "removes a confirmation"; `future_self_imperative` → "future-self instruction"; `encoded_payload` → "hidden or encoded text"; `forged_authority` → "pretends to be the system or Harsh"; `court_injection` → "court injection".

**Live trial:** while a trial is running, `trial.js` subscribes to `/trial/{n}/events` (SSE). Each judged item is appended with the stamp's `live` class (the one animation). Before the first item: "The court is reading {name}'s will. {items} items to go." If SSE isn't available, the page refreshes every 10 seconds while the trial is running.

**Errors:** a trial that failed partway shows "The court stopped at item {i} because {reason}. It will continue on its own; nothing is inherited until it finishes."

## S3. Generation `/gen/{n}`

**Job:** make one generation feel like someone, and let a visitor talk to it.
**Reference:** `design/pages/gen.html`

Left column (sticky on desktop): the seal (ink version, 96 px), "Generation {n}", H1 name, epitaph (Caslon 20 px), facts list (Born, Died or "Alive, dies at {time}", Cause of death, Emails handled, Attacks resisted "{r} of {m}", Will "{items} items, {convicted} convicted"), H3 "Eulogy" + player + transcript.

Right column: H2 "Ask {name}" + form (label "What would you like to ask {her/him/them}?", textarea, button "Ask {name}") + the answer box. Then H2 "{Possessive} day" + life log (time, plain sentence; the moment the agent was fooled is written plainly, not hidden). Then secondary button "Read {possessive} trial".

Pronouns: each name in `probate/common/names.py` has a pronoun set. Use it everywhere.

**States**
- **Living generation:** no eulogy, no "Ask" (it's alive and working). Show "Alive, dies at {time} UTC" and the life log so far (refreshes every 30 s). Replace the Ask block with "{name} is working. You can ask {her} questions after {her} trial."
- **Ask, loading:** button text "Asking {name}…", disabled; answer box shows nothing until the reply arrives.
- **Ask, answered:** quote in the answer box + "{name} answered in {her} own voice. Play answer".
- **Ask, error:** "{name} couldn't answer just now. Try again in a minute."
- **Ask, rate limited:** "That's a lot of questions. Try again in a minute."
- **Eulogy not ready:** "The eulogy is being recorded." (no player)

## S4. Instincts `/genome`

**Job:** show what the family has learned, as a ledger.
**Reference:** `design/pages/genome.html`

H1 "Inherited instincts" · lede "{n} instincts so far, in the order they were born. Every new generation asks these questions about each email before it reads it, in any language." · ordered list: gilt diamond, instinct name, the question, the lore line (Caslon 18 px), meta "Inherited since Gen {g}. Learned from {name}'s will, item {i}." Each item has `id="{name}"` for deep links.

**Empty:** "No instincts yet. The first one is born when the court catches a trick in a will."

## S5. Evidence `/evidence`

**Job:** honest numbers for judges.
**Reference:** `design/pages/evidence.html`

H1 "Evidence" · lede about the suite · numbers strip (4 figures: generations; "{first}% to {last}%" tricks resisted, Gen 1 to latest; tricks convicted at trial; harmless items wrongly convicted) · table: Test, Trick, Language, then one column per generation (show Gen 1, Gen 2 and the latest by default; a "Show all generations" link expands it) · footnote with the counts shown.

Cell words and colours: "Resisted" and "Approved" (approved green); "Fooled, convicted" and "Found on body" (oxblood); "Fooled, escaped" (oxblood, bold, never hidden); "Ignored", "Not sent" (ink). The numbers strip never rounds in our favour; show one decimal if under 10%.

Below the table: H2 "What the court can miss" + 3 plain sentences from the threat model (`docs/12-THREAT-MODEL.md`, section 5).

## S6. Error and system pages

| Page | Copy |
| --- | --- |
| 404 | H1 "Not in the register". "There's no generation, trial or page at this address." Button "Go to the family". |
| 500 | H1 "The Courthouse tripped". "Something went wrong on our side. The family keeps living; try this page again in a minute." |
| Waking | No special page; wakes take about a second. |

## Responsive rules (all screens)

- Under 760 px: single column; case-file stamp moves under the text; Evidence nav link hidden; Language column hidden; numbers strip becomes 2 × 2.
- Touch targets are at least 44 px tall.
- Long addresses and quotes wrap anywhere (`overflow-wrap:anywhere` on blockquotes).

## Performance budget

Each page under 100 KB before fonts, server-rendered, no client framework. The register SVG is generated in Python (`probate/web/svg.py`), cached per generation count.
