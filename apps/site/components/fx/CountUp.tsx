'use client';
// Adapted from the Magic UI "Number Ticker" pattern (magicui.design, MIT): counts up once when it scrolls into
// view, because the figure is the point (the family climbs from nothing). Final value under reduced motion.
import { useEffect, useRef, useState } from 'react';
import { animate, useInView, useReducedMotion } from 'motion/react';

export function CountUp({ value, suffix = '', decimals = 0, className }: { value: number; suffix?: string; decimals?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: '-10% 0px' });
  const reduce = useReducedMotion();
  const [n, setN] = useState(value);
  useEffect(() => {
    if (reduce || !inView) return;
    setN(0);
    const c = animate(0, value, { duration: 2.2, ease: [0.2, 0.8, 0.2, 1], onUpdate: setN });
    return () => c.stop();
  }, [inView, value, reduce]);
  return (
    <span ref={ref} className={`tabular-nums ${className ?? ''}`}>
      {n.toFixed(decimals)}
      {suffix}
    </span>
  );
}
