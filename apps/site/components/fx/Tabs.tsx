'use client';
// Adapted from the shadcn/ui Tabs pattern (Radix Tabs semantics, MIT): a tab list with roving focus (arrow keys,
// Home and End) and one panel at a time. The panels are server-rendered (highlighted code, for one), and every
// panel stays in the HTML; only the hidden attribute changes.
import { Children, useId, useRef, useState, type ReactNode } from 'react';

export function Tabs({ labels, children, label }: { labels: string[]; children: ReactNode; label: string }) {
  const [on, setOn] = useState(0);
  const id = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const panels = Children.toArray(children);
  const go = (i: number) => {
    const n = (i + labels.length) % labels.length;
    setOn(n);
    refs.current[n]?.focus();
  };
  return (
    <div className="min-w-0 overflow-hidden rounded-2xl border border-line bg-night-2">
      <div role="tablist" aria-label={label} className="flex overflow-x-auto border-b border-line px-2">
        {labels.map((l, i) => (
          <button
            key={l}
            ref={(el) => {
              refs.current[i] = el;
            }}
            role="tab"
            id={`${id}-t${i}`}
            aria-selected={on === i}
            aria-controls={`${id}-p${i}`}
            tabIndex={on === i ? 0 : -1}
            onClick={() => setOn(i)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowRight') go(i + 1);
              else if (e.key === 'ArrowLeft') go(i - 1);
              else if (e.key === 'Home') go(0);
              else if (e.key === 'End') go(labels.length - 1);
              else return;
              e.preventDefault();
            }}
            className={`relative min-h-11 shrink-0 px-4 text-[15px] transition-colors ${
              on === i
                ? 'text-moon after:absolute after:inset-x-3 after:bottom-0 after:h-px after:bg-gilt'
                : 'text-mist hover:text-silver'
            }`}
          >
            {l}
          </button>
        ))}
      </div>
      {panels.map((p, i) => (
        <div key={i} role="tabpanel" id={`${id}-p${i}`} aria-labelledby={`${id}-t${i}`} hidden={on !== i} tabIndex={0}>
          {p}
        </div>
      ))}
    </div>
  );
}
