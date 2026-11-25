'use client';
// Below-the-fold sections that need JavaScript (the scroll film, the verdict cards, the court demo) are rendered
// to HTML at build time like everything else, but their code (and the animation library behind it) is not
// downloaded or hydrated until the section is about to be scrolled into view. React keeps the server HTML on
// screen while the chunk is pending, then hydrates it in place, so nothing jumps and nothing is blank.
import { Suspense, lazy, useEffect, useRef, type ComponentType } from 'react';

const NEAR = '900px 0px';

function defer(load: () => Promise<{ default: ComponentType }>) {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  // On the server (the static build) the section renders at once; in the browser it waits for the gate.
  const Lazy = lazy(async () => {
    if (typeof window !== 'undefined') await gate;
    return load();
  });
  return function Deferred() {
    const ref = useRef<HTMLDivElement>(null);
    useEffect(() => {
      const el = ref.current;
      if (!el) return;
      if (!('IntersectionObserver' in window)) {
        release();
        return;
      }
      const io = new IntersectionObserver(
        (entries) => {
          if (entries.some((e) => e.isIntersecting)) {
            release();
            io.disconnect();
          }
        },
        { rootMargin: NEAR },
      );
      io.observe(el);
      return () => io.disconnect();
    }, []);
    return (
      <div ref={ref}>
        <Suspense fallback={null}>
          <Lazy />
        </Suspense>
      </div>
    );
  };
}

export const LifeStory = defer(() => import('./life-story').then((m) => ({ default: m.LifeStory })));
export const LineageFilm = defer(() => import('./lineage-film').then((m) => ({ default: m.LineageFilm })));
export const TryCourt = defer(() => import('./try-court').then((m) => ({ default: m.TryCourt })));
export const VerdictStack = defer(() => import('./verdict-stack').then((m) => ({ default: m.VerdictStack })));
