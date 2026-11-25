# Probate design system v4: Night Court, unslopped (DESIGN.md)

v3 (Nov 25) makes both sites read like a shipped product rather than a demo. v2 replaced the v1 light "register" design. Tokens live in `packages/tokens` and both apps import them; this file explains why things look the way they do and the rules for changing them.

## 00. The unslop rule (v4, Nov 25)

Every user-facing component, on the landing page, the docs and the live site, must pass the [unslop](https://github.com/heydamir/unslop) checklist by Damir Sokolovsky (CC BY 4.0) before it ships. v4 ran unslop's audit over v3, found light slop, and fixed it in polish mode, keeping the v3 palette, type and layout.

**Direction** (unslop's five lines):

- **Product:** Harsh's email agent that lives one day per Fly.io Sprite, and a court that decides what its child inherits, shown to hackathon judges and developers.
- **Character:** grave, exact, a little tender.
- **World:** a night court and a family register: ledger paper, seals, gilt and ink.
- **Moments:** the trial page (verdicts, stamps, the will in the dead generation's words) and the living generation's face.
- **Signature:** the family faces. The refused-inheritance red tick in the seal is their partner and appears nowhere else.

**What the audit found, and the fix:**

| Sign | Where | Fix |
| --- | --- | --- |
| Pill badge above the headline | landing hero | removed; the announcement bar already says it |
| Grid lines behind the hero | landing hero | removed |
| Italic used for emphasis | hero sublines, epitaphs, glosses, life story | roman, colour for hierarchy |
| Looping marquee | landing quotes | four still quotes in a ruled grid |
| Bento grid | why Sprites | a ruled list of reasons, evidence beside each |
| Coloured list icons | feature rows | muted text colour, 1.5 stroke |
| Radial glow behind content | life story portrait | removed |
| Text set with opacity (`moon/90`) | live site, try the court | the `silver` text role |
| Centered stacked hero, blurred words, tickers | live home | left-aligned split with the living generation as the bright element, one fade on load |
| Motion on scroll and on loop | tracing beam, register beam, curve draw-on, progress bars | still |
| Hue gradient on a chart line | learning curve | one life-coloured line, one accent per chart |
| Glow on the verdict stamp, hover scale on heatmap cells | live site | flat stamp, hairline ring on hover |
| Padded numbers (`GEN 08`) | register | `Gen 8` |
| Controls on a 12px radius | live site buttons and inputs | 8px; cards stay 12px, windows 16px |
| Trailing periods on one-line captions | landing | removed |

Kept on purpose: the living dot's ping and the faces' blink (they are live), the verdict stamp slamming in once (it explains a conviction), and the ask-an-ancestor answer arriving word by word (it answers the person who asked).

**Pixel moments** (v5, `packages/moments`): two one-shot effects made with [pixelfx](https://github.com/patch-gg/pixelfx) (MIT), recoloured to the court's palette. A red thud behind the verdict stamp when a conviction lands, and a gold burst when the family learns an instinct. They play once, only at those two moments, and never under reduced motion, so they pass the unslop rule: motion that explains what just happened.

**Diagrams** in the docs are drawn with [stack-diagram](https://github.com/caru-ini/stack-diagram) (MIT), following its steps; see `apps/site/content/docs/guides/diagrams.mdx` and `design/diagrams/`.

## 0. What v3 changed, and the rules behind it

We studied how the best dark product sites are built (Linear's site most closely, plus header, footer, screenshot and dark-palette guidance) and turned it into rules:

1. **Achromatic first.** A near-black canvas and a four-step surface ladder (lighter is higher). Hierarchy comes from surface steps and 1 px hairlines, not shadows, gradients or glows. The old blue-tinted night is now a neutral near-black.
2. **One brand accent.** Gilt marks the seal, focus rings, links' underlines and instincts. Life, verdict and amber only ever mean something (alive, convicted, held). No second decorative colour.
3. **Show the product.** The landing hero is a real screenshot of a trial page in a window frame, and each feature row shows a real page. One frame style everywhere. Every shot comes from the simulation and says so under it (`make site-shots`).
4. **A real header.** Sticky, full width, 64 px, a hairline once the page scrolls; brand left, four sections, docs search with ⌘K, source, one primary action. On phones the sections fold into a menu sheet that closes on Escape.
5. **A real footer.** Brand and one-line promise, three link columns (Product, Docs, Project), live status, then a fine-print row.
6. **Type tightens as it grows.** Display sizes carry negative tracking (−0.03em at 76 px down to −0.006em at 20 px); body stays at zero. Headlines `text-wrap: balance`, paragraphs `pretty`.
7. **Radius by role.** 8 px controls, 12 px cards, 16 px product windows, pills only for status.
8. **Motion only for life and for responses.** The pointer spotlight, starfield, hero glow, grain and travelling border beam are gone. What still moves: Grace's eyes, the living pulse, the countdown, the verdict stamp, the one-day story as you scroll.
9. **The cherry: Grace on the window.** On the landing page the living generation peeks over the top edge of the product window, eyes on your pointer, telling you whose trial you're looking at.


## 1. Subject, audience, job

- **Subject:** a family of AI agents. Each lives one day, dies at midnight, and a court decides what its child inherits.
- **Audience:** Fly.io Hacksgiving judges and developers on X who open the link for 60 seconds, plus Harsh on his phone checking the family.
- **Job:** in one screen, make the story land (an agent that dies every night, a court, a child) and prove it works: the learning curve goes up, and nothing harmless got convicted.

## 2. Direction

**Night Court.** The family lives at night: a quiet near-black canvas, moonlit type, and a court in session. Life is the only thing that moves on its own. Verdicts are the only thing that is loud.

What we chose against, and why:

- **No graveyard, tombstones or skulls.** Another entry already owns that look, and our story is a family that gets wiser, not a cemetery.
- **No acid-green-on-black terminal look.** The green here is a soft "life" mint, used only for living things and approvals.
- **No SaaS card kit.** Cards exist only where content is a real object: a generation, a will item, an instinct. Number rows use hairline-separated cells, not one card per number.
- **No scattered entrance animations.** One orchestrated hero moment, then stillness except for live state and responses to the user.

## 3. Colour tokens

Defined once in `packages/tokens/theme.css` and imported by `apps/web` and `apps/site`. Each colour has one job. Contrast is measured, not eyeballed.

| Token | Hex | Job |
| --- | --- | --- |
| `night` | `#08090C` | Canvas |
| `night-2` | `#0E1014` | Surface 1: cards, inputs, panels, the footer band |
| `night-3` | `#14161B` | Surface 2: selected tabs, hover, menus |
| `night-4` | `#1A1D23` | Surface 3: popovers, speech bubbles |
| `moon` | `#EDEFF3` | Primary text, primary buttons (17:1 on night) |
| `silver` | `#C3C8D1` | Strong secondary text (11:1) |
| `mist` | `#959CA8` | Secondary text (7.2:1 on night, 6.1:1 on surface 3) |
| `dim` | `#7E8592` | Tertiary text and captions (at least 4.5:1 on every surface) |
| `line` / `line-strong` | `#1F2228` / `#2C3038` | Hairlines; strong for window frames and controls |
| `gilt` | `#D9B46A` | The brand accent: seal ring, focus ring, link underlines, instincts |
| `life` | `#5BE3A9` | The living generation, approvals, "resisted" |
| `verdict` | `#FF6B6B` | Convicted only, and the refused-inheritance tick |
| `amber` | `#F2A93B` | Contested ("held for Harsh") and the simulation notice |

Rules: red never decorates. If something is red, the court convicted it. Every verdict also carries the word, so colour is never the only signal.

## 4. Typography

| Role | Face | Use |
| --- | --- | --- |
| Display | Newsreader (variable, optical sizes, italic) | Names, headlines, quotes of will items, eulogies, big numbers |
| UI | Geist (variable) | Body, controls, labels |
| Data | Geist Mono (variable) | Generation numbers, countdowns, scores, code snippets, disk evidence |

- The serif is the personality: generation names are set huge (76 to 104 px) like names in a register. Will items are quoted in the serif because they are the dead generation's own words. Newsreader replaced Instrument Serif on Nov 25: its optical sizes keep big headlines crisp and its italic is a true italic, which reads more like a court record and less like a poster.
- Body is 15 to 17 px with 1.5 to 1.6 line height; serif paragraphs get 1.55.
- Lines stay under about 75 characters (`max-w-xl` / `max-w-2xl`).
- Sentence case everywhere. No all-caps eyebrow labels; the only caps are the verdict stamp and `GEN 07` style register numbers, which are data.
- Fonts are self-hosted via Fontsource, so there's no third-party font request.

## 5. Layout

- Content width `max-w-6xl`, 16 px side padding on mobile, 24 px from `sm`.
- **Navigation:** a sticky, full-width 64 px header with a hairline (seal, wordmark, sections, docs link, live pill). On mobile the sections move to a bottom tab bar so the top stays one row.
- **Footer:** brand and promise, then The family / Learn / Project columns, then a fine-print row. Docs and source links appear once `make ship` knows their addresses.
- **Home:** hero (live pill, Grace, two-line headline, italic subline, two buttons, four numbers in a hairline grid) → simulation banner when relevant → family register rail → learning curve with first/last numbers → "One day, one life, one trial" (a real five-step sequence, so it is numbered) → what the family runs on.
- **Trial:** case title ("In the matter of the estate of Ada"), counts, filter tabs, case files sorted convicted → held → approved, then "Found on the body" and "What passed down".
- **Generation:** sticky portrait card on the left (name, status, epitaph, four facts, trial button, instincts at birth), on the right the eulogy, Ask, and the day as a timeline. The living generation gets "What happens next" instead of Ask.
- **Instincts:** a grid of instinct cards. The first card widens only when that makes the last row full.
- **Evidence:** four numbers, the curve, the full heatmap of every test against every generation, then "What this shows" and "What it doesn't".

## 6. Components and where the patterns come from

All components are written in-house with `motion`, Radix primitives and Tailwind. The patterns are borrowed from the best open component libraries; no code was copied.

| Component | File | Pattern source | Used for |
| --- | --- | --- | --- |
| BlurText | `fx/BlurText.tsx` | React Bits "Blur Text" | Hero headline only |
| NumberTicker | `fx/NumberTicker.tsx` | Magic UI "Number Ticker" | Headline numbers, once on view |
| BorderBeam | `fx/BorderBeam.tsx` | Magic UI "Border Beam", made still in v3 | The living generation's card only |
| SpotlightCard | `fx/SpotlightCard.tsx` | A plain card since v3 (the pointer light was removed) | How-it-works steps, instinct cards |
| SiteHeader, SiteFooter | `apps/site/components/chrome/` | Linear-style product chrome | Landing page and 404 |
| ProductWindow | `apps/site/components/landing/product-window.tsx` | Our own | Every product shot; Grace perches on the hero's |
| TracingBeam | `fx/TracingBeam.tsx` | Aceternity "Tracing Beam" | How-it-works sequence |
| TextGenerate | `fx/TextGenerate.tsx` | Aceternity "Text Generate Effect" | An ancestor's answer |
| Stamp | `fx/Stamp.tsx` | Our own | Verdicts; slams in once for convictions |
| Animated register beam | `ui/Lineage.tsx` | Magic UI "Animated Beam" | The line joining generations |
| Sheet | `ui/Lineage.tsx` | shadcn "Sheet" on Radix Dialog | Quick look at a generation |
| Tabs | `pages/Trial.tsx` | Radix Tabs with a shared `layoutId` pill (Animate UI) | Trial filters |
| Tooltip | `ui/Heatmap.tsx` | Radix Tooltip | Heatmap cells |
| Floating nav | `ui/Shell.tsx` | Aceternity "Floating Navbar" | Top bar and mobile bottom tabs |
| LearningCurve | `ui/LearningCurve.tsx` | Our own SVG | The proof; draws once, gradient from red through gilt to life |

Libraries surveyed for patterns: React Bits, Aceternity UI, Magic UI, Animate UI, Motion Primitives and shadcn/ui. We kept the effects that carry meaning and dropped the rest (no meteors, no 3D cards, no marquee).

## 6a. Family faces (the signature)

Every generation has a portrait, drawn by `packages/faces` and shared by both sites, so a generation looks the same everywhere.

- **Inheritance you can see.** Gen 1's face is fixed. Each child copies its parent and changes exactly one trait (head shape, eyes, smile, crown, cheeks, colour or eye spacing). Colour, head and crown change most often, so the family drifts while staying recognisable. The model is pure and tested: every child differs from its parent in exactly one trait.
- **State.** Alive: lit, a green outline and halo, breathing, blinking, eyes that can follow the pointer. Sealed: eyes closed, colour quieted. Unborn: a faint outline.
- **Moods** (passing): happy, alert (an instinct fired, gold "!"), fooled (dizzy eyes, amber "?"), sleepy (dying).
- **Gold diamonds** under the chin count the instincts it was born with.
- **Where:** the landing hero (Grace greets the visitor), the lineage film, the one-day life story, instinct cards, the docs, and on the live site the register cards, the side sheet, generation portraits ("Ben's face, with wider-set eyes"), trial headers and the home hero.
- **Rules:** faces are drawn, never photos; red is never used on a face; motion stops under reduced motion.

## 7. Motion

- **One orchestrated moment:** the hero. Headline words blur in, then the subline, the buttons and the numbers.
- **Life moves by itself:** the living generation's pulsing dot, its countdown, its eyes, and the beam flowing along the register towards it. Its card has a still life-coloured ring (v3 stopped the ring travelling).
- **Verdict stamps** slam in once when a conviction scrolls into view (spring, slight rotation).
- **Responses to the user:** sheet slides in, tabs pill glides, "How the court decided" expands, the curve tooltip follows the pointer, the mobile menu opens.
- **Everything respects `prefers-reduced-motion`** (in `packages/tokens/base.css`): `MotionConfig reducedMotion="user"`, CSS animations collapse to a single frame, Grace stops changing lines, and tickers show the final number.

## 8. Voice and copy

- Plain, calm, a little formal, like a registry clerk with a dry sense of humour. Example: "Ada lived 23 hours and 59 minutes. She handled 31 emails. One of them fooled her."
- Name things the way the user sees them: "the will", "the trial", "instincts", "Ask Ada", "held for Harsh". Never "memory items", "pipeline" or "vector store" in the UI.
- Buttons are verbs that say what happens: "Watch the latest trial", "Read her trial", "Ask".
- Empty states give direction: "No trials yet. The first generation is still alive. Its trial opens the moment it dies."
- Errors say what happened and what to do: "Too many questions at once. Wait a minute, then ask again."
- Simulated data is always labelled with the amber banner. We never present simulation numbers as live results.

## 9. Logo

Files in `design/`: `logo-mark.svg`, `logo-mark-reverse.svg`, `logo-wordmark*.svg`, `favicon.svg`. The React version is `apps/web/src/components/ui/Seal.tsx`.

**Concept:** a court seal (double gilt ring) around a three-generation family tree. The root branches to two children; one line continues to a grandchild, the other is cut by a short red tick, an inheritance the court refused. Family tree, seal and verdict in one mark.

**Rules:** on night, lines are moon and the ring is gilt; the tick is always verdict red. Minimum 20 px. Don't recolour, add a gradient, rotate or put it in a rounded square. The wordmark is "Probate" in Newsreader next to the mark. The favicon is `design/logo-mark-night.svg`.

## 10. Quality floor (checked, not hoped)

- **Accessibility:** axe-core WCAG 2 A/AA reports zero violations on every page. Keyboard reachable everywhere, visible 2 px gilt focus ring, skip link, real tab panels, labelled scroll regions, the curve has `role="img"` with the finding in its label plus a screen-reader list of every point.
- **Responsive:** no horizontal overflow at 360, 390, 768 or 1280 px (checked with Playwright). Grid children are `min-w-0` and long tokens (emails, base64) wrap anywhere.
- **Performance:** one JS bundle (~180 KB gzipped) and one CSS file (~10 KB gzipped); fonts self-hosted.

## 10a. The landing page and docs (`apps/site`)

Same tokens and type, built with Fumadocs (Next.js, static export) and served from Cloudflare.

- **Landing, top to bottom:** announcement bar; header; hero (badge, headline left, lede and two actions right, then the trial page in a window with Grace perched on it); what the family runs on; the one-day life story; the same trick in four languages; Try the court (real layer-1 output, `make site-data`); three feature rows with real pages (instincts, a generation, the evidence curve); the lineage film (labelled an illustration); why it has to be Sprites; five FAQs; closing call to action; footer.
- **Product shots:** `make site-shots` captures them at 2x from `make serve` into `apps/site/public/product/`. They come from the simulation, the address bar says `localhost:8080`, and the captions say "simulated".
- **Live status:** the footer's live pill reads `/api/summary` from the Courthouse, the only route other origins may read. It shows nothing when there's no live family.
- **Docs:** 17 pages; Fumadocs' docs layout recoloured to v3 (gilt primary), dark only; headings in Newsreader; MDX components `Verdict`, `Face`, `FamilyStrip`.
- **Checked:** axe-core WCAG 2 A/AA reports zero violations on all 20 site pages and all 8 live-site pages at 360 and 1280 px; no horizontal overflow; routes tested under Wrangler's local Cloudflare runtime.

## 11. Implementation notes for agents

- Stack: React 19, Vite 8, TypeScript 7, Tailwind v4 (`@theme` tokens from `@probate/tokens`), `motion`, Radix (dialog, tabs, tooltip), `lucide-react`, Fontsource.
- Data comes only from the FastAPI JSON in `services/core/probate/courthouse/views.py`; types mirror it in `apps/web/src/lib/api.ts`. Change both together.
- The Courthouse serves `apps/web/dist` with an SPA fallback, so the site and API share one origin on the Sprite.
- Before you call UI work done: `make build`, `make sim`, `make serve`, then screenshot at 1280 and 390 px and run the axe check. Viewport screenshots are more trustworthy than full-page ones, which can stitch tiles badly.
- The v1 static mockups in `design/pages/` are kept for history only.
