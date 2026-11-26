import type { Metadata } from 'next';
import { FamilyFace } from 'kinfaces/react';
import Link from '@/components/intent-link';
import { getMDXComponents } from '@/components/mdx';
import { theArticle } from '@/lib/article';
import { appName, githubUrl, siteUrl } from '@/lib/shared';

// The write-up, rendered from content/article/my-agent-dies-every-night.md: one reading column, the contents
// beside it on wide screens, and the reading-progress line from the home layout above it.

function fmt(d: Date) {
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
}

export default async function ArticlePage() {
  const page = theArticle();
  const { title, description, author, cover, coverAlt } = page.data;
  const date = new Date(page.data.date);
  const MDX = page.data.body;
  const words = (await page.data.getText('processed')).split(/\s+/).filter(Boolean).length;
  const minutes = Math.max(1, Math.round(words / 230));
  const url = `${siteUrl}/article`;
  const share = encodeURIComponent(url);
  const ld = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    description,
    datePublished: date.toISOString(),
    author: { '@type': 'Person', name: author, url: 'https://github.com/harshbhx' },
    publisher: { '@type': 'Organization', name: appName },
    image: cover ? `${siteUrl}${cover}` : undefined,
    mainEntityOfPage: url,
    wordCount: words,
  };

  return (
    <article className="mx-auto w-full max-w-6xl px-5 pb-20 pt-10 sm:px-6 md:pt-16">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld).replace(/</g, '\\u003c') }} />
      <header className="max-w-3xl">
        <h1 className="font-display text-[44px] font-[420] leading-[1.02] tracking-[-0.03em] text-balance sm:text-[64px]">{title}</h1>
        <p className="mt-5 max-w-2xl text-[19px] leading-relaxed text-silver sm:text-[21px]">{description}</p>
        <div className="mt-7 flex items-center gap-3 border-t border-line pt-5">
          <FamilyFace gen={7} life="alive" mood="happy" instincts={3} size={44} title="Grace, generation 7" />
          <p className="text-[15px] text-mist">
            <span className="text-moon">{author}</span>
            <span aria-hidden className="mx-2 text-dim">·</span>
            <time dateTime={date.toISOString().slice(0, 10)}>{fmt(date)}</time>
            <span aria-hidden className="mx-2 text-dim">·</span>
            {minutes} min read
          </p>
        </div>
      </header>

      {/* On phones the cover is left out (and, being lazy and hidden, never downloaded): the words come first. */}
      {cover ? (
        <figure className="mt-10 hidden overflow-hidden rounded-2xl border border-line bg-night-2 sm:block">
          {/* eslint-disable-next-line @next/next/no-img-element -- static export, pre-sized WebP */}
          <img
            src={cover}
            srcSet={cover.endsWith('.webp') ? `${cover.replace('.webp', '-720.webp')} 720w, ${cover.replace('.webp', '-1280.webp')} 1280w, ${cover} 2560w` : undefined}
            sizes="(min-width: 1152px) 1104px, calc(100vw - 40px)"
            alt={coverAlt ?? ''}
            width={2560}
            height={2000}
            loading="lazy"
            decoding="async" className="aspect-[16/9] w-full object-cover object-top" />
        </figure>
      ) : null}

      <div className="mt-12 grid gap-12 lg:grid-cols-[minmax(0,1fr)_15rem]">
        <div className="article-body prose min-w-0 max-w-[44rem]">
          <MDX components={getMDXComponents()} />
        </div>
        <aside className="hidden lg:block">
          <nav aria-label="In this article" className="sticky top-24">
            <p className="text-[13px] text-dim">In this article</p>
            <ol className="mt-3 grid gap-1 border-l border-line">
              {page.data.toc
                .filter((t) => t.depth === 2)
                .map((t) => (
                  <li key={t.url}>
                    <a href={t.url} className="-ml-px block border-l border-transparent py-1 pl-4 text-[14px] leading-snug text-mist hover:border-gilt hover:text-moon">
                      {t.title}
                    </a>
                  </li>
                ))}
            </ol>
          </nav>
        </aside>
      </div>

      <footer className="mt-16 grid gap-6 border-t border-line pt-10 md:grid-cols-[1fr_auto] md:items-end">
        <div className="max-w-xl">
          <p className="font-display text-[26px] leading-tight text-moon">Written by {author}</p>
          <p className="mt-2 text-[16px] leading-relaxed text-silver">
            B.Tech student who builds AI agents. Probate was written fresh during Fly.io Hacksgiving 2026.
          </p>
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-[15px]">
            <Link href="/docs/for-judges" className="text-moon underline decoration-gilt/50 underline-offset-[4px] hover:decoration-gilt">
              For judges
            </Link>
            <Link href="/docs/memory-court" className="text-moon underline decoration-gilt/50 underline-offset-[4px] hover:decoration-gilt">
              The memory court
            </Link>
            <a href={githubUrl || 'https://github.com/harshbhx/probate'} className="text-moon underline decoration-gilt/50 underline-offset-[4px] hover:decoration-gilt">
              Source code
            </a>
          </div>
        </div>
        <div className="flex gap-3 text-[15px]">
          <a
            href={`https://x.com/intent/post?text=${encodeURIComponent(title)}&url=${share}`}
            className="inline-flex min-h-11 items-center rounded-lg border border-line-strong px-4 text-moon hover:bg-night-3"
          >
            Share on X
          </a>
          <a
            href={`https://www.linkedin.com/sharing/share-offsite/?url=${share}`}
            className="inline-flex min-h-11 items-center rounded-lg border border-line-strong px-4 text-moon hover:bg-night-3"
          >
            Share on LinkedIn
          </a>
        </div>
      </footer>
    </article>
  );
}

export function generateMetadata(): Metadata {
  const page = theArticle();
  const date = new Date(page.data.date).toISOString();
  return {
    title: page.data.title,
    description: page.data.description,
    alternates: { canonical: '/article' },
    authors: [{ name: page.data.author, url: 'https://github.com/harshbhx' }],
    openGraph: {
      type: 'article',
      title: page.data.title,
      description: page.data.description,
      publishedTime: date,
      authors: [page.data.author],
      images: '/og/article/image.png',
    },
    twitter: { card: 'summary_large_image', images: '/og/article/image.png' },
  };
}
