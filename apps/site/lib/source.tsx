import { llms, loader } from 'fumadocs-core/source';
import { lucideIconsPlugin } from 'fumadocs-core/source/lucide-icons';
import { statusBadgesPlugin } from 'fumadocs-core/source/status-badges';
import { defineDocs } from 'fumadocs-mdx/macro';
import { metaSchema, pageSchema } from 'fumadocs-core/source/schema';
import { z } from 'zod';
import { docsRoute } from './shared';
import { openapi } from './openapi';

const docs = defineDocs({
  dir: 'content/docs',
  docs: {
    schema: pageSchema.extend({
      // A small label next to the page in the sidebar, e.g. "new" or "soon".
      status: z.string().optional(),
    }),
    // "Last updated" under each page, from git history.
    lastModified: true,
    postprocess: {
      includeProcessedMarkdown: true,
    },
  },
  meta: {
    schema: metaSchema,
  },
});

export const source = loader(
  {
    docs: docs.toFumadocsSource(),
    // One page per Courthouse route, grouped by tag, under Reference → HTTP API.
    openapi: await openapi.staticSource({
      baseDir: '(reference)/reference/api',
      groupBy: 'tag',
    }),
  },
  {
    baseUrl: docsRoute,
    plugins: [
      lucideIconsPlugin(),
      statusBadgesPlugin({
        renderBadge: (status) => (
          <span className="ms-auto rounded border border-gilt/40 px-1.5 py-px font-mono text-[10px] uppercase tracking-wide text-gilt">
            {status}
          </span>
        ),
      }),
      openapi.loaderPlugin(),
    ],
  },
);

export const docsLlms = llms(source, {
  renderPage: async (page) => {
    if (page.type === 'openapi') {
      const { id, bundled } = page.data.getSchema();
      return `# ${page.data.title} (${page.url})\n\nOpenAPI schema \`${id}\`:\n\n\`\`\`json\n${JSON.stringify(bundled.info, null, 2)}\n\`\`\``;
    }
    return `# ${page.data.title} (${page.url})

${await page.data.getText('processed')}`;
  },
  // link to the files under `/llms.mdx`
  renderUrl: (item) => (/^\/.*\.(md|txt)$/.test(item.url) ? `/llms.mdx${item.url}` : item.url),
});
