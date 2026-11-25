'use client';
// The living generation greets the visitor. Its eyes follow the pointer, and it says a few
// true things about its life, one at a time. Hovering it makes it happy; it never chases you.
import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { FamilyFace, type Mood } from '@probate/faces';

const LINES: { text: string; mood: Mood }[] = [
  { text: 'Hi, I’m Grace. I was born this morning.', mood: 'happy' },
  { text: 'I already know three tricks my family fell for.', mood: 'alert' },
  { text: 'My ancestor Ada was fooled by a fake invoice. None of us has fallen for one since.', mood: 'idle' },
  { text: 'At midnight I die, and a court reads my will.', mood: 'sleepy' },
  { text: 'Whatever it approves, my child inherits.', mood: 'happy' },
];

export function HeroFace() {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  const [hover, setHover] = useState(false);

  useEffect(() => {
    if (reduce) return;
    const id = setInterval(() => !document.hidden && setI((n) => (n + 1) % LINES.length), 4200);
    return () => clearInterval(id);
  }, [reduce]);

  const line = LINES[i];
  return (
    <div className="relative flex flex-col items-center">
      <div className="relative min-h-[92px] w-full max-w-[300px]" aria-live="polite">
        <AnimatePresence mode="wait">
          <motion.p
            key={i}
            initial={reduce ? false : { opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.3 }}
            className="relative rounded-2xl border border-line-strong bg-night-3/90 px-4 py-3 text-[15px] leading-snug text-moon shadow-[0_20px_50px_-20px_rgb(0_0_0/0.8)] backdrop-blur"
          >
            {line.text}
            <span
              aria-hidden
              className="absolute -bottom-[7px] left-1/2 size-3 -translate-x-1/2 rotate-45 border-b border-r border-line-strong bg-night-3"
            />
          </motion.p>
        </AnimatePresence>
      </div>
      <motion.div
        onPointerEnter={() => setHover(true)}
        onPointerLeave={() => setHover(false)}
        animate={reduce ? undefined : { y: [0, -6, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        className="mt-3"
      >
        <FamilyFace
          gen={7}
          life="alive"
          mood={hover ? 'happy' : line.mood}
          instincts={3}
          track
          size={176}
          title="Grace, generation 7, alive"
        />
      </motion.div>
      <p className="mt-4 text-center font-mono text-[12px] text-dim">
        gen 07 · grace · <span className="text-life">alive</span>
      </p>
    </div>
  );
}
