'use client';
// Adapted from the Magic UI "Number Ticker" pattern (magicui.design, MIT): counts up once when it scrolls into
// view, because the figure is the point (the family climbs from nothing). Final value under reduced motion.
import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from '@/lib/use-reduced-motion';

export function CountUp({ value, suffix = '', decimals = 0, className }: { value: number; suffix?: string; decimals?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduce = useReducedMotion();
  const [n, setN] = useState(value);
  useEffect(() => {
    const el = ref.current;
    if (reduce || !el || !('IntersectionObserver' in window)) return;
    let raf = 0;
    const run = () => {
      const t0 = performance.now();
      const tick = (now: number) => {
        const p = Math.min(1, (now - t0) / 2200);
        setN(value * (1 - Math.pow(1 - p, 4)));
        if (p < 1) raf = requestAnimationFrame(tick);
      };
      setN(0);
      raf = requestAnimationFrame(tick);
    };
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          io.disconnect();
          run();
        }
      },
      { rootMargin: '-10% 0px' },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [value, reduce]);
  return (
    <span ref={ref} className={`tabular-nums ${className ?? ''}`}>
      {n.toFixed(decimals)}
      {suffix}
    </span>
  );
}
