'use client';
// A tall section pins one statement mid-screen and lights it word by word as you scroll through it. Idea from
// Magic UI "Text Reveal" (MIT), via the same pattern in Tarang FM. The words are real text the whole time (only
// opacity moves); under reduced motion the whole statement is simply shown.
import { useRef } from 'react';
import { motion, useReducedMotion, useScroll, useTransform, type MotionValue } from 'motion/react';

function Word({ progress, range, children, accent }: { progress: MotionValue<number>; range: [number, number]; children: string; accent: boolean }) {
  const opacity = useTransform(progress, range, [0.16, 1]);
  return (
    <motion.span style={{ opacity }} className={accent ? 'text-gilt' : undefined}>
      {children}
    </motion.span>
  );
}

export function TextReveal({ id, text, accent = [], run = 1.6, className = '' }: { id?: string; text: string; accent?: string[]; run?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 0.85', 'end 0.55'] });
  const lit = new Set(accent.map((w) => w.toLowerCase()));
  const words = text.split(' ');
  const key = (w: string) => w.toLowerCase().replace(/[^a-z]/g, '');
  return (
    <div id={id} ref={ref} style={{ height: reduce ? 'auto' : `${run * 100}vh` }} className="relative">
      <div className={`${reduce ? '' : 'sticky top-0 flex h-screen items-center'} mx-auto max-w-6xl px-5 py-16 sm:px-6 ${className}`}>
        <p className="max-w-5xl font-display text-[34px] font-[420] leading-[1.14] tracking-[-0.02em] text-moon sm:text-[52px] lg:text-[68px]">
          {words.map((w, i) =>
            reduce ? (
              <span key={i} className={lit.has(key(w)) ? 'text-gilt' : undefined}>
                {w}{' '}
              </span>
            ) : (
              <Word key={i} progress={scrollYProgress} range={[i / words.length, (i + 1) / words.length]} accent={lit.has(key(w))}>
                {`${w} `}
              </Word>
            ),
          )}
        </p>
      </div>
    </div>
  );
}
