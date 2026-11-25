# Accessibility

[![PageSpeed accessibility 100](https://img.shields.io/badge/PageSpeed_accessibility-100-5be3a9?style=flat-square)](#scores-at-a-glance)
[![Best practices 100](https://img.shields.io/badge/best_practices-100-5be3a9?style=flat-square)](#scores-at-a-glance)
[![SEO 100](https://img.shields.io/badge/SEO-100-5be3a9?style=flat-square)](#scores-at-a-glance)
[![axe: 0 WCAG A/AA issues](https://img.shields.io/badge/axe-0_WCAG_A%2FAA_issues-5be3a9?style=flat-square)](#what-axe-found)
[![Report a barrier](https://img.shields.io/badge/report_a_barrier-issue_form-d9b46a?style=flat-square)](https://github.com/harshbhx/probate/issues/new?template=accessibility.yml)

Probate is about an agent that can't be fooled into acting for the wrong person. Its sites should work for every person: on a phone, with a keyboard, with motion turned off, or with no JavaScript at all. This page says what we aim for, what we've measured, what isn't tested yet, and how to tell us when something gets in your way.

> [!TIP]
> **Something hard to use?** [Report a barrier](https://github.com/harshbhx/probate/issues/new?template=accessibility.yml). No account details or screenshots of private mail needed: say which page, what you were trying to do, and what got in the way.

## What this covers

| Site | Where | What it is |
| --- | --- | --- |
| Landing page and docs | `apps/site` | The project page, `/links`, and every docs page |
| Live family | `apps/web` | The register, trials, generations, instincts, evidence and the judges page |

## Our priorities

1. **Everyone can read it.** WCAG 2.2 AA is the bar: contrast, headings in order, landmarks, alt text, and links that are clear without colour.
2. **Everyone can use it.** Every control works with a keyboard and has a visible focus ring. Nothing needs a mouse, a hover or a gesture.
3. **Motion is optional.** With reduced motion on, nothing moves: headlines are final, counters show their end values, and the scroll film shows its last frame.
4. **Content comes first.** Every heading and paragraph is in the page's HTML, so the sites read without JavaScript, in reader modes, and for AI agents (the docs are also served as plain text at `/llms.txt`).
5. **Plain words.** Hard words are underlined the first time they appear on a docs page; hover, focus or tap one to see what it means.

## Scores at a glance

[PageSpeed Insights](https://pagespeed.web.dev/), mobile, on the live landing page, Nov 26, 2026:

| Accessibility | Best Practices | SEO | Performance | Agentic browsing |
| :---: | :---: | :---: | :---: | :---: |
| **100** | **100** | **100** | 92, fixed | 2 of 3, fixed |

> [!NOTE]
> Every point lost came from one thing: the animated "every night." in the headline changed width on every frame, so the text around it moved (layout shift 0.15). It now sits over the real text without resizing it, and layout shift is 0. On our own machine, Lighthouse 13.6 then gives 100 for Accessibility, Best Practices, SEO and Agentic browsing on the landing page and every docs page we ran, and 100 in every category on desktop. We'll update this table after the next PageSpeed run on the live site.

## What axe found

[axe](https://github.com/dequelabs/axe-core) tests a page against every WCAG rule a program can check.

| Pass | Pages | Widths | WCAG 2.0, 2.1, 2.2 A and AA issues |
| --- | --- | --- | :---: |
| Landing page and docs, every page | 50 | 390 and 1280 px | **0** |
| Live family: home, trial, generation, instincts, evidence, judges (locked, refused, unlocked) | 8 views | 390 and 1440 px | **0** |

Also checked on every landing and docs page: nothing scrolls sideways on a phone, and none of the 52 links between pages is broken.

With axe's extra best-practice rules turned on, 28 notes remain, all from one rule (`region`) on two parts of the docs framework we don't write: its "skip to page" link and the table of contents sit outside a landmark. They aren't WCAG failures.

## Supported environments

| | Tested | Expected to work |
| --- | --- | --- |
| Browsers | Chromium (Chrome, Edge), desktop and Android emulation | Current Firefox and Safari |
| Screens | 390 px phone and 1280 to 1440 px desktop | 320 px and up; zoom to 200% |
| Input | Mouse, keyboard (glossary, menus, forms), touch (emulated) | Switch and voice control, through standard buttons and links |
| Settings | Reduced motion; JavaScript off | Forced colours (not yet tested) |
| Theme | Dark (both sites have one theme) | |

## Known barriers

| Barrier | Where | Status |
| --- | --- | --- |
| Not yet tested with a screen reader (VoiceOver, NVDA, TalkBack) | Both sites | Planned |
| Forced-colours (high contrast) mode not checked | Both sites | Planned |
| Small text inside the product screenshots can't be read on phones | Landing page | Each has alt text describing it |
| Text over the hero glow and words dim on purpose until you scroll to them aren't judged by axe | Landing page | Checked by eye only |
| The attack panel's results and the running-life panel need a real Courthouse to test | Live family | Checked after the real run |
| Keyboard-only walk through the search dialog and the docs menu on phones | Docs | Looked at by eye only |

## Report a barrier

1. Open the [accessibility issue form](https://github.com/harshbhx/probate/issues/new?template=accessibility.yml). It asks for the page, what you were doing, what got in the way, and your setup (browser, device, any assistive technology).
2. We reply on the issue, label it `accessibility`, and treat a barrier that stops someone finishing a task the same as a broken feature.
3. If the problem also exposes something private or lets someone act for another person, use [private vulnerability reporting](https://github.com/harshbhx/probate/security/advisories/new) instead. See [`SECURITY.md`](../SECURITY.md).

Prefer not to use GitHub? Email harshbhx@gmail.com with "Accessibility" in the subject.

## For contributors

Before a pull request that changes what people see:

- [ ] Build the site and run axe on the pages you changed, at 390 and 1280 px (see below). No new WCAG A or AA issues.
- [ ] Every new control is a real `button` or `a`, reachable with Tab, with a visible focus ring.
- [ ] Every new animation stops under `prefers-reduced-motion: reduce`, and its text is readable with JavaScript off.
- [ ] Images have alt text; decorative icons have `aria-hidden`.
- [ ] Nothing changes size after it first paints (no layout shift).
- [ ] Hard words you introduce are added to [`apps/site/lib/glossary.ts`](../apps/site/lib/glossary.ts).

The full design rules are in [`docs/04-DESIGN.md`](04-DESIGN.md).

## Ownership and upkeep

Harsh Bhanushali ([@harshbhx](https://github.com/harshbhx)) owns accessibility for both sites. This page is updated after every PageSpeed or axe pass and whenever a known barrier is fixed. Last full pass: **Nov 26, 2026**.

---

<details>
<summary><b>How to repeat every check</b></summary>

<br>

**Lighthouse / PageSpeed.** Build the site, serve it, and run:

```sh
npm run build -w @probate/site && npx serve apps/site/out -l 3060
npx lighthouse http://localhost:3060/ --chrome-flags="--headless=new"            # phone
npx lighthouse http://localhost:3060/ --chrome-flags="--headless=new" --preset=desktop
```

**axe, landing page, docs and live site.** Not part of CI. Needs Node 22+, a system Chrome, and axe-core installed anywhere outside the repo.

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

`a11y_check.mjs` drives Chrome over the DevTools protocol at 390x844 (mobile emulation, scale 2) and 1440x900, scrolls each page to the bottom so scroll-driven text is in its final state, and runs axe with the WCAG 2.0/2.1/2.2 A and AA tags plus best-practice rules. It exits non-zero if anything is found, and fails loudly if a page rendered a not-found view.

**Reduced motion.** Emulate `prefers-reduced-motion: reduce` (DevTools > Rendering), scroll the whole page, then check `document.getAnimations()` is empty and no visible text has an effective opacity below 0.95.

</details>

<details>
<summary><b>What was fixed, Nov 25 and 26, 2026</b></summary>

<br>

axe nodes found (mobile / desktop), before and after the first pass:

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
| Total | 67 (without the Judges states) | 28, all the `region` best-practice note |

- **Landing.** The hero docket title was an `h3` straight after the `h1`; now a paragraph. The Hacksgiving strip sat outside any landmark; it is now an `aside` with a name. The scrambled headline no longer resizes, so layout shift is 0.
- **Live site.** Generation cards had an `aria-label` that didn't contain their visible text (WCAG 2.5.3); the visible text now names the button. The hero sat outside `main`, so the skip link skipped it; `main` now wraps it. Case-file headings jumped from h1 to h4; they now go h2, h3. Links in the locked judges form were told apart by colour only; they are underlined.
- **Docs.** At 390 px the Hacksgiving banner's close button overlapped its text; the banner now reserves room for it, and the close icon uses the secondary text colour. Glossary words became plain buttons with one shared definition card, and docs links prefetch on intent rather than on sight, so pages do less work while loading.
- **Phones.** The pinned statement left a screen of empty space around six lines of text; on phones it is now a normal block that lights up as it scrolls past.
- **Reduced motion.** The page rise fade, the case-file open and close, and the generation side sheet still animated (Motion's `reducedMotion="user"` only stops transforms); they are now instant.
- **No JavaScript.** Section headings and the statement were in the HTML at opacity 0; a `noscript` rule in the root layout now shows them.

</details>
