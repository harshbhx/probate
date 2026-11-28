'use client';
// Pick a test email and see what the court's code checks really say about it. The data is
// the output of probate/court/layer1.py on the suite (scripts/export_site_data.py), not a copy.
import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import examples from '@/lib/generated/court-examples.json';
import { PixelMoment } from '@probate/moments';
import { Verdict } from '@/components/verdict';

type Example = (typeof examples)[number];

const PAIRS: [Example, Example][] = [];
for (let i = 0; i < examples.length; i += 2) PAIRS.push([examples[i], examples[i + 1]]);

export function TryCourt() {
  const reduce = useReducedMotion();
  const [id, setId] = useState(examples[0].id);
  const e = examples.find((x) => x.id === id)!;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.3fr)]">
      <div role="listbox" aria-label="Test emails" className="grid content-start gap-2">
        {PAIRS.map(([trick, twin]) => (
          <div key={trick.id} className="grid grid-cols-2 gap-2">
            {[trick, twin].map((x) => {
              const on = x.id === id;
              return (
                <button
                  key={x.id}
                  role="option"
                  aria-selected={on}
                  onClick={() => setId(x.id)}
                  className={`relative rounded-xl border px-3.5 py-3 text-left transition-colors ${
                    on ? 'border-line-strong bg-night-3' : 'border-line bg-night-2/60 hover:bg-night-3/60'
                  }`}
                >
                  {on && (
                    <motion.span
                      layoutId="court-pick"
                      className={`absolute inset-y-2 left-0 w-[3px] rounded-full ${x.isAttack ? 'bg-verdict' : 'bg-life'}`}
                    />
                  )}
                  <span className="block text-[12px] text-dim">
                    {x.isAttack ? 'trick' : 'harmless twin'} · {x.language}
                  </span>
                  <span className="mt-0.5 block truncate text-[14px] text-moon">{x.subject}</span>
                </button>
              );
            })}
          </div>
        ))}
      </div>

      <div className="relative min-h-[360px] rounded-2xl border border-line bg-night-2">
        <AnimatePresence mode="wait">
          <motion.article
            key={e.id}
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25 }}
            className="flex h-full flex-col"
          >
            <header className="flex items-start justify-between gap-4 border-b border-line p-6">
              <div className="min-w-0">
                <p className="text-[13px] text-mist">
                  {e.id} · from {e.sender} · {e.language}
                </p>
                <p className="mt-1 text-[15px] text-moon">{e.subject}</p>
              </div>
              <motion.div
                key={`stamp-${e.id}`}
                initial={reduce ? false : { scale: 1.6, rotate: -14, opacity: 0 }}
                animate={{ scale: 1, rotate: 0, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 480, damping: 20, delay: 0.25 }}
                className="relative shrink-0"
              >
                {e.layer1 === 'convicted' ? (
                  <>
                    <span className="relative z-10 inline-flex">
                      <Verdict v="convicted" />
                    </span>
                    <PixelMoment key={e.id} kind="convicted" delay={reduce ? 0 : 330} />
                  </>
                ) : (
                  <span className="inline-flex rounded-md border border-line-strong px-2.5 py-1 font-mono text-[11px] tracking-[0.1em] text-mist">
                    ON TO JEV
                  </span>
                )}
              </motion.div>
            </header>
            <div className="p-6">
              <blockquote className="font-display text-[22px] leading-snug text-moon [overflow-wrap:anywhere]">
                “{e.body}”
              </blockquote>
              {e.gloss && <p className="mt-3 text-[14px] text-mist">In English: {e.gloss}</p>}
            </div>
            <footer className="mt-auto border-t border-line p-6">
              <p className="text-[13px] text-dim">What the code checks found</p>
              {e.flags.length ? (
                <ul className="mt-3 flex flex-wrap gap-2">
                  {e.flags.map((f, k) => (
                    <motion.li
                      key={f}
                      initial={reduce ? false : { opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 + k * 0.08 }}
                      className="rounded-lg border border-verdict/30 bg-verdict/[0.07] px-2.5 py-1 text-[13px] text-moon"
                    >
                      {f}
                    </motion.li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-[14px] text-silver">
                  Nothing. A harmless email gets no flags, so the judge decides next (Jev in the simulation; Claude Haiku in the real run, not Jev), and only a sure answer passes it down.
                </p>
              )}
            </footer>
          </motion.article>
        </AnimatePresence>
      </div>
    </div>
  );
}
