import type { MetadataRoute } from 'next';
import { siteUrl } from '@/lib/shared';
import { source } from '@/lib/source';

// Written once at build time (the site is a static export).
export const dynamic = 'force-static';

/** Every public page: the landing page, the write-up, the links page and all of the docs. */
export default function sitemap(): MetadataRoute.Sitemap {
  const at = (path: string) => new URL(path, siteUrl).toString();
  return [
    { url: at('/'), priority: 1 },
    { url: at('/article'), priority: 0.9 },
    { url: at('/data'), priority: 0.8 },
    { url: at('/links'), priority: 0.5 },
    ...source.getPages().map((page) => ({ url: at(page.url), priority: 0.7 })),
  ];
}
