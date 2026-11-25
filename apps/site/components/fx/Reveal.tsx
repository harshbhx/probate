'use client';
// Adapted from the Magic UI "Blur Fade" pattern (magicui.design, MIT): fades up once when it scrolls into view.
// Used on section headings only, so the page has one quiet rhythm and nothing scatters.
// The motion is plain CSS (.reveal in global.css, only under no-preference); this component only flips a data
// attribute when the block enters the screen, so it ships no animation library.
import { useEffect, useRef } from 'react';

export function Reveal({ children, className = '', delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
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
      { rootMargin: '0px 0px -8% 0px' },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} className={`reveal ${className}`} style={delay ? ({ '--reveal-delay': `${delay}s` } as React.CSSProperties) : undefined}>
      {children}
    </div>
  );
}
