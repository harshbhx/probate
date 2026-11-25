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
