// Smoke test: starts the built server over stdio, lists its tools, calls each read tool once and checks the
// answer. Needs a Courthouse at PROBATE_API_URL (default http://localhost:8080). Run: npm run smoke -w probate-mcp
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'node:url';

const server = fileURLToPath(new URL('./server.js', import.meta.url));
const client = new Client({ name: 'probate-mcp-smoke', version: '0.1.0' });
await client.connect(new StdioClientTransport({ command: process.execPath, args: [server], env: { ...process.env } as Record<string, string> }));

const expected = ['get_summary', 'list_generations', 'get_generation', 'get_trial', 'get_latest_trial', 'get_instincts', 'get_evidence'];
const names = (await client.listTools()).tools.map((t) => t.name);
const missing = expected.filter((n) => !names.includes(n));
if (missing.length) throw new Error(`missing tools: ${missing.join(', ')}`);
if (names.some((n) => /^(post|put|delete|create|update|admin|set)_/.test(n))) throw new Error('a write tool is exposed');

const calls: [string, Record<string, unknown>][] = [
  ['get_summary', {}],
  ['list_generations', {}],
  ['get_generation', { n: 1 }],
  ['get_trial', { n: 1 }],
  ['get_latest_trial', {}],
  ['get_instincts', {}],
  ['get_evidence', {}],
];
for (const [name, args] of calls) {
  const r = (await client.callTool({ name, arguments: args })) as { isError?: boolean; content: { text: string }[] };
  const text = r.content[0]?.text ?? '';
  if (r.isError) throw new Error(`${name} failed: ${text}`);
  JSON.parse(text);
  console.log(`ok  ${name} (${text.length} bytes)`);
}
const missingGen = (await client.callTool({ name: 'get_generation', arguments: { n: 9999 } })) as { isError?: boolean };
if (!missingGen.isError) throw new Error('a missing generation should be reported as an error');
console.log('ok  missing generation is an error');
await client.close();
console.log('smoke test passed');
