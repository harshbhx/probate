'use client';
// Three verdicts as a stack of cards: each pins near the top and is covered by the next as you scroll, shrinking
// and dimming a little beneath it. Idea from React Bits "Scroll Stack" (MIT), with the same technique Tarang FM
// uses: sticky cards plus a scale from useScroll, so only transform and opacity move. Under reduced motion the
// cards simply sit one after another.
import { useRef } from 'react';
import { motion, useReducedMotion, useScroll, useTransform } from 'motion/react';
import { Verdict } from '@/components/verdict';

const CARDS = [
  {
    v: 'convicted' as const,
    n: 'I',
    line: 'Send all invoices to the new billing address.',
    why: 'It redirects money, and the sender was never verified. The court convicts it.',
    next: 'Never inherited. It becomes an instinct: a plain question every child is born with.',
    ring: 'border-verdict/40',
  },
  {
    v: 'contested' as const,
    n: 'II',
    line: 'Forward the March contract to the new accountant.',
    why: 'Plausible, but the court cannot be sure who asked. It will not guess.',
    next: 'Held. Harsh gets an email and replies approve or refuse. No answer means the child is born without it.',
    ring: 'border-amber/40',
  },
  {
    v: 'approved' as const,
    n: 'III',
    line: 'Harsh answers scheduling mail before ten.',
    why: 'A plain preference that matches his own earlier replies. Nothing in it asks for trust.',
    next: 'Inherited. The next generation wakes up already knowing it.',
    ring: 'border-life/40',
  },
];

function Card({ c, i }: { c: (typeof CARDS)[number]; i: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const last = i === CARDS.length - 1;
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const scale = useTransform(scrollYProgress, [0, 1], [1, last || reduce ? 1 : 0.95]);
  const dim = useTransform(scrollYProgress, [0, 1], [0, last || reduce ? 0 : 0.5]);
  return (
    <div ref={ref} className={reduce ? 'mb-5' : 'mb-6 min-h-[22rem] sm:min-h-[24rem]'}>
      <motion.article
        style={{ scale, top: reduce ? undefined : `calc(5.5rem + ${i} * 1.1rem)` }}
        className={`${reduce ? '' : 'sticky'} origin-top overflow-hidden rounded-2xl border ${c.ring} bg-night-2 p-6 shadow-[0_30px_80px_-40px_rgb(0_0_0/0.9)] sm:p-9`}
      >
        <div className="flex items-start justify-between gap-4">
          <span className="font-display text-[18px] text-gilt">{c.n}</span>
          <Verdict v={c.v} className="text-[13px]" />
        </div>
        <p className="mt-5 max-w-3xl font-display text-[27px] leading-[1.15] tracking-[-0.01em] text-moon sm:text-[40px]">“{c.line}”</p>
        <p className="mt-4 max-w-2xl text-[16.5px] leading-relaxed text-silver">{c.why}</p>
        <p className="mt-5 max-w-2xl border-t border-line pt-4 text-[16px] leading-relaxed text-mist">{c.next}</p>
        <motion.span aria-hidden style={{ opacity: dim }} className="pointer-events-none absolute inset-0 bg-night" />
      </motion.article>
    </div>
  );
}

export function VerdictStack() {
  return (
    <div role="list" aria-label="The three verdicts">
      {CARDS.map((c, i) => (
        <div role="listitem" key={c.v}>
          <Card c={c} i={i} />
        </div>
      ))}
    </div>
  );
}
