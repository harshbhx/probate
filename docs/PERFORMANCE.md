# Performance and security headers (landing page and docs)

Written 26 Nov 2026. The site is a Next.js static export (`apps/site`) served by a Cloudflare Worker with static assets.

## Baseline

PageSpeed Insights, mobile, 26 Nov 2026 (Lighthouse 13.6): Performance 96, Accessibility 97, Best Practices 96, SEO 100.
After this change was deployed, PageSpeed Insights gives the live landing page 100 in every category, on mobile and desktop ([the report](https://pagespeed.web.dev/analysis/https-probate-dualmindlab-tech/vpe78glfex2y2g3pr7glw7)).

## What changed and why

| Finding | Cause | Fix |
| --- | --- | --- |
| Contrast | The pinned statement started each word at opacity 0.16 (1.46:1) | Words start in `--color-unlit` (#757c89, 4.75:1) and move to their lit colour with a CSS variable. Reduced motion shows them lit. |
| Console errors | Next asks for prefetch files named `__next.a.b.txt`, the export writes `__next.a/b.txt`: 404 | `scripts/postbuild.mjs` writes the dotted copies too |
| Layout shift | Hero text scramble changed glyph widths; web fonts swapped without matching fallbacks | The real text sets the box; metric-matched fallback faces for Geist and Newsreader; Geist preloaded |
| Forced reflow | `ScrollRegions` read layout inside a MutationObserver on every change | Reads batched, once per frame |
| Unused JavaScript | The search index (about 110 KB) and the animation library loaded on every page; links prefetched the docs shell | Search loads on first open; the four below-the-fold sections hydrate when about to scroll into view (`components/landing/deferred.tsx`); Reveal, CountUp, TextReveal, ScrollProgress no longer use the animation library; landing links prefetch on pointer, focus or touch |
| Render-blocking CSS | One external stylesheet | `experimental.inlineCss` |
| Headers | None | `public/_headers` |

## Headers (`apps/site/public/_headers`)

- `Content-Security-Policy`: `script-src 'self'` plus sha256 of the two inline scripts that are the same on every page (theme, dismissed banner). The per-page inline scripts (Next flight data and bootstrap) are moved by the post-build step into one external file per page, because a hash per page would exceed Cloudflare's limit of 100 rules and 2000 characters per line. A nonce is impossible in a static export. `style-src` keeps `'unsafe-inline'` because React and the scroll effects write `style=""` attributes, which cannot be hashed. `connect-src` adds the origin of `NEXT_PUBLIC_LIVE_URL` when it is set at build time.
- `Strict-Transport-Security` 2 years, includeSubDomains, no preload. `Cross-Origin-Opener-Policy: same-origin`. `X-Frame-Options: DENY` and `frame-ancestors 'none'`. `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`.
- Cache: `/_next/static/*` immutable for a year; `/product`, `/diagrams`, `/moments` a week; HTML keeps Cloudflare's default `max-age=0, must-revalidate` (a deploy replaces the hashed chunks, so stale HTML must not be served).
- Not done: Trusted Types (`require-trusted-types-for 'script'`). It needs a default policy for the chunk loader and was not tested against search, the Base UI popovers and navigation. Cloudflare's own injected inline script (bot detection) cannot be allowed by hash, so it is blocked by the CSP and may log one console message.

## Re-running Lighthouse

```
mkdir lh && cd lh && npm init -y && npm i lighthouse
CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe" npx lighthouse https://probate.dualmindlab.tech/ --preset=desktop --view
```
Mobile is the default. Lab numbers vary with the machine; run each page a few times.
