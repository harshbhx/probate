'use client';
// Adapted from the React Bits "Decrypted Text" pattern (reactbits.dev, MIT): glyphs shuffle, then lock in
// left to right. Plays once on mount. The real text is always in the DOM for readers and search, and under
// prefers-reduced-motion it never changes. The real text also sets the box (the scrambled layer is
// absolutely positioned over it), so shuffling never moves or resizes anything around it.
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
    <span className={`relative inline-block ${className ?? ''}`}>
      <span className={shown === text ? undefined : 'opacity-0'}>{text}</span>
      {shown !== text && (
        <span aria-hidden className="pointer-events-none absolute left-0 top-0 whitespace-pre">
          {shown}
        </span>
      )}
    </span>
  );
}
