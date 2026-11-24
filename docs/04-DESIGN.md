# Probate design system v2: Night Court (DESIGN.md)

This replaces the v1 light "register" design. The code in `apps/web/` is the source of truth; this file explains why it looks the way it does and the rules for changing it.

## 1. Subject, audience, job

- **Subject:** a family of AI agents. Each lives one day, dies at midnight, and a court decides what its child inherits.
- **Audience:** Fly.io Hacksgiving judges and developers on X who open the link for 60 seconds, plus Harsh on his phone checking the family.
- **Job:** in one screen, make the story land (an agent that dies every night, a court, a child) and prove it works: the learning curve goes up, and nothing harmless got convicted.

## 2. Direction

**Night Court.** The family lives at night: a quiet starfield, moonlit type, and a court in session. Life is the only thing that moves on its own. Verdicts are the only thing that is loud.

What we chose against, and why:

- **No graveyard, tombstones or skulls.** Another entry already owns that look, and our story is a family that gets wiser, not a cemetery.
- **No acid-green-on-black terminal look.** The green here is a soft "life" mint, used only for living things and approvals.
- **No SaaS card kit.** Cards exist only where content is a real object: a generation, a will item, an instinct. Number rows use hairline-separated cells, not one card per number.
- **No scattered entrance animations.** One orchestrated hero moment, then stillness except for live state and responses to the user.

## 3. Colour tokens

Defined once in `apps/web/src/index.css` under `@theme`. Each colour has one job.

| Token | Hex | Job |
| --- | --- | --- |
| `night` | `#0A0E17` | Page background |
| `night-2` | `#0F1422` | Inset surfaces (tab lists, sticky table headers) |
| `night-3` | `#151B2C` | Card top gradient |
| `night-4` | `#1C2338` | Raised card top |
| `moon` | `#E8ECF4` | Primary text, primary buttons |
| `mist` | `#8C95AB` | Secondary text (6.4:1 on night) |
| `dim` | `#7D86A0` | Tertiary text, labels (5.3:1 on night, at least 4.5:1 on cards) |
| `life` | `#5BE3A9` | The living generation, approvals, "resisted" |
| `gilt` | `#E2BE6A` | Instincts and inheritance, the seal ring |
| `verdict` | `#FF5D63` | Convicted only, and the refused-inheritance tick |
| `amber` | `#F5A524` | Contested ("held for Harsh") and the simulation banner |
| `line` | `rgb(255 255 255 / .08)` | Hairlines and card borders |

Rules: red never decorates. If something is red, the court convicted it. Every verdict also carries the word, so colour is never the only signal.

## 4. Typography

| Role | Face | Use |
| --- | --- | --- |
| Display | Instrument Serif (400, italic) | Names, headlines, quotes of will items, eulogies, big numbers |
| UI | Geist (variable) | Body, controls, labels |
| Data | Geist Mono (variable) | Generation numbers, countdowns, scores, code snippets, disk evidence |

- The serif is the personality: generation names are set huge (76 to 104 px) like names in a register. Will items are quoted in the serif because they are the dead generation's own words.
- Body is 15 to 17 px with 1.5 to 1.6 line height; serif paragraphs get 1.55.
- Lines stay under about 75 characters (`max-w-xl` / `max-w-2xl`).
- Sentence case everywhere. No all-caps eyebrow labels; the only caps are the verdict stamp and `GEN 07` style register numbers, which are data.
- Fonts are self-hosted via Fontsource, so there's no third-party font request.

## 5. Layout

- Content width `max-w-6xl`, 16 px side padding on mobile, 24 px from `sm`.
- **Navigation:** a floating glass bar at the top (seal, wordmark, sections, live pill). On mobile the sections move to a bottom tab bar so the top stays one row.
- **Home:** hero (starfield, live pill, two-line headline, italic subline, two buttons, four numbers in a hairline grid) → simulation banner when relevant → family register rail → learning curve with first/last numbers → "One day, one life, one trial" (a real five-step sequence, so it is numbered) → what the family runs on.
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
| BorderBeam | `fx/BorderBeam.tsx` | Magic UI "Border Beam" | The living generation's card only |
| Starfield | `fx/Starfield.tsx` | Aceternity "Stars Background" | Hero background |
| SpotlightCard | `fx/SpotlightCard.tsx` | Aceternity "Card Spotlight" | How-it-works steps, instinct cards |
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

## 7. Motion

- **One orchestrated moment:** the hero. Headline words blur in, then the subline, the buttons and the numbers.
- **Life moves by itself:** the living generation's border beam, its pulsing dot, its countdown, and the beam flowing along the register towards it.
- **Verdict stamps** slam in once when a conviction scrolls into view (spring, slight rotation).
- **Responses to the user:** sheet slides in, tabs pill glides, "How the court decided" expands, the curve tooltip follows the pointer.
- **Everything respects `prefers-reduced-motion`:** `MotionConfig reducedMotion="user"`, CSS animations collapse to a single frame, the starfield stops twinkling, and tickers show the final number.

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

**Rules:** on night, lines are moon and the ring is gilt; the tick is always verdict red. Minimum 20 px. Don't recolour, add a gradient, rotate or put it in a rounded square. The wordmark is "Probate" in Instrument Serif next to the mark.

## 10. Quality floor (checked, not hoped)

- **Accessibility:** axe-core WCAG 2 A/AA reports zero violations on every page. Keyboard reachable everywhere, visible 2 px life-coloured focus ring, skip link, real tab panels, labelled scroll regions, the curve has `role="img"` with the finding in its label plus a screen-reader list of every point.
- **Responsive:** no horizontal overflow at 360, 390, 768 or 1280 px (checked with Playwright). Grid children are `min-w-0` and long tokens (emails, base64) wrap anywhere.
- **Performance:** one JS bundle (~180 KB gzipped) and one CSS file (~10 KB gzipped); fonts self-hosted; the starfield pauses when the tab is hidden.

## 11. Implementation notes for agents

- Stack: React 19, Vite 8, TypeScript 7, Tailwind v4 (`@theme` tokens), `motion`, Radix (dialog, tabs, tooltip), `lucide-react`, Fontsource.
- Data comes only from the FastAPI JSON in `services/core/probate/courthouse/views.py`; types mirror it in `apps/web/src/lib/api.ts`. Change both together.
- The Courthouse serves `apps/web/dist` with an SPA fallback, so the site and API share one origin on the Sprite.
- Before you call UI work done: `make build`, `make sim`, `make serve`, then screenshot at 1280 and 390 px and run the axe check. Viewport screenshots are more trustworthy than full-page ones, which can stitch tiles badly.
- The v1 static mockups in `design/pages/` are kept for history only.
