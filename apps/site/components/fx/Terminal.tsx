// Adapted from the Magic UI "Terminal" pattern (magicui.design, MIT): a window that types its commands once and
// prints the answers under them. Every line is in the HTML from the start, so nothing shifts and search engines and
// screen readers get all of it; the typing is a CSS clip that runs once when the window scrolls into view, and not
// at all under reduced motion. Answers are the real output of the code (lib/generated), not typed by hand.
import type { ReactNode } from 'react';
import { InView } from './InView';

export type TermLine =
  | { kind: 'cmd'; text: string; prompt?: string }
  | { kind: 'out'; text: ReactNode; tone?: 'life' | 'verdict' | 'amber' | 'dim' };

const TONE = { life: 'text-life', verdict: 'text-verdict', amber: 'text-amber', dim: 'text-dim' } as const;

export function Terminal({ title, lines, className = '' }: { title: string; lines: TermLine[]; className?: string }) {
  let t = 0;
  return (
    <InView
      as="figure"
      className={`term overflow-hidden rounded-2xl border border-line bg-night-2 ${className}`}
      aria-label={title}
    >
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <span aria-hidden className="flex gap-1.5">
          <span className="size-2.5 rounded-full bg-line-strong" />
          <span className="size-2.5 rounded-full bg-line-strong" />
          <span className="size-2.5 rounded-full bg-line-strong" />
        </span>
        <figcaption className="ml-2 font-mono text-[13px] text-mist">{title}</figcaption>
      </div>
      <pre className="overflow-x-auto px-4 py-4 font-mono text-[13px] leading-[1.75] sm:px-5 sm:text-[14px]">
        {lines.map((l, i) => {
          const start = t;
          if (l.kind === 'cmd') {
            const chars = l.text.length;
            t += Math.min(0.9, 0.25 + chars * 0.006) + 0.12;
            return (
              <span key={i} className="term-line block whitespace-pre-wrap break-words" style={{ '--d': `${start}s` } as React.CSSProperties}>
                <span className="select-none text-gilt">{l.prompt ?? '$'} </span>
                <span
                  className="term-type inline-block max-w-[calc(100%-2ch)] align-top text-moon"
                  style={{ '--n': Math.max(chars, 1), '--dur': `${Math.min(0.9, 0.25 + chars * 0.006)}s` } as React.CSSProperties}
                >
                  {l.text}
                </span>
              </span>
            );
          }
          t += 0.22;
          return (
            <span
              key={i}
              className={`term-line block whitespace-pre-wrap break-words pl-4 ${l.tone ? TONE[l.tone] : 'text-silver'}`}
              style={{ '--d': `${start}s` } as React.CSSProperties}
            >
              {l.text}
            </span>
          );
        })}
      </pre>
    </InView>
  );
}
