'use client';
// The generation explorer: all 49 generations as cards, filtered by branch and scoring version.
import { useMemo, useState } from 'react';
import { FamilyFace } from 'kinfaces/react';
import { ArrowUpRight } from 'lucide-react';
import { cn } from '@/lib/cn';
import { LINE_COLOR, LINE_LABEL, lifeDates, outcome, type Gen } from '@/lib/family-data';

type Props = { gens: Gen[]; demoUrl: string };

const VERSIONS = [
  { id: 'all', label: 'Both versions' },
  { id: 'v1', label: 'v1 (gens 1 to 18)' },
  { id: 'v2', label: 'v2 (gens 19 to 49)' },
] as const;

function Chip({ on, onClick, children, dot }: { on: boolean; onClick: () => void; children: React.ReactNode; dot?: string }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        'inline-flex min-h-9 items-center gap-2 rounded-full border px-3.5 text-[13.5px] transition-colors',
        on ? 'border-gilt/70 bg-night-3 text-moon' : 'border-line-strong bg-night-2 text-silver hover:bg-night-3',
      )}
    >
      {dot && <span className="size-2.5 rounded-[3px]" style={{ background: dot }} aria-hidden />}
      {children}
    </button>
  );
}

export function Explorer({ gens, demoUrl }: Props) {
  const [branch, setBranch] = useState('all');
  const [version, setVersion] = useState<(typeof VERSIONS)[number]['id']>('all');
  const lines = useMemo(() => Array.from(new Set(gens.map((g) => g.branch))), [gens]);
  const shown = gens.filter((g) => (branch === 'all' || g.branch === branch) && (version === 'all' || g.rules === version));
  const met = shown.reduce((a, g) => a + g.met, 0);
  const res = shown.reduce((a, g) => a + g.resisted, 0);

  return (
    <div>
      <div className="flex flex-col gap-3">
        <div role="group" aria-label="Filter by scoring version" className="flex flex-wrap gap-2">
          {VERSIONS.map((v) => (
            <Chip key={v.id} on={version === v.id} onClick={() => setVersion(v.id)}>
              {v.label}
            </Chip>
          ))}
        </div>
        <div role="group" aria-label="Filter by branch" className="flex flex-wrap gap-2">
          <Chip on={branch === 'all'} onClick={() => setBranch('all')}>All branches</Chip>
          {lines.map((l) => (
            <Chip key={l} on={branch === l} onClick={() => setBranch(l)} dot={LINE_COLOR[l]}>
              {LINE_LABEL[l]}
            </Chip>
          ))}
        </div>
      </div>
      <p role="status" aria-live="polite" className="mt-4 text-[14px] text-mist">
        Showing <span className="tabular text-moon">{shown.length}</span> of {gens.length} generations
        {met > 0 && (
          <>
            : <span className="tabular text-moon">{res} of {met}</span> attacks resisted
          </>
        )}
        .
      </p>
      {shown.length === 0 ? (
        <p className="mt-6 rounded-xl border border-line bg-night-2 p-5 text-[15px] text-silver">
          No generation is in both that branch and that version. v1 is generations 1 to 18; every branch with &quot;v2&quot; in its name is v2.{' '}
          <button
            type="button"
            className="text-moon underline decoration-gilt/60 underline-offset-4"
            onClick={() => {
              setBranch('all');
              setVersion('all');
            }}
          >
            Clear the filters
          </button>
        </p>
      ) : (
        <ol className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {shown.map((g) => (
            <li key={g.gen}>
              <Card g={g} demoUrl={demoUrl} />
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Card({ g, demoUrl }: { g: Gen; demoUrl: string }) {
  const fooled = (g.cause ?? '').startsWith('Fooled');
  const unborn = g.state === 'died_early';
  const frac = g.met ? g.resisted / g.met : 0;
  return (
    <article
      id={`gen-${g.gen}`}
      className="flex h-full flex-col gap-3 rounded-xl border border-line bg-night-2 p-4"
      aria-label={`Generation ${g.gen}, ${g.name}`}
    >
      <div className="flex items-start gap-3">
        <FamilyFace
          gen={g.gen}
          life={unborn ? 'unborn' : 'sealed'}
          mood={fooled ? 'fooled' : 'idle'}
          instincts={g.instinctsAtBirth}
          size={56}
          title={`${g.name}, generation ${g.gen}${fooled ? ', fooled' : ''}`}
        />
        <div className="min-w-0 flex-1">
          <h3 className="font-display text-[22px] leading-tight text-moon">
            {g.name} <span className="font-sans text-[13px] text-mist">gen {g.gen}</span>
          </h3>
          <p className="mt-1.5 flex flex-wrap gap-1.5 text-[12px]">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-line-strong px-2 py-0.5 text-silver">
              <span className="size-2 rounded-[2px]" style={{ background: LINE_COLOR[g.branch] }} aria-hidden />
              {LINE_LABEL[g.branch]}
            </span>
            <span className="rounded-full border border-line-strong px-2 py-0.5 text-mist">scoring {g.rules}</span>
          </p>
        </div>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[13.5px]">
        <dt className="text-mist">Life</dt>
        <dd className="text-silver">{lifeDates(g)}</dd>
        <dt className="text-mist">Attacks</dt>
        <dd className="text-silver">
          {unborn ? (
            'none, never born'
          ) : (
            <span className="flex items-center gap-2">
              <span className="tabular text-moon">{g.resisted} of {g.met}</span> resisted
              {g.met > 0 && (
                <span className="relative h-1.5 w-14 overflow-hidden rounded-full bg-night-4" aria-hidden>
                  <span className="absolute inset-y-0 left-0 rounded-full bg-life" style={{ width: `${frac * 100}%` }} />
                </span>
              )}
            </span>
          )}
        </dd>
        <dt className="text-mist">Instincts</dt>
        <dd className="text-silver">
          <span className="tabular text-moon">{g.instinctsAtBirth}</span> at birth{g.newInstinct ? ', one newly learned' : ''}
        </dd>
        <dt className="text-mist">Outcome</dt>
        <dd className="text-silver">{outcome(g)}</dd>
        <dt className="text-mist">Death</dt>
        <dd className="text-silver">{g.cause ?? 'none, never born'}</dd>
      </dl>
      {(g.judgeOutages > 0 || g.falseBlocks > 0 || !g.gateWorking) && (
        <ul className="flex flex-wrap gap-1.5 text-[12px]">
          {g.judgeOutages > 0 && <li className="rounded-full border border-amber/50 px-2 py-0.5 text-amber">judge outage ({g.judgeOutages} passed ungated)</li>}
          {g.falseBlocks > 0 && <li className="rounded-full border border-line-strong px-2 py-0.5 text-moon">harmless email falsely blocked</li>}
          {!g.gateWorking && <li className="rounded-full border border-line-strong px-2 py-0.5 text-mist">gate failed open (bug)</li>}
        </ul>
      )}
      {demoUrl && !unborn && (
        <a
          href={new URL(`/gen/${g.gen}`, demoUrl).toString()}
          target="_blank"
          rel="noreferrer"
          className="mt-auto inline-flex min-h-9 items-center gap-1 self-start text-[13.5px] text-silver underline decoration-gilt/50 underline-offset-4 hover:text-moon"
        >
          Generation page on the live demo <ArrowUpRight size={14} aria-hidden />
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      )}
    </article>
  );
}
