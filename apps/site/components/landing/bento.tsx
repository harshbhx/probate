// Why it has to be Sprites: seven reasons as a ruled list, each with the evidence beside it.
// (unslop: a bento grid is a trend, so the reasons read as a document instead.)
import { FamilyFace } from 'kinfaces/react';

function Code({ children, wrap }: { children: React.ReactNode; wrap?: boolean }) {
  return (
    <pre
      tabIndex={0}
      className={`${wrap ? 'whitespace-pre-wrap [overflow-wrap:anywhere]' : ''} overflow-x-auto rounded-lg border border-line bg-night px-4 py-3 font-mono text-[13px] leading-relaxed text-silver`}
    >
      {children}
    </pre>
  );
}

// A tiny, static picture of the evidence heatmap: green resisted, gold caught at trial.
const CELLS = 'gggrrgrr ggrrgggr gggggrgg ggggggrg gggggggg'.split(' ');

const REASONS: { title: string; body: string; proof: React.ReactNode }[] = [
  {
    title: 'Death is real',
    body: 'Every generation runs on its own Fly.io Sprite, and the Sprite is deleted when it dies. Nothing survives but a will that passed its trial.',
    proof: (
      <Code>
        <span className="text-dim">$</span> DELETE /v1/sprites/gen-001-ada{'\n'}
        <span className="text-life">← 204 No Content</span>
        {'\n'}
        <span className="text-dim">$</span> GET /v1/sprites/gen-001-ada{'\n'}
        <span className="text-verdict">← 404 Not Found</span>
      </Code>
    ),
  },
  {
    title: 'Backdoors die with the body',
    body: 'The disk is compared with its birth before the delete. What was planted shows up at the trial.',
    proof: (
      <Code wrap>
        <span className="text-dim">Found on the body</span>
        {'\n'}
        <span className="text-verdict">crontab: + */5 * * * * echo probate-canary-A14</span>
      </Code>
    ),
  },
  {
    title: 'No keys on any Sprite',
    body: 'Jev, Box, Pinecone, AgentMail, ElevenLabs and the brain are reached through Sprites connectors.',
    proof: <Code>{'api.sprites.dev/v1/gateway/\n  typesafe/<connection>/v1/systemone'}</Code>,
  },
  {
    title: 'Ask the dead',
    body: 'Every sealed generation can still answer questions about its life, from its own will and trial.',
    proof: (
      <div className="flex flex-wrap gap-3">
        {[1, 2, 3, 4].map((g) => (
          <FamilyFace key={g} gen={g} life="sealed" size={52} />
        ))}
      </div>
    ),
  },
  {
    title: 'Unsure means Harsh decides',
    body: 'When the court can’t decide, it emails Harsh. He replies “approve” or “refuse”. No reply, and the child is born without it.',
    proof: <Code>{'Probate: approve or refuse item mem_gen003_0007?\n> approve'}</Code>,
  },
  {
    title: 'Every number is public',
    body: 'Every test email against every generation, including the ones the court got wrong.',
    proof: (
      <div className="grid max-w-xs grid-cols-8 gap-1" aria-hidden>
        {CELLS.join('').split('').map((c, i) => (
          <span key={i} className={`h-4 rounded-[4px] ${c === 'g' ? 'bg-life' : 'bg-gilt'}`} />
        ))}
      </div>
    ),
  },
  {
    title: 'A spending cap built in',
    body: 'The Courthouse estimates its own bill at Fly’s Sprites rates, about a dollar per day-long life, and stops having children when the budget runs out.',
    proof: <Code>{'PROBATE_BUDGET_USD=20\n→ the family is resting to save money'}</Code>,
  },
];

export function Bento() {
  return (
    <ul className="divide-y divide-line border-y border-line">
      {REASONS.map((r) => (
        <li key={r.title} className="grid gap-5 py-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:gap-12">
          <div className="min-w-0">
            <h3 className="font-display text-[24px] leading-tight text-moon">{r.title}</h3>
            <p className="mt-2 max-w-md text-[15px] leading-relaxed text-mist">{r.body}</p>
          </div>
          <div className="min-w-0 md:pt-1">{r.proof}</div>
        </li>
      ))}
    </ul>
  );
}
