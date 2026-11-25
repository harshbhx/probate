'use client';
// Adapted from the React Bits "Decrypted Text" pattern (reactbits.dev, MIT): glyphs shuffle, then lock in
// left to right. Plays once on mount. The real text is always in the DOM for readers and search, and under
// prefers-reduced-motion it never changes. The real text also sets the box (the scrambled layer sits on top of it
// in the same grid cell), so shuffling never moves the lines around it.
import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from '@/lib/use-reduced-motion';

const GLYPHS = '01+-/\|=<>#%';

export function Scramble({ text, duration = 1500, delay = 350, className }: { text: string; duration?: number; delay?: number; className?: string }) {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(text);
  const raf = useRef(0);

  useEffect(() => {
    if (reduce) return;
    let start = 0;
    const timer = window.setTimeout(() => {
      const tick = (now: number) => {
        if (!start) start = now;
        const p = Math.min(1, (now - start) / duration);
        const locked = Math.floor(p * text.length);
        setShown(
          text
            .split('')
            .map((c, i) => (c === ' ' || i < locked ? c : GLYPHS[Math.floor(Math.random() * GLYPHS.length)]))
            .join(''),
        );
        if (p < 1) raf.current = requestAnimationFrame(tick);
        else setShown(text);
      };
      raf.current = requestAnimationFrame(tick);
    }, delay);
    return () => {
      window.clearTimeout(timer);
      cancelAnimationFrame(raf.current);
    };
  }, [text, duration, delay, reduce]);

  return (
    <span className={`inline-grid ${className ?? ''}`}>
      <span className="col-start-1 row-start-1 opacity-0">{text}</span>
      <span aria-hidden className="col-start-1 row-start-1 whitespace-pre tabular-nums">
        {shown}
      </span>
    </span>
  );
}
