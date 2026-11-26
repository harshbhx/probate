'use client';
// Marks its element with data-in the first time it scrolls into view, once. The motion itself is CSS keyed off
// that attribute (global.css, under prefers-reduced-motion: no-preference only), so the component ships a few
// lines of JavaScript and no animation library. The same idea as Reveal, without Reveal's fade.
import { createElement, useEffect, useRef, type ReactNode } from 'react';

export function InView({
  as = 'div',
  className,
  margin = '0px 0px -12% 0px',
  children,
  ...rest
}: {
  as?: 'div' | 'section' | 'ol' | 'ul' | 'figure';
  className?: string;
  margin?: string;
  children: ReactNode;
} & Partial<Record<`data-${string}` | `aria-${string}` | 'role' | 'id', string>>) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!('IntersectionObserver' in window)) {
      el.dataset.in = '';
      return;
    }
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          el.dataset.in = '';
          io.disconnect();
        }
      },
      { rootMargin: margin },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [margin]);
  return createElement(as, { ref, className, ...rest }, children);
}
