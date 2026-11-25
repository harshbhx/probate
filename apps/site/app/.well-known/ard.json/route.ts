// Agentic Resource Discovery manifest: tells AI agents what Probate offers them (lib/agents.ts).
import { ardManifest } from '@/lib/agents';

export const revalidate = false;

export function GET() {
  return Response.json(ardManifest(), { headers: { 'Content-Type': 'application/json' } });
}
