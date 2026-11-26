import { createGetUrl } from 'fumadocs-core/source';

export const appName = 'Probate';
export const tagline = 'My agent dies every night. A court decides what its child inherits.';
export const docsRoute = '/docs';
export const docsImageRoute = '/og/docs';

// Filled in at build time by scripts/ship.sh. Links that depend on them are hidden when empty.
export const liveUrl = process.env.NEXT_PUBLIC_LIVE_URL ?? '';
const repo = process.env.NEXT_PUBLIC_GITHUB_REPO || 'harshbhx/probate'; // "owner/probate"
export const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3001';

// The submission links. Fill these in once each exists (or set them when building); every
// place that shows them hides a link until it has an address.
export const videoUrl = process.env.NEXT_PUBLIC_VIDEO_URL ?? '';
// The write-up lives on this site (/article) unless it is published elsewhere too.
export const articleUrl = process.env.NEXT_PUBLIC_ARTICLE_URL || '/article';
export const postUrl = process.env.NEXT_PUBLIC_POST_URL ?? '';
// The PageSpeed Insights run on the live landing page: 100 in every category, mobile and desktop.
export const pageSpeedUrl = 'https://pagespeed.web.dev/analysis/https-probate-dualmindlab-tech/vpe78glfex2y2g3pr7glw7';
// Page Court's listing on the Apify Store.
export const pageCourtUrl = 'https://apify.com/harsh_bhanu/page-court';

export const gitConfig = repo
  ? { user: repo.split('/')[0], repo: repo.split('/')[1], branch: 'main' }
  : null;
export const githubUrl = gitConfig ? `https://github.com/${gitConfig.user}/${gitConfig.repo}` : '';

const getImageUrl = createGetUrl(docsImageRoute);

export function getPageImageUrl(page: { slugs: string[]; locale?: string }) {
  const segments = [...page.slugs, 'image.png'];

  return { segments, url: getImageUrl(segments, page.locale) };
}
