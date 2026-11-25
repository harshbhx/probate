import { createGetUrl } from 'fumadocs-core/source';

export const appName = 'Probate';
export const tagline = 'My agent dies every night. A court decides what its child inherits.';
export const docsRoute = '/docs';
export const docsImageRoute = '/og/docs';

// Filled in at build time by scripts/ship.sh. Links that depend on them are hidden when empty.
export const liveUrl = process.env.NEXT_PUBLIC_LIVE_URL ?? '';
const repo = process.env.NEXT_PUBLIC_GITHUB_REPO ?? ''; // "owner/probate"
export const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3001';

export const gitConfig = repo
  ? { user: repo.split('/')[0], repo: repo.split('/')[1], branch: 'main' }
  : null;
export const githubUrl = gitConfig ? `https://github.com/${gitConfig.user}/${gitConfig.repo}` : '';

const getImageUrl = createGetUrl(docsImageRoute);

export function getPageImageUrl(page: { slugs: string[]; locale?: string }) {
  const segments = [...page.slugs, 'image.png'];

  return { segments, url: getImageUrl(segments, page.locale) };
}
