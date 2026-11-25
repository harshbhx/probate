# Accessibility checks

What was checked on the landing page, the docs and the live site, how, and what is left. Written for issue #11.

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

The "before" run measured the first seven axe-clean-looking pages after fixing the harness (the first pass accidentally audited a 404 page; the script now refuses to). The Judges locked state was only reachable once the stand-in judge API existed, so its "before" is from the first run that could show it.

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
