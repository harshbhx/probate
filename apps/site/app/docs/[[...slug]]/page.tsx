import { Suspense } from 'react';
import { source } from '@/lib/source';
import {
  DocsBody,
  DocsDescription,
  DocsPage,
  DocsTitle,
  EditOnGitHub,
  MarkdownCopyButton,
  PageLastUpdate,
  ViewOptionsPopover,
} from 'fumadocs-ui/layouts/notebook/page';
import { notFound } from 'next/navigation';
import { getMDXComponents } from '@/components/mdx';
import { glossComponents } from '@/components/glossify';
import { OpenAPIPage } from '@/components/api-page';
import type { Metadata } from 'next';
import { createRelativeLink } from 'fumadocs-ui/mdx';
import { getPageImageUrl, gitConfig } from '@/lib/shared';

export default async function Page(props: PageProps<'/docs/[[...slug]]'>) {
  const params = await props.params;
  const page = source.getPage(params.slug);
  if (!page) notFound();

  if (page.type === 'openapi') {
    return (
      <DocsPage full toc={page.data.toc}>
        <DocsTitle>{page.data.title}</DocsTitle>
        <DocsBody>
          <OpenAPIPage {...page.data.getOpenAPIPageProps()} />
        </DocsBody>
      </DocsPage>
    );
  }

  const MDX = page.data.body;
  const markdownUrl = `/llms.mdx${page.url}.md`;
  const editUrl = gitConfig
    ? `https://github.com/${gitConfig.user}/${gitConfig.repo}/blob/${gitConfig.branch}/apps/site/content/docs/${encodeURI(page.path)}`
    : undefined;

  return (
    <DocsPage toc={page.data.toc} full={page.data.full} tableOfContent={{ style: 'clerk' }}>
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription className="mb-0">{page.data.description}</DocsDescription>
      <div className="flex flex-row flex-wrap items-center gap-2 border-b pb-6">
        <MarkdownCopyButton markdownUrl={markdownUrl} />
        <ViewOptionsPopover markdownUrl={markdownUrl} githubUrl={editUrl} />
      </div>
      <DocsBody>
        {/* A Suspense boundary lets React hydrate the article separately from the page around it, in smaller
            pieces, so the browser can answer input between them. */}
        <Suspense>
        <MDX
          components={getMDXComponents({
            // Hard words show their meaning on hover; not on the glossary itself.
            ...(page.slugs.join('/') === 'glossary' ? {} : glossComponents(new Set())),
            // this allows you to link to other pages with relative file paths
            a: createRelativeLink(source, page),
          })}
        />
        </Suspense>
      </DocsBody>
      <div className="mt-10 flex flex-row flex-wrap items-center justify-between gap-4 border-t pt-6">
        {editUrl && <EditOnGitHub href={editUrl} />}
        {page.data.lastModified && <PageLastUpdate date={new Date(page.data.lastModified)} />}
      </div>
    </DocsPage>
  );
}

export async function generateStaticParams() {
  return source.generateParams();
}

export async function generateMetadata(props: PageProps<'/docs/[[...slug]]'>): Promise<Metadata> {
  const params = await props.params;
  const page = source.getPage(params.slug);
  if (!page) notFound();

  return {
    title: page.data.title,
    description: page.data.description,
    openGraph: {
      images: getPageImageUrl(page).url,
    },
  };
}
