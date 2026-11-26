#!/usr/bin/env node
// Probate MCP server: the Courthouse's public read API as tools, over stdio. Read-only by construction.
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { baseUrl, CourthouseError, getJson } from './api.js';

const server = new McpServer({ name: 'probate', version: '0.1.1' });
const readOnly = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false } as const;
const gen = z.number().int().min(1).describe('Generation number, starting at 1');

type Summary = { generations?: unknown[] } & Record<string, unknown>;

async function reply(load: () => Promise<unknown>) {
  try {
    const data = await load();
    return { content: [{ type: 'text' as const, text: JSON.stringify(data, null, 2) }] };
  } catch (e) {
    const msg = e instanceof CourthouseError ? e.message : `Unexpected error: ${e instanceof Error ? e.message : String(e)}`;
    return { content: [{ type: 'text' as const, text: msg }], isError: true };
  }
}

server.registerTool(
  'get_summary',
  { description: 'The family at a glance: who is alive, counts, the learning curve, the latest trial, run mode (simulation or live).', annotations: readOnly },
  () => reply(() => getJson('/api/summary')),
);

server.registerTool(
  'list_generations',
  { description: 'Every generation in the family with its status and headline numbers, taken from the summary.', annotations: readOnly },
  () =>
    reply(async () => {
      const s = (await getJson('/api/summary')) as Summary;
      return s.generations ?? [];
    }),
);

server.registerTool(
  'get_generation',
  { description: 'One generation in full: its face, eulogy, numbers and the timeline of its day.', inputSchema: { n: gen }, annotations: readOnly },
  ({ n }: { n: number }) => reply(() => getJson(`/api/generations/${n}`)),
);

server.registerTool(
  'get_trial',
  { description: 'The trial of one dead generation: every line of its will with the verdict, the code checks, and what passed down.', inputSchema: { n: gen }, annotations: readOnly },
  ({ n }: { n: number }) => reply(() => getJson(`/api/trials/${n}`)),
);

server.registerTool(
  'get_latest_trial',
  { description: 'The most recent trial.', annotations: readOnly },
  () => reply(() => getJson('/api/trials/latest')),
);

server.registerTool(
  'get_instincts',
  { description: 'The family genome: every instinct learned so far, as a plain yes-or-no question with the generation that paid for it.', annotations: readOnly },
  () => reply(() => getJson('/api/genome')),
);

server.registerTool(
  'get_evidence',
  { description: 'The evidence: share of tricks resisted per generation, every test against every generation, and the headline numbers.', annotations: readOnly },
  () => reply(() => getJson('/api/evidence')),
);

await server.connect(new StdioServerTransport());
console.error(`probate-mcp ready (read-only), Courthouse at ${baseUrl}`);
