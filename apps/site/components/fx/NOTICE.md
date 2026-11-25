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
