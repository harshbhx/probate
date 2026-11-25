'use client';
// A tall section pins one statement mid-screen and lights it word by word as you scroll through it. Idea from
// Magic UI "Text Reveal" (MIT), via the same pattern in Tarang FM. The words are real text the whole time. Unlit
// words are drawn in --color-unlit, which already passes WCAG AA on the canvas, and move toward their lit colour
// as one scroll handler sets a --p custom property (0 to 1) on each word. Under reduced motion (CSS) every word
// is lit and the statement is a normal block instead of a pinned run.
import { useEffect, useRef } from 'react';

export function TextReveal({ id, text, accent = [], run = 1.6, className = '' }: { id?: string; text: string; accent?: string[]; run?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const words = text.split(' ');
  const lit = new Set(accent.map((w) => w.toLowerCase()));
  const key = (w: string) => w.toLowerCase().replace(/[^a-z]/g, '');

  useEffect(() => {
    const box = ref.current;
    if (!box) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const spans = Array.from(box.querySelectorAll<HTMLElement>('.lit-word'));
    let raf = 0;
    let top = 0;
    let height = 1;
    // Layout is read here, once per resize, and never inside the scroll handler.
    const measure = () => {
      const r = box.getBoundingClientRect();
      top = r.top + window.scrollY;
      height = r.height;
    };
    const paint = () => {
      raf = 0;
      // Same window as before: from the block's top at 85% of the screen to its bottom at 55%.
      const start = top - window.innerHeight * 0.85;
      const end = top + height - window.innerHeight * 0.55;
      const progress = Math.min(1, Math.max(0, (window.scrollY - start) / (end - start)));
      const n = spans.length;
      for (let i = 0; i < n; i++) {
        const p = Math.min(1, Math.max(0, progress * n - i));
        spans[i].style.setProperty('--p', p.toFixed(3));
      }
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(paint);
    };
    const ro = new ResizeObserver(() => {
      measure();
      onScroll();
    });
    ro.observe(box);
    measure();
    paint();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      ro.disconnect();
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div
      id={id}
      ref={ref}
      style={{ '--run-h': `${run * 100}vh` } as React.CSSProperties}
      // Phones: no pin. The statement is a normal block that lights up as it crosses the screen, so there is no
      // screen of empty space around a six-line paragraph. From sm up it pins for a run of `run` screens (unless
      // the visitor prefers reduced motion).
      className="relative motion-safe:sm:h-[var(--run-h)]"
    >
      <div className={`motion-safe:sm:sticky motion-safe:sm:top-0 motion-safe:sm:flex motion-safe:sm:h-screen motion-safe:sm:items-center mx-auto max-w-6xl px-5 py-24 sm:px-6 sm:py-16 ${className}`}>
        <p className="max-w-5xl font-display text-[34px] font-[420] leading-[1.14] tracking-[-0.02em] text-moon sm:text-[52px] lg:text-[68px]">
          {words.map((w, i) => (
            <span key={i} className="lit-word" style={lit.has(key(w)) ? ({ '--lit': 'var(--color-gilt)' } as React.CSSProperties) : undefined}>
              {w}{' '}
            </span>
          ))}
        </p>
      </div>
    </div>
  );
}
