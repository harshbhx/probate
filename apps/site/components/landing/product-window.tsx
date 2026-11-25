'use client';
// A real screenshot of the live site in one consistent window frame. Every product shot on the
// landing page uses this frame (one frame style per page). The hero's window has Grace perched
// on top: the living generation, peeking over the edge, eyes on your pointer.
import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { Lock } from 'lucide-react';
import { FamilyFace, type Mood } from '@probate/faces';
// The shots come from a local simulated run (scripts: docs/04-DESIGN.md), so the address says so.
const host = 'localhost:8080';

type Props = {
  src: string;
  alt: string;
  path: string;
  width: number;
  height: number;
  eager?: boolean;
  perch?: boolean;
  className?: string;
};

export function ProductWindow({ src, alt, path, width, height, eager, perch, className = '' }: Props) {
  return (
    <figure className={`relative ${perch ? 'pt-16' : ''} ${className}`}>
      {perch && <Perch />}
      <div className="relative z-10 overflow-hidden rounded-2xl border border-line-strong bg-night-2 shadow-[0_40px_100px_-40px_rgb(0_0_0/0.9)]">
        <div className="flex h-10 items-center gap-3 border-b border-line bg-night-3 px-4" aria-hidden>
          <span className="flex gap-1.5">
            <i className="size-2.5 rounded-full bg-[#3a3e46]" />
            <i className="size-2.5 rounded-full bg-[#3a3e46]" />
            <i className="size-2.5 rounded-full bg-[#3a3e46]" />
          </span>
          <span className="mx-auto flex h-6 min-w-0 max-w-[70%] items-center gap-1.5 rounded-md bg-night-2 px-3 font-mono text-[11.5px] text-mist">
            <Lock size={10} className="shrink-0" />
            <span className="truncate">
              {host}
              <span className="text-dim">{path}</span>
            </span>
          </span>
          <span className="w-[46px]" />
        </div>
        {/* eslint-disable-next-line @next/next/no-img-element -- static export, pre-sized WebP */}
        <img
          src={src}
          alt={alt}
          width={width}
          height={height}
          loading={eager ? 'eager' : 'lazy'}
          decoding="async"
          className="block h-auto w-full"
        />
      </div>
    </figure>
  );
}

const LINES: { text: string; mood: Mood }[] = [
  { text: 'Hi, I’m Grace. I was born this morning.', mood: 'happy' },
  { text: 'This is the trial of Ada, the first of us.', mood: 'idle' },
  { text: 'I was born knowing every trick she fell for.', mood: 'alert' },
  { text: 'At midnight I die, and the court reads my will.', mood: 'sleepy' },
  { text: 'Whatever it approves, my child inherits.', mood: 'happy' },
];

function Perch() {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  const [hover, setHover] = useState(false);
  useEffect(() => {
    if (reduce) return;
    const id = setInterval(() => !document.hidden && setI((n) => (n + 1) % LINES.length), 4400);
    return () => clearInterval(id);
  }, [reduce]);
  const line = LINES[i];
  return (
    // Sits behind the window (z-0, the window is z-10): the window's top edge covers Grace's
    // chin, so she peeks over it. 64px of padding above the window plus 24px of overlap.
    <div className="absolute inset-x-0 top-0 z-0 flex h-[88px] items-end justify-end pr-[7%]">
      <div className="mb-9 mr-3 hidden w-[264px] sm:block" aria-live="polite">
        <AnimatePresence mode="wait">
          <motion.p
            key={i}
            initial={reduce ? false : { opacity: 0, x: 6 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -4 }}
            transition={{ duration: 0.25 }}
            className="relative rounded-xl border border-line-strong bg-night-4 px-3.5 py-2.5 text-[14px] leading-snug text-moon"
          >
            {line.text}
            <span
              aria-hidden
              className="absolute -right-[6px] bottom-3 size-2.5 rotate-45 border-r border-t border-line-strong bg-night-4"
            />
          </motion.p>
        </AnimatePresence>
      </div>
      <div onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}>
        <FamilyFace
          gen={7}
          life="alive"
          mood={hover ? 'happy' : line.mood}
          instincts={3}
          track
          size={88}
          title="Grace, generation 7, alive"
        />
      </div>
    </div>
  );
}
