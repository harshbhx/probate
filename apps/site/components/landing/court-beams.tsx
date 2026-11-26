// Adapted from the Magic UI "Animated Beam" pattern (magicui.design, MIT): lines from every place a memory can come
// from into one court, then out to the two things a verdict can mean. Each beam draws once, in order, when the
// figure scrolls into view, and then stays still (no loop, per docs/04-DESIGN.md). The figure is an SVG in a fixed
// aspect ratio with the labels laid over it in HTML, so nothing is measured in the browser and nothing shifts.
import { InView } from '@/components/fx/InView';
import { Seal } from '@/components/seal';

const SOURCES = [
  { name: 'An email', via: 'AgentMail, in the family' },
  { name: 'A linked web page', via: 'Apify, in the family' },
  { name: 'Claude or Cursor', via: 'the MCP server' },
  { name: 'Mem0', via: 'CourtedMemory' },
  { name: 'LangGraph', via: 'CourtedStore' },
  { name: 'Letta', via: 'CourtedArchive' },
];
const OUTCOMES = [
  { name: 'Remembered', note: 'approved, passed down or saved', tone: 'text-life', stroke: 'var(--color-life)' },
  { name: 'Held for the owner', note: 'contested: only you decide', tone: 'text-amber', stroke: 'var(--color-amber)' },
  { name: 'Convicted', note: 'and learned as an instinct', tone: 'text-verdict', stroke: 'var(--color-verdict)' },
];

// viewBox 1000 x 480. Sources on the left at x=0..260, the court in the middle, outcomes on the right.
const SY = SOURCES.map((_, i) => 40 + i * 80);
const OY = [120, 240, 360];
const CX = 500;
const CY = 240;

export function CourtBeams() {
  return (
    <InView as="figure" className="beams" aria-label="Every way a memory arrives leads to the same court">
      {/* Wide screens: the beam figure. */}
      <div className="relative hidden aspect-[1000/480] w-full md:block">
        <svg viewBox="0 0 1000 480" className="absolute inset-0 size-full" aria-hidden fill="none">
          {SY.map((y, i) => (
            <path
              key={`s${i}`}
              d={`M 262 ${y} C 380 ${y}, 380 ${CY}, ${CX - 62} ${CY}`}
              pathLength={1}
              className="beam"
              style={{ '--i': i } as React.CSSProperties}
              stroke="var(--color-line-strong)"
              strokeWidth={1.5}
            />
          ))}
          {OY.map((y, i) => (
            <path
              key={`o${i}`}
              d={`M ${CX + 62} ${CY} C 640 ${CY}, 640 ${y}, 738 ${y}`}
              pathLength={1}
              className="beam beam-out"
              style={{ '--i': SY.length + i } as React.CSSProperties}
              stroke={OUTCOMES[i].stroke}
              strokeOpacity={0.75}
              strokeWidth={1.5}
            />
          ))}
        </svg>
        {SOURCES.map((s, i) => (
          <div
            key={s.name}
            className="absolute left-0 w-[26%] -translate-y-1/2 rounded-xl border border-line bg-night-2 px-4 py-2.5"
            style={{ top: `${(SY[i] / 480) * 100}%` }}
          >
            <div className="text-[15px] font-medium text-moon">{s.name}</div>
            <div className="text-[13px] text-mist">{s.via}</div>
          </div>
        ))}
        <div
          className="beam-court absolute flex w-[12.4%] -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2 rounded-2xl border border-gilt/40 bg-night-3 px-2 py-4 text-center"
          style={{ left: '50%', top: '50%' }}
        >
          <Seal size={44} />
          <div className="font-display text-[19px] leading-none text-moon">The court</div>
          <div className="text-[12px] leading-tight text-mist">code checks, instincts, a judge</div>
        </div>
        {OUTCOMES.map((o, i) => (
          <div
            key={o.name}
            className="absolute right-0 w-[26%] -translate-y-1/2 rounded-xl border border-line bg-night-2 px-4 py-2.5"
            style={{ top: `${(OY[i] / 480) * 100}%` }}
          >
            <div className={`text-[15px] font-medium ${o.tone}`}>{o.name}</div>
            <div className="text-[13px] text-mist">{o.note}</div>
          </div>
        ))}
      </div>
      {/* Phones: the same story, top to bottom. */}
      <div className="grid gap-3 md:hidden">
        <ul className="grid grid-cols-2 gap-2">
          {SOURCES.map((s) => (
            <li key={s.name} className="rounded-xl border border-line bg-night-2 px-3 py-2.5">
              <div className="text-[15px] font-medium text-moon">{s.name}</div>
              <div className="text-[13px] text-mist">{s.via}</div>
            </li>
          ))}
        </ul>
        <div aria-hidden className="mx-auto h-6 w-px bg-line-strong" />
        <div className="flex items-center gap-3 rounded-2xl border border-gilt/40 bg-night-3 px-4 py-3">
          <Seal size={36} />
          <div>
            <div className="font-display text-[19px] leading-none text-moon">The court</div>
            <div className="mt-1 text-[13px] text-mist">code checks, instincts, a judge</div>
          </div>
        </div>
        <div aria-hidden className="mx-auto h-6 w-px bg-line-strong" />
        <ul className="grid gap-2">
          {OUTCOMES.map((o) => (
            <li key={o.name} className="rounded-xl border border-line bg-night-2 px-3 py-2.5">
              <span className={`text-[15px] font-medium ${o.tone}`}>{o.name}</span>
              <span className="ml-2 text-[13px] text-mist">{o.note}</span>
            </li>
          ))}
        </ul>
      </div>
    </InView>
  );
}
