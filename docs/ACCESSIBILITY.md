# Accessibility checks

What was checked on the landing page, the docs and the live site, how, and what is left. Written for issue #11.

## PageSpeed and Lighthouse

PageSpeed Insights, mobile, live landing page, Nov 26, 2026: **Accessibility 100, Best Practices 100, SEO 100**, Performance 92, Agentic browsing 2 of 3. Every lost point came from layout shift (0.15): the scrambled "every night." in the hero resized its box on each frame. `components/fx/Scramble.tsx` now draws the scramble over the real text without resizing it, so layout shift is 0 (PR #48).

Lighthouse 13.6 locally after the fix (mobile preset, simulated throttling): Accessibility, Best Practices, SEO and Agentic browsing 100 on the landing page and every docs page checked; Performance 91 to 96 (landing) and 93 to 97 (docs) on phones, 100 on desktop. The phone range is main-thread time, which this machine measures higher than PageSpeed did. To repeat: `npx lighthouse <url> --chrome-flags="--headless=new"` (add `--preset=desktop` for desktop).

The same PR made the docs lighter while loading: glossary words are plain buttons with one shared definition card per page (`components/gloss-layer.tsx`) instead of a pop-up component each, and docs links prefetch on intent instead of on sight (about 20 prefetches on load down to 6).

The docs site also has a page for this: `/docs/accessibility`.

## How to repeat the axe pass

Not part of CI. It needs Node 22+, a system Chrome and axe-core installed anywhere outside the repo.

```sh
# 1. site
NEXT_PUBLIC_SITE_URL=http://127.0.0.1:4747 npm run build -w @probate/site
# 2. live site with a frozen API (never commit the api.ts patch)
python scripts/preview_snapshot.py --out .preview/snapshot
python scripts/preview_patch_api.py apps/web/src/lib/api.ts
npm run build -w @probate/web && git checkout apps/web/src/lib/api.ts
python scripts/preview_assemble.py --dist apps/web/dist --snapshot .preview/snapshot --out .preview/web
# 3. serve both (site with /x -> x.html, web with SPA fallback and a stand-in judge API)
node scripts/a11y_serve.mjs --site apps/site/out --web .preview/web &
# 4. run axe (npm i axe-core in a scratch folder, pass its axe.min.js)
node scripts/a11y_check.mjs --axe /path/to/node_modules/axe-core/axe.min.js --verbose
```

`a11y_check.mjs` drives Chrome over the DevTools protocol at 390x844 (mobile emulation, scale 2) and 1440x900, scrolls each page to the bottom so scroll-driven text is in its final state, and runs axe with the WCAG 2.0/2.1/2.2 A and AA tags plus best-practice rules. It exits non-zero if anything is found and fails loudly if a page rendered a not-found view. Pages: landing `/`, `/docs`, `/docs/journey`, `/docs/for-judges`, `/docs/reference/api`, and on the live site `/`, `/trial/3`, `/gen/3`, `/instincts`, `/evidence`, `/judges` (locked, key refused, unlocked). Both sites are dark only, so there is no light pass.

## Results (violating nodes, mobile / desktop)

| Page | Before | After |
|---|---|---|
| landing `/` | 3 / 3 | 0 / 0 |
| docs `/docs` | 2 / 7 | 1 / 6 |
| docs `/docs/journey` | 2 / 4 | 1 / 3 |
| docs `/docs/for-judges` | 2 / 11 | 1 / 10 |
| docs `/docs/reference/api` | 2 / 6 | 1 / 5 |
| web `/` | 9 / 14 | 0 / 0 |
| web `/trial/3` | 1 / 1 | 0 / 0 |
| web `/gen/3`, `/instincts`, `/evidence` | 0 / 0 | 0 / 0 |
| web `/judges` locked | 3 / n.a. | 0 / 0 |
| web `/judges` refused, unlocked | not measured before | 0 / 0 |
| Total | 67 (without the Judges states) | 28 |

The "before" numbers come from the unmodified main, after fixing the harness (the very first pass accidentally audited a not-found page; the script now refuses to). The Judges states were only reachable once the stand-in judge API existed, so only the locked state has a "before". The landing page also scored 26 extra nodes when measured scrolled to the top, because the pinned statement is deliberately dim until reached; the script now measures at the bottom.

## Fixed

- Landing: the hero docket title was an `h3` straight after the `h1` (heading order); now a paragraph. The Hacksgiving strip sat outside any landmark; it is now an `aside` with a name.
- Live site: generation cards had an `aria-label` that did not contain their visible text (WCAG 2.5.3); the label is gone, the visible text names the button. The hero sat outside `main` (the skip link also skipped it); `main` now wraps hero and page. Case file headings jumped h1 to h4; there is now an `h2` and the sub-headings are `h3`. Links in the locked Judges form were distinguishable by colour only; they are underlined.
- Docs: at 390px the Hacksgiving banner close button overlapped the text. The banner reserves room for the button, uses a smaller line height, and its text flows as one block. The close icon was drawn at half strength; it now uses the secondary text colour. The banner is a named region.
- Pinned statement on phones left a screen of empty space around six lines of text. On phones it is now a normal block that lights up as it scrolls past; from `sm` up it is still pinned.

## Reduced motion

Checked with `Emulation.setEmulatedMedia` (`prefers-reduced-motion: reduce`), scrolling the whole page, then listing running animations (`document.getAnimations()`) and any visible text with an effective opacity below 0.95.

- Landing at 390 and 1440: no running animations, no dimmed text, no scroll progress bar, no pinned sections. Hero text is final, statement is fully lit, number tickers show final values, lineage film shows its end state, spotlight and magnet do nothing.
- Live site: nothing running on any page. Remaining dim text is disabled controls (Ask, Unlock) which are exempt.
- Fixed: the page rise fade (`Page`, hero), the case file open/close height and bar animations, and the generation side sheet still animated under reduced motion (Motion's `reducedMotion="user"` only stops transforms); they are now instant.
- No JavaScript: section headings and the statement used to be in the HTML at opacity 0 or 0.16. A `noscript` rule in the root layout now shows them. The hero headline is in the initial HTML.

## Known gaps

- Remaining axe findings (28 nodes) are all the `region` best-practice rule on fumadocs internals in the docs: the library's "skip to page" link and the table-of-contents column are outside landmarks. Not a WCAG failure and not our markup; left as is.
- The Attack panel result states and the live running-life panel need a real Courthouse and are not covered; nor are the search dialog, the docs sidebar drawer (looked at by eye only), keyboard-only walk-throughs, screen reader testing, or forced-colours mode.
- The product screenshots on the landing page are images of the live site; their small text is not readable on phones. They have alt text.
- axe finds only part of what matters. Contrast of text over the hero glow and the scrubbed statement mid-scroll (words are deliberately dim until reached) is not judged by it.
