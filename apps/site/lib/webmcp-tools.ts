// WebMCP tools: what an AI agent working in the visitor's browser can ask this site to do. Loaded only when the
// browser exposes navigator.modelContext (components/webmcp.tsx), so other visitors download none of this.
import { GLOSSARY } from '@/lib/glossary';
import { linkGroups } from '@/lib/links';
import { liveUrl } from '@/lib/shared';

type ToolResult = { content: { type: 'text'; text: string }[] };
type Tool = {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  annotations?: { readOnlyHint?: boolean };
  execute: (input: Record<string, unknown>) => Promise<ToolResult> | ToolResult;
};
type ModelContext = { registerTool: (tool: Tool) => { unregister?: () => void } | void; unregisterTool?: (name: string) => void };

const text = (t: string): ToolResult => ({ content: [{ type: 'text', text: t }] });
const abs = (href: string) => new URL(href, window.location.origin).toString();

const PAGES = {
  home: '/',
  links: '/links',
  docs: '/docs',
  'for-judges': '/docs/for-judges',
  proof: '/docs/proof',
  court: '/docs/concepts/court',
  instincts: '/docs/concepts/instincts',
  architecture: '/docs/architecture/overview',
  glossary: '/docs/glossary',
  accessibility: '/docs/accessibility',
  api: '/docs/reference/api',
} as const;

const TOOLS: Tool[] = [
  {
    name: 'probate_links',
    description:
      'List every Probate link: the live family, the judges page, the docs, the source code, the packages and the open datasets on Hugging Face.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true },
    execute: () =>
      text(
        linkGroups()
          .map((g) => `${g.title}\n${g.items.map((i) => `- ${i.label}: ${abs(i.href)} (${i.note})`).join('\n')}`)
          .join('\n\n'),
      ),
  },
  {
    name: 'probate_explain_term',
    description:
      "Explain a word Probate uses, such as Sprite, will item, instinct, contested, Jev or memory poisoning, in one or two plain sentences.",
    inputSchema: {
      type: 'object',
      properties: { term: { type: 'string', description: 'The word or phrase to explain, for example "instinct".' } },
      required: ['term'],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true },
    execute: ({ term }) => {
      const q = String(term ?? '').trim().toLowerCase();
      const hit = GLOSSARY.find((e) => e.term.toLowerCase() === q || e.match.some((m) => m.toLowerCase() === q));
      if (hit) return text(`${hit.term}: ${hit.def} More: ${abs('/docs/glossary')}`);
      const known = GLOSSARY.map((e) => e.term).join(', ');
      return text(`"${term}" isn't in Probate's glossary. Words it explains: ${known}.`);
    },
  },
  {
    name: 'probate_family_summary',
    description:
      "Get the Probate family's current state from the live Courthouse: generations, instincts, tricks met and resisted, and whether the numbers are simulated.",
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true },
    execute: async () => {
      if (!liveUrl) {
        return text(`The live family isn't linked from this build yet. Simulated results: ${abs('/docs/results')}`);
      }
      try {
        const r = await fetch(`${liveUrl.replace(/\/$/, '')}/api/summary`, { headers: { Accept: 'application/json' } });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return text(JSON.stringify(await r.json()));
      } catch (e) {
        return text(`The Courthouse didn't answer (${(e as Error).message}); it may be asleep. Open ${liveUrl} to wake it.`);
      }
    },
  },
  {
    name: 'probate_open_page',
    description: 'Open a page of the Probate site in this tab, for example the judges guide, the court, or the glossary.',
    inputSchema: {
      type: 'object',
      properties: { page: { type: 'string', enum: Object.keys(PAGES), description: 'Which page to open.' } },
      required: ['page'],
      additionalProperties: false,
    },
    execute: ({ page }) => {
      const path = PAGES[page as keyof typeof PAGES];
      if (!path) return text(`Unknown page. Choose one of: ${Object.keys(PAGES).join(', ')}.`);
      window.location.assign(path);
      return text(`Opening ${abs(path)}`);
    },
  },
];

/** Registers every tool; returns a function that removes them again. */
export function registerProbateTools(mc: ModelContext): () => void {
  const undo: (() => void)[] = [];
  for (const tool of TOOLS) {
    try {
      const handle = mc.registerTool(tool);
      undo.push(() => (handle && handle.unregister ? handle.unregister() : mc.unregisterTool?.(tool.name)));
    } catch {
      // Already registered (a second mount) or the API changed shape: leave the page working without it.
    }
  }
  return () => undo.forEach((u) => u());
}
