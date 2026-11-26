// The second Agent Skill in the ARD manifest: Probate's court checks as a tool any agent can run (lib/agents.ts).
import { courtChecksSkill } from '@/lib/agents';

export const revalidate = false;

export function GET() {
  return new Response(courtChecksSkill(), { headers: { 'Content-Type': 'text/markdown; charset=utf-8' } });
}
