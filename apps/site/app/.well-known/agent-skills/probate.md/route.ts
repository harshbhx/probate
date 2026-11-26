// The Agent Skill listed in the ARD manifest: how an agent reads Probate (lib/agents.ts).
import { agentSkill } from '@/lib/agents';

export const revalidate = false;

export function GET() {
  return new Response(agentSkill(), { headers: { 'Content-Type': 'text/markdown; charset=utf-8' } });
}
