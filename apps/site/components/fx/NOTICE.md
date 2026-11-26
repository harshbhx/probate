# Patterns used in `components/fx` and `components/landing`

Written from the published behaviour of these MIT-licensed libraries. No library code was installed or copied
wholesale; each file is a small re-implementation with `motion` and Tailwind and says which pattern it follows.

| File | Pattern | Library |
| --- | --- | --- |
| `Scramble.tsx` | Decrypted Text | React Bits (reactbits.dev, by David Haz) |
| `Spotlight.tsx` | Spotlight | Aceternity UI (ui.aceternity.com, by Manu Arora) |
| `Reveal.tsx` | Blur Fade | Magic UI (magicui.design) |
| `CountUp.tsx` | Number Ticker | Magic UI |
| `../landing/docket.tsx` | Border-lit card with a live-looking record | Aceternity UI "Glare Card" and Magic UI "Shine Border" (as a still hairline) |
| `../landing/life-story.tsx` | Sticky scroll reveal | Aceternity UI "Sticky Scroll Reveal" |
| `../../app/(home)/page.tsx` (Tile, Evidence) | Bento grid of product tiles | Aceternity UI "Bento Grid", shadcn/ui card tokens |

Also surveyed and not used: React Bits Aurora, Particles and Splash Cursor (ambient, looping), Aceternity Lamp and
Background Beams (loud), Magic UI Marquee and Animated Beam on the landing (looping, against docs/04-DESIGN.md).

## Round 2 additions

| File | Pattern | Library |
| --- | --- | --- |
| `ScrollProgress.tsx` | Scroll Progress | Magic UI |
| `SpotlightCard.tsx` | Spotlight Card, Card Hover Effect | React Bits, Aceternity UI |
| `TextReveal.tsx` | Text Reveal | Magic UI |
| `Magnet.tsx` | Magnet | React Bits |
| `BigWord.tsx` | Edge-to-edge wordmark | Our own |
| `../landing/verdict-stack.tsx` | Scroll Stack | React Bits |
| `../landing/quotes.tsx` | Quote cards on spotlight cards | Aceternity UI "Card Hover Effect" |

The Scroll Stack, Text Reveal and Magnet implementations follow the same patterns already adapted in the Tarang FM and Ratchet projects by the same author.

## Round 3 (v8): a component for every product

Each one plays once, or only answers the reader, and passes the unslop rule in `docs/04-DESIGN.md`: motion that explains what just happened, then stillness.

| File | Pattern | Library |
| --- | --- | --- |
| `Terminal.tsx` | Terminal with a typing animation, played once | Magic UI |
| `../landing/court-beams.tsx` | Animated Beam, drawn once and then still | Magic UI |
| `../landing/page-verdicts.tsx` | Animated List, cases called once | Magic UI |
| `FileTree.tsx` | File Tree, on `<details>` with no JavaScript | Magic UI |
| `Tabs.tsx` | Tabs with roving focus | shadcn/ui (Radix Tabs semantics) |
| `InView.tsx` | The in-view trigger behind all three, CSS only | Our own, after Magic UI Blur Fade |

The docs use Fumadocs UI's own components (Cards, Tabs, Files, TypeTable, Accordions, Steps) and reuse the three above.
