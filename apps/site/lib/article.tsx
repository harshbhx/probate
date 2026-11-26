// The write-up, kept as a plain Markdown file (content/article/*.md) and rendered by the site itself, so the
// article lives with the code it describes and needs no outside blog.
import { loader } from 'fumadocs-core/source';
import { defineDocs } from 'fumadocs-mdx/macro';
import { pageSchema } from 'fumadocs-core/source/schema';
import { z } from 'zod';

const articles = defineDocs({
  dir: 'content/article',
  docs: {
    schema: pageSchema.extend({
      author: z.string(),
      date: z.string().or(z.date()),
      cover: z.string().optional(),
      coverAlt: z.string().optional(),
    }),
    postprocess: { includeProcessedMarkdown: true },
  },
});

export const articleSource = loader({ source: articles.toFumadocsSource(), baseUrl: '/article' });

export function theArticle() {
  const page = articleSource.getPages()[0];
  if (!page) throw new Error('No article in content/article');
  return page;
}
