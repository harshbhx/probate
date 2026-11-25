'use client';
// Reading progress as a thin gilt line along the top of the page. Pattern from Magic UI "Scroll Progress"
// (magicui.design, MIT), also used on Tarang FM. It answers the reader's own scrolling, so it is not ambient.
// One passive scroll listener writes a transform (no layout reads in the handler beyond scrollY); hidden under
// reduced motion by CSS.
import { useEffect, useRef } from 'react';

export function ScrollProgress() {
  const bar = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = bar.current;
    if (!el) return;
    let raf = 0;
    let max = 1;
    const measure = () => {
      max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    };
    const paint = () => {
      raf = 0;
      el.style.transform = `scaleX(${Math.min(1, Math.max(0, window.scrollY / max))})`;
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(paint);
    };
    const ro = new ResizeObserver(() => {
      measure();
      onScroll();
    });
    ro.observe(document.body);
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
      ref={bar}
      aria-hidden
      style={{ transform: 'scaleX(0)' }}
      className="pointer-events-none fixed inset-x-0 top-0 z-50 h-[2px] origin-left bg-gilt transition-transform duration-150 ease-out motion-reduce:hidden"
    />
  );
}
