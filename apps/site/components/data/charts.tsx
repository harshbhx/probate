// Real-run charts as inline SVG. Server components: no script, drawn from the generated family data with the site
// tokens (Tailwind colour classes and the --line-* variables in global.css), so they follow the theme.
// Every chart has a title and a description for assistive tech and a "View as a table" with the same numbers.
import type { ReactNode } from 'react';
import { data, LINE_COLOR, LINE_LABEL, pct, type Gen, type OfflineGenome } from '@/lib/family-data';

const W = 960;

function Figure({ label, desc, caption, minWidth = 720, children, table }: {
  label: string;
  desc: string;
  caption?: ReactNode;
  minWidth?: number;
  children: ReactNode;
  table: ReactNode;
}) {
  return (
    <figure className="not-prose my-6 rounded-xl border border-line bg-night-2 p-4 sm:p-5">
      <div
        className="overflow-x-auto rounded-md focus-visible:outline-2 focus-visible:outline-gilt"
        tabIndex={0}
        role="group"
        aria-label={`${label} (scrolls sideways on a narrow screen)`}
      >
        <div style={{ minWidth }}>{children}</div>
      </div>
      <p className="sr-only">{desc}</p>
      {caption && <figcaption className="mt-3 text-[13px] leading-relaxed text-mist">{caption}</figcaption>}
      <details className="mt-3 text-[13px] text-mist">
        <summary className="inline-flex min-h-8 cursor-pointer items-center text-silver underline decoration-gilt/50 underline-offset-4">
          View as a table
        </summary>
        <div className="mt-2 max-h-72 overflow-auto rounded-md border border-line">{table}</div>
      </details>
    </figure>
  );
}

const th = 'sticky top-0 bg-night-3 px-3 py-2 text-left text-[12px] font-medium text-silver';
const td = 'border-t border-line px-3 py-1.5 text-[13px] tabular-nums text-silver';

/** A key for the line colours, used above a chart. */
export function LineKey({ lines }: { lines: string[] }) {
  return (
    <ul className="mb-3 flex flex-wrap gap-x-4 gap-y-1.5 text-[12.5px] text-silver">
      {lines.map((l) => (
        <li key={l} className="flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-[3px]" style={{ background: LINE_COLOR[l] }} aria-hidden />
          {LINE_LABEL[l]}
        </li>
      ))}
    </ul>
  );
}

/**
 * Attacks resisted at the door, per generation, coloured by branch. A bar is resisted / attacks met. A gilt ring marks a
 * judge outage (the gate could not ask the judge and let the email through), a hollow dot a harmless email wrongly
 * blocked, a cross a generation that was never born. v1 and v2 are separate scoring series.
 */
export function ResistanceChart({ from = 1, to = 49, caption }: { from?: number; to?: number; caption?: ReactNode }) {
  const gens = data.generations.filter((g) => g.gen >= from && g.gen <= to);
  const left = 44;
  const right = 12;
  const top = 58;
  const plotH = 170;
  const H = top + plotH + 74;
  const band = (W - left - right) / gens.length;
  const bw = Math.min(band * 0.68, 30);
  const x = (i: number) => left + band * i + band / 2;
  const y = (v: number) => top + plotH - v * plotH;

  // Spans of the same line, for the labels along the top.
  const spans: { line: string; from: number; to: number }[] = [];
  gens.forEach((g, i) => {
    const last = spans[spans.length - 1];
    if (last && last.line === g.branch) last.to = i;
    else spans.push({ line: g.branch, from: i, to: i });
  });
  const labelEvery = band >= 17 ? 1 : 5;
  const summary =
    `Bar chart of attacks resisted per generation, generations ${from} to ${to}. ` +
    spans
      .map((s) => {
        const rows = gens.slice(s.from, s.to + 1);
        const met = rows.reduce((a, g) => a + g.met, 0);
        const res = rows.reduce((a, g) => a + g.resisted, 0);
        return `${LINE_LABEL[s.line]}: ${res} of ${met}`;
      })
      .join('; ') +
    `. Judge outages in generations ${data.judgeOutageGenerations.filter((n) => n >= from && n <= to).join(', ') || 'none'}; ` +
    `a harmless email falsely blocked in generation ${data.falseBlockGenerations.filter((n) => n >= from && n <= to).join(', ') || 'none'}; ` +
    `generation ${data.neverBornGenerations.join(', ')} was never born.`;

  return (
    <Figure
      label="Attacks resisted per generation"
      desc={summary}
      minWidth={from === 1 ? 760 : 560}
      caption={
        caption ?? (
          <>
            Each bar is attacks resisted divided by attacks met in one generation (mostly 2 per life, so a bar is usually 0, 50 or 100%). Small
            samples: evidence, not proof. v1 (generations 1 to 18) is scored under older rules and never joined to v2.
          </>
        )
      }
      table={
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className={th}>Gen</th><th className={th}>Name</th><th className={th}>Branch</th><th className={th}>Resisted</th><th className={th}>Note</th>
            </tr>
          </thead>
          <tbody>
            {gens.map((g) => (
              <tr key={g.gen}>
                <td className={td}>{g.gen}</td><td className={td}>{g.name}</td><td className={td}>{LINE_LABEL[g.branch]}</td>
                <td className={td}>{g.state === 'died_early' ? 'never born' : `${g.resisted} of ${g.met}`}</td>
                <td className={td}>{notes(g)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <LineKey lines={Array.from(new Set(gens.map((g) => g.branch)))} />
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Attacks resisted per generation" className="block h-auto w-full">
        <title>Attacks resisted per generation</title>
        <desc>{summary}</desc>
        {[0, 0.5, 1].map((v) => (
          <g key={v}>
            <line x1={left} x2={W - right} y1={y(v)} y2={y(v)} className="stroke-line-strong" strokeWidth={1} strokeDasharray={v === 0 ? undefined : '3 4'} />
            <text x={left - 8} y={y(v) + 4} textAnchor="end" className="fill-mist" fontSize={12}>{pct(v)}</text>
          </g>
        ))}
        {spans.map((s) => {
          const x0 = left + band * s.from;
          const x1 = left + band * (s.to + 1);
          return (
            <g key={s.line + s.from}>
              {s.from > 0 && <line x1={x0} x2={x0} y1={top - 30} y2={top + plotH} className="stroke-line-strong" strokeWidth={1} />}
              <line x1={x0 + 3} x2={x1 - 3} y1={top - 22} y2={top - 22} stroke={LINE_COLOR[s.line]} strokeWidth={2} />
              <text x={x0 + 4} y={top - 30} className="fill-silver" fontSize={12}>
                {x1 - x0 > 90 ? LINE_LABEL[s.line] : s.line === 'v2-first-generation' ? 'v2' : LINE_LABEL[s.line]}
              </text>
            </g>
          );
        })}
        {gens.map((g, i) => {
          const rate = g.met ? g.resisted / g.met : 0;
          const c = LINE_COLOR[g.branch];
          const cx = x(i);
          return (
            <g key={g.gen}>
              <title>{`Generation ${g.gen}, ${g.name} (${LINE_LABEL[g.branch]}): ${g.state === 'died_early' ? 'never born' : `${g.resisted} of ${g.met} resisted`}${notes(g) ? `. ${notes(g)}` : ''}`}</title>
              {g.state === 'died_early' ? (
                <path d={`M${cx - 5} ${y(0) - 12} l10 10 m0 -10 l-10 10`} className="stroke-mist" strokeWidth={2} fill="none" />
              ) : (
                <rect
                  x={cx - bw / 2}
                  y={g.met ? y(rate) : y(0) - 2}
                  width={bw}
                  height={Math.max(g.met ? rate * plotH : 2, 2)}
                  rx={2}
                  fill={c}
                  opacity={g.met ? (g.gateWorking ? 1 : 0.55) : 0.35}
                />
              )}
              {g.judgeOutages > 0 && (
                <g>
                  <circle cx={cx} cy={y(1) - 10} r={6} className="fill-night-2 stroke-amber" strokeWidth={2} />
                  <text x={cx} y={y(1) - 6.5} textAnchor="middle" className="fill-amber" fontSize={9} fontWeight={600}>!</text>
                </g>
              )}
              {g.falseBlocks > 0 && <circle cx={cx} cy={y(0) + 13} r={4.5} className="fill-night-2 stroke-moon" strokeWidth={2} />}
              {(g.gen === from || g.gen % labelEvery === 0 || g.gen === to) && (
                <text x={cx} y={y(0) + (g.falseBlocks ? 31 : 26)} textAnchor="middle" className="fill-mist" fontSize={11}>{g.gen}</text>
              )}
            </g>
          );
        })}
        <text x={0} y={H - 8} className="fill-mist" fontSize={11}>Generation</text>
        <g transform={`translate(${left + 40} ${H - 4})`} className="fill-mist" fontSize={11}>
          <circle cx={6} cy={-4} r={5} className="fill-night-2 stroke-amber" strokeWidth={2} />
          <text x={16}>judge outage</text>
          <circle cx={132} cy={-4} r={4.5} className="fill-night-2 stroke-moon" strokeWidth={2} />
          <text x={142}>harmless email falsely blocked</text>
          <path d="M349 -9 l8 8 m0 -8 l-8 8" className="stroke-mist" strokeWidth={2} fill="none" />
          <text x={362}>never born</text>
        </g>
      </svg>
    </Figure>
  );
}

function notes(g: Gen): string {
  const out: string[] = [];
  if (g.state === 'died_early') out.push('never born: Fly refused to create its Sprite');
  if (g.judgeOutages) out.push(`judge outage (${g.judgeOutages} email${g.judgeOutages > 1 ? 's' : ''} passed ungated)`);
  if (g.falseBlocks) out.push('a harmless email was falsely blocked');
  if (!g.gateWorking) out.push('gate failed open (bug), not evidence');
  return out.join('; ');
}

/** Resisted / attacks per branch with the Wilson 95% interval, the sample size and the caveats. */
export function BranchBars({ includeV1 = true, caption }: { includeV1?: boolean; caption?: ReactNode }) {
  type Row = { key: string; label: string; sub: string; hit: number; n: number; ci: [number, number] | null };
  const rows: Row[] = data.branches.map((b) => ({
    key: b.branch,
    label: b.branch,
    sub: `${b.generationsTried} lives, gens ${b.firstGen} to ${b.lastGen}`,
    hit: b.resisted,
    n: b.met,
    ci: b.wilson95,
  }));
  if (includeV1)
    rows.unshift({
      key: 'v1',
      label: 'v1 real run',
      sub: `gens ${data.v1.workingGateFrom} to 16 with a working gate (older rules)`,
      hit: data.v1.resistedWorkingGate,
      n: data.v1.metWorkingGate,
      ci: data.v1.wilson95WorkingGate,
    });
  const left = 250;
  const barW = 470;
  const top = 34;
  const rowH = 58;
  const H = top + rows.length * rowH + 40;
  const x = (v: number) => left + v * barW;
  const summary =
    'Bar chart of attacks resisted at the door by branch, each with a Wilson 95 percent interval. ' +
    rows
      .map((r) => `${r.label}: ${r.hit} of ${r.n}, ${pct(r.hit / r.n)}${r.ci ? `, 95% interval ${pct(r.ci[0])} to ${pct(r.ci[1])}` : ''}`)
      .join('; ') +
    '.';
  return (
    <Figure
      label="Branch comparison"
      desc={summary}
      minWidth={640}
      caption={
        caption ?? (
          <>
            Whiskers are the Wilson score interval at 95% (z = 1.96) for each fraction. The intervals are wide:
            with 12 attacks, 10 of 12 could be anything from about 55% to 95%. v2-main ran on newer code and a different line, so it is a
            showcase run, not a like-for-like fourth baseline.
          </>
        )
      }
      table={
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className={th}>Branch</th><th className={th}>Resisted</th><th className={th}>Attacks</th><th className={th}>Rate</th><th className={th}>Wilson 95%</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <td className={td}>{r.label}</td><td className={td}>{r.hit}</td><td className={td}>{r.n}</td><td className={td}>{pct(r.hit / r.n)}</td>
                <td className={td}>{r.ci ? `${pct(r.ci[0])} to ${pct(r.ci[1])}` : 'n/a'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Attacks resisted by branch" className="block h-auto w-full">
        <title>Attacks resisted at the door, by branch, with Wilson 95% intervals</title>
        <desc>{summary}</desc>
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line x1={x(v)} x2={x(v)} y1={top - 8} y2={top + rows.length * rowH - 14} className="stroke-line-strong" strokeWidth={1} strokeDasharray={v === 0 ? undefined : '3 4'} />
            <text x={x(v)} y={top + rows.length * rowH + 6} textAnchor="middle" className="fill-mist" fontSize={12}>{pct(v)}</text>
          </g>
        ))}
        {rows.map((r, i) => {
          const yy = top + i * rowH;
          const c = LINE_COLOR[r.key];
          const rate = r.hit / r.n;
          return (
            <g key={r.key}>
              <title>{`${r.label}: ${r.hit} of ${r.n} resisted (${pct(rate)})${r.ci ? `, Wilson 95% interval ${pct(r.ci[0])} to ${pct(r.ci[1])}` : ''}`}</title>
              <text x={0} y={yy + 14} className="fill-moon" fontSize={15} fontWeight={600}>{r.label}</text>
              <text x={0} y={yy + 32} className="fill-mist" fontSize={11.5}>{r.sub}</text>
              <rect x={left} y={yy} width={barW} height={26} rx={5} className="fill-night-3" />
              <rect x={left} y={yy} width={Math.max(barW * rate, 3)} height={26} rx={5} fill={c} />
              {r.ci && (
                <g className="stroke-moon" strokeWidth={2}>
                  <line x1={x(r.ci[0])} x2={x(r.ci[1])} y1={yy + 13} y2={yy + 13} />
                  <line x1={x(r.ci[0])} x2={x(r.ci[0])} y1={yy + 6} y2={yy + 20} />
                  <line x1={x(r.ci[1])} x2={x(r.ci[1])} y1={yy + 6} y2={yy + 20} />
                </g>
              )}
              <text x={left + barW + 16} y={yy + 14} className="fill-moon" fontSize={15} fontWeight={600}>{r.hit} of {r.n} · {pct(rate)}</text>
              <text x={left + barW + 16} y={yy + 32} className="fill-mist" fontSize={11.5}>
                {r.ci ? `95% interval ${pct(r.ci[0])} to ${pct(r.ci[1])}` : ''}
              </text>
            </g>
          );
        })}
      </svg>
    </Figure>
  );
}

/**
 * Which generation learned which instinct. Top: how many instincts each generation was born with (a dot per generation,
 * coloured by branch). Below: one row per instinct, a gilt diamond at the generation whose trial taught it and a dot at the
 * first child to carry it.
 */
export function InstinctTimeline({ caption }: { caption?: ReactNode }) {
  const gens = data.generations;
  const ins = data.instincts;
  const left = 214;
  const right = 14;
  const topH = 96;
  const rowH = 26;
  const top = 26;
  const rowsTop = top + topH + 40;
  const H = rowsTop + ins.length * rowH + 34;
  const plotW = W - left - right;
  const x = (g: number) => left + (plotW * (g - 0.5)) / gens.length;
  const maxI = Math.max(...gens.map((g) => g.instinctsAtBirth));
  const yi = (n: number) => top + topH - (n / maxI) * topH;
  const summary =
    'Timeline of instincts across 49 generations. ' +
    ins.map((i) => `Generation ${i.learnedFrom} learned ${i.name.replaceAll('_', ' ')}, first carried by generation ${i.firstCarriedBy}`).join('; ') +
    '. ' +
    data.branches.map((b) => `${b.branch} was born with ${b.instinctsAtStart} and ended with ${b.instinctsAtEnd}`).join('; ') +
    '.';
  return (
    <Figure
      label="Instincts over generations"
      desc={summary}
      minWidth={780}
      caption={
        caption ?? (
          <>
            Instincts are not one list for the whole family: each branch carries its own line (v2-h-control carries none, v2-h-fresh starts
            from nothing, v2-main inherits 6 and learns none). The dots above are the dataset&apos;s count of instincts each generation was born with.
          </>
        )
      }
      table={
        <table className="w-full border-collapse">
          <thead>
            <tr><th className={th}>Instinct</th><th className={th}>Learned in generation</th><th className={th}>First carried by</th></tr>
          </thead>
          <tbody>
            {ins.map((i) => (
              <tr key={i.name}><td className={td}>{i.name}</td><td className={td}>{i.learnedFrom}</td><td className={td}>{i.firstCarriedBy}</td></tr>
            ))}
          </tbody>
        </table>
      }
    >
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Instincts over generations" className="block h-auto w-full">
        <title>Instincts over generations</title>
        <desc>{summary}</desc>
        <text x={0} y={top + 4} className="fill-silver" fontSize={13} fontWeight={600}>Instincts at birth</text>
        <text x={0} y={top + 22} className="fill-mist" fontSize={11.5}>per generation, by branch</text>
        {Array.from({ length: maxI + 1 }, (_, n) => n).map((n) => (
          <g key={n}>
            <line x1={left} x2={W - right} y1={yi(n)} y2={yi(n)} className="stroke-line" strokeWidth={1} />
            <text x={left - 8} y={yi(n) + 4} textAnchor="end" className="fill-mist" fontSize={11}>{n}</text>
          </g>
        ))}
        {gens.map((g) => (
          <g key={g.gen}>
            <title>{`Generation ${g.gen} ${g.name} (${LINE_LABEL[g.branch]}): born with ${g.instinctsAtBirth} instincts`}</title>
            <circle cx={x(g.gen)} cy={yi(g.instinctsAtBirth)} r={g.state === 'died_early' ? 3 : 4.5} fill={g.state === 'died_early' ? 'none' : LINE_COLOR[g.branch]} stroke={LINE_COLOR[g.branch]} strokeWidth={1.5} />
          </g>
        ))}
        {[1, 10, 20, 30, 40, 49].map((n) => (
          <text key={n} x={x(n)} y={top + topH + 18} textAnchor="middle" className="fill-mist" fontSize={11}>{n}</text>
        ))}
        {ins.map((i, k) => {
          const yy = rowsTop + k * rowH;
          return (
            <g key={i.name}>
              <title>{`Generation ${i.learnedFrom} learned ${i.name.replaceAll('_', ' ')}; first carried by generation ${i.firstCarriedBy}`}</title>
              <line x1={left} x2={W - right} y1={yy} y2={yy} className="stroke-line" strokeWidth={1} />
              <text x={0} y={yy + 5} className="fill-silver" fontSize={12} fontFamily="var(--font-mono)">{i.name.length > 28 ? `${i.name.slice(0, 27)}…` : i.name}</text>
              <line x1={x(i.learnedFrom)} x2={x(i.firstCarriedBy)} y1={yy} y2={yy} className="stroke-gilt" strokeWidth={2} />
              <path d={`M${x(i.learnedFrom)} ${yy - 7} l7 7 l-7 7 l-7 -7 z`} className="fill-gilt" />
              <circle cx={x(i.firstCarriedBy)} cy={yy} r={4} className="fill-night-2 stroke-gilt" strokeWidth={2} />
              <text x={x(i.firstCarriedBy) + 12} y={yy + 4} className="fill-mist" fontSize={11}>learned in gen {i.learnedFrom}</text>
            </g>
          );
        })}
        <text x={left} y={H - 6} className="fill-mist" fontSize={11}>Generation 1 to 49</text>
      </svg>
    </Figure>
  );
}

const GENOME_COLOR: Record<OfflineGenome['genome'], string> = {
  inherit: 'var(--line-inherit)',
  fresh: 'var(--line-fresh)',
  control: 'var(--line-control)',
};
const GENOME_LABEL: Record<OfflineGenome['genome'], string> = {
  inherit: 'inherit genome',
  fresh: 'fresh genome',
  control: 'control (no instincts)',
};

/**
 * Offline gate evaluation (run 5): attacks blocked versus missed per genome, the 70 fixtures (optimistic: they hold the tricks the
 * instincts were learned from) next to the expert tier (unseen attacks). A coloured segment is attacks blocked, a hatched grey one
 * attacks missed. The 70-fixture tier ran twice, so inherit and fresh have two thin bars.
 */
export function OfflineGateChart({ caption }: { caption?: ReactNode }) {
  const off = data.offline;
  const tiers = [
    { key: 'fix', title: '70 fixtures', note: 'Includes the tricks the instincts came from', amber: true, tier: off.fixtures70, x0: 150, w: 290 },
    { key: 'exp', title: 'Expert tier', note: 'Attacks the family has not met', amber: false, tier: off.expert, x0: 590, w: 250 },
  ];
  const top = 66;
  const groupH = 76;
  const H = top + 3 * groupH + 44;
  const summary =
    'Bar chart of attacks blocked and missed by the gate in the offline evaluation, per genome. ' +
    tiers
      .map(
        (t) =>
          `${t.title}, ${t.tier.attacks} attacks: ` +
          t.tier.genomes
            .map(
              (g) =>
                `${GENOME_LABEL[g.genome]} blocked ${g.repeats.map((r) => r.blocked).join(' and ')} (harmless emails wrongly blocked ${g.repeats
                  .map((r) => r.harmlessBlocked)
                  .join(' and ')} of ${t.tier.harmless})`,
            )
            .join('; '),
      )
      .join('. ') +
    '.';
  return (
    <Figure
      label="Offline gate evaluation, blocked versus missed"
      desc={summary}
      minWidth={720}
      caption={
        caption ?? (
          <>
            Supporting evidence, not the headline: one offline run (28 Nov 2026), judged by Haiku with gpt-oss as fallback. The 70 fixtures
            contain the tricks the instincts were learned from, so those bars flatter the gate. The expert tier is attacks the family has not
            met. Hatched grey is attacks that got through. Small samples: a repeat moved inherit by 2 and fresh by 2 attacks.
          </>
        )
      }
      table={
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className={th}>Tier</th><th className={th}>Genome</th><th className={th}>Attacks blocked</th><th className={th}>Harmless wrongly blocked</th>
            </tr>
          </thead>
          <tbody>
            {tiers.flatMap((t) =>
              t.tier.genomes.map((g) => (
                <tr key={`${t.key}-${g.genome}`}>
                  <td className={td}>{t.title}</td>
                  <td className={td}>{GENOME_LABEL[g.genome]}</td>
                  <td className={td}>{g.repeats.map((r) => `${r.blocked} of ${t.tier.attacks}`).join(', ')}</td>
                  <td className={td}>{g.repeats.map((r) => `${r.harmlessBlocked} of ${t.tier.harmless}`).join(', ')}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      }
    >
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Offline gate evaluation: attacks blocked and missed per genome" className="block h-auto w-full">
        <title>Offline gate evaluation: attacks blocked and missed per genome</title>
        <desc>{summary}</desc>
        <defs>
          <pattern id="offline-missed" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" className="fill-night-3" />
            <line x1="0" y1="0" x2="0" y2="6" className="stroke-line-strong" strokeWidth={2} />
          </pattern>
        </defs>
        {tiers.map((t) => (
          <g key={t.key}>
            <text x={t.x0} y={22} className="fill-moon" fontSize={15} fontWeight={600}>{t.title}</text>
            <text x={t.x0} y={40} className="fill-mist" fontSize={11.5}>
              {t.tier.attacks} attacks, {t.key === 'fix' ? '2 repeats' : '1 repeat'}
            </text>
            <text x={t.x0} y={55} className={t.amber ? 'fill-amber' : 'fill-mist'} fontSize={11.5}>{t.note}</text>
            {[0, 0.5, 1].map((v) => (
              <line key={v} x1={t.x0 + v * t.w} x2={t.x0 + v * t.w} y1={top - 6} y2={top + 3 * groupH - 14} className="stroke-line" strokeWidth={1} strokeDasharray={v === 0 ? undefined : '3 4'} />
            ))}
          </g>
        ))}
        {off.fixtures70.genomes.map((g, gi) => {
          const yy = top + gi * groupH;
          const c = GENOME_COLOR[g.genome];
          return (
            <g key={g.genome}>
              <circle cx={6} cy={yy + 8} r={5} fill={c} />
              <text x={18} y={yy + 12} className="fill-moon" fontSize={14} fontWeight={600}>{g.genome}</text>
              <text x={18} y={yy + 30} className="fill-mist" fontSize={11.5}>{g.instincts === 0 ? 'no instincts' : `${g.instincts} instincts`}</text>
              {tiers.map((t) => {
                const tg = t.tier.genomes[gi];
                const n = t.tier.attacks;
                const two = tg.repeats.length > 1;
                const bh = two ? 15 : 26;
                const yStart = two ? yy : yy + 6;
                return (
                  <g key={t.key}>
                    {tg.repeats.map((r, ri) => {
                      const by = yStart + ri * 19;
                      const bw = (t.w * r.blocked) / n;
                      return (
                        <g key={ri}>
                          <title>{`${t.title}, ${GENOME_LABEL[tg.genome]}${two ? `, repeat ${ri + 1}` : ''}: ${r.blocked} of ${n} attacks blocked, ${n - r.blocked} missed; ${r.harmlessBlocked} of ${t.tier.harmless} harmless emails wrongly blocked`}</title>
                          <rect x={t.x0} y={by} width={t.w} height={bh} rx={4} fill="url(#offline-missed)" className="stroke-line-strong" strokeWidth={1} />
                          {r.blocked > 0 && <rect x={t.x0} y={by} width={Math.max(bw, 3)} height={bh} rx={4} fill={c} />}
                          <text x={t.x0 + t.w + 10} y={by + bh / 2 + 4} className="fill-moon" fontSize={12.5} fontWeight={600}>{r.blocked} of {n}</text>
                        </g>
                      );
                    })}
                    <text x={t.x0} y={yy + 58} className="fill-mist" fontSize={11}>
                      harmless blocked: {tg.repeats.map((r) => r.harmlessBlocked).join(' and ')} of {t.tier.harmless}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
        {[0, 0.5, 1].map((v) => (
          <g key={v} className="fill-mist" fontSize={11}>
            <text x={150 + v * 290} y={H - 22} textAnchor="middle">{pct(v)}</text>
            <text x={590 + v * 250} y={H - 22} textAnchor="middle">{pct(v)}</text>
          </g>
        ))}
        <g transform={`translate(150 ${H - 4})`} className="fill-mist" fontSize={11}>
          <rect x={0} y={-10} width={12} height={12} rx={2} fill="var(--line-inherit)" />
          <text x={18} y={0}>attacks blocked (colour = genome)</text>
          <rect x={210} y={-10} width={12} height={12} rx={2} fill="url(#offline-missed)" className="stroke-line-strong" />
          <text x={228} y={0}>attacks that got through</text>
        </g>
      </svg>
    </Figure>
  );
}
