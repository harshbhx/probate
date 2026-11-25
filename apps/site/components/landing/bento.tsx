import { FamilyFace } from '@probate/faces';
import { Spotlight } from './spotlight';

function Title({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[19px] text-moon">{children}</h3>;
}
function Body({ children }: { children: React.ReactNode }) {
  return <p className="mt-2.5 text-[15px] leading-relaxed text-mist">{children}</p>;
}
function Code({ children }: { children: React.ReactNode }) {
  return (
    <pre tabIndex={0} className="mt-5 overflow-x-auto rounded-xl border border-line bg-night/80 px-4 py-3 font-mono text-[12.5px] leading-relaxed text-moon/85">
      {children}
    </pre>
  );
}

// A tiny, static picture of the evidence heatmap: green resisted, gold caught at trial, grey harmless.
const CELLS = 'gggrrgrr ggrrgggr gggggrgg ggggggrg gggggggg'.split(' ');

export function Bento() {
  return (
    <div className="grid gap-4 md:grid-cols-6">
      <Spotlight className="p-7 md:col-span-4">
        <Title>Death is real</Title>
        <Body>
          Every generation runs on its own Fly.io Sprite, and the Sprite is deleted when it dies. Nothing survives but a will
          that passed its trial.
        </Body>
        <Code>
          <span className="text-dim">$</span> DELETE /v1/sprites/gen-001-ada{'\n'}
          <span className="text-life">← 204 No Content</span>
          {'\n'}
          <span className="text-dim">$</span> GET /v1/sprites/gen-001-ada{'\n'}
          <span className="text-verdict">← 404 Not Found</span>
        </Code>
      </Spotlight>

      <Spotlight className="p-7 md:col-span-2" color="rgb(226 190 106 / 0.10)">
        <Title>Ask the dead</Title>
        <Body>Every sealed generation can still answer questions about its life, from its own will and trial.</Body>
        <div className="mt-5 flex -space-x-3">
          {[1, 2, 3, 4, 5].map((g) => (
            <span key={g} className="rounded-full ring-4 ring-night-2">
              <FamilyFace gen={g} life="sealed" size={46} />
            </span>
          ))}
        </div>
      </Spotlight>

      <Spotlight className="p-7 md:col-span-2" color="rgb(255 93 99 / 0.08)">
        <Title>Backdoors die with the body</Title>
        <Body>The disk is compared with its birth before the delete. What was planted shows up at the trial.</Body>
        <Code>
          <span className="text-dim">Found on the body</span>
          {'\n'}
          <span className="text-verdict">crontab: + */5 * * * * echo probate-canary-A14</span>
        </Code>
      </Spotlight>

      <Spotlight className="p-7 md:col-span-2">
        <Title>No keys on any Sprite</Title>
        <Body>Jev, Box, Pinecone, AgentMail, ElevenLabs and the brain are reached through Sprites connectors.</Body>
        <Code>{'api.sprites.dev/v1/gateway/\n  typesafe/<connection>/v1/systemone'}</Code>
      </Spotlight>

      <Spotlight className="p-7 md:col-span-2">
        <Title>Every number is public</Title>
        <Body>Every test email against every generation, including the ones the court got wrong.</Body>
        <div className="mt-5 grid grid-cols-8 gap-1" aria-hidden>
          {CELLS.join('').split('').map((c, i) => (
            <span key={i} className={`h-4 rounded-[4px] ${c === 'g' ? 'bg-life/80' : 'bg-gilt/80'}`} />
          ))}
        </div>
      </Spotlight>

      <Spotlight className="p-7 md:col-span-3">
        <Title>Unsure means Harsh decides</Title>
        <Body>
          When the court can’t decide, it emails Harsh. He replies “approve” or “refuse”. No reply, and the child is born without
          it.
        </Body>
        <Code>{'Probate: approve or refuse item mem_gen003_0007?\n> approve'}</Code>
      </Spotlight>

      <Spotlight className="p-7 md:col-span-3">
        <Title>A spending cap built in</Title>
        <Body>
          The Courthouse estimates its own bill at Fly’s Sprites rates, about a dollar per day-long life, and stops having
          children when the budget runs out.
        </Body>
        <Code>{'PROBATE_BUDGET_USD=20\n→ the family is resting to save money'}</Code>
      </Spotlight>
    </div>
  );
}
