'use client';
// A card with a soft gilt light that follows the pointer and warms the edge. Pattern from React Bits
// "Spotlight Card" and Aceternity "Card Hover Effect" (MIT), rebuilt with CSS variables. The light is a response
// to the pointer, so it does nothing on touch screens and nothing moves on its own.
import { useRef } from 'react';

export function SpotlightCard({ children, className = '', as: Tag = 'div' }: { children: React.ReactNode; className?: string; as?: 'div' | 'li' | 'article' }) {
  const ref = useRef<HTMLElement>(null);
  const move = (e: React.PointerEvent) => {
    if (e.pointerType !== 'mouse') return;
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty('--mx', `${e.clientX - r.left}px`);
    el.style.setProperty('--my', `${e.clientY - r.top}px`);
    el.style.setProperty('--lit', '1');
  };
  const leave = () => ref.current?.style.setProperty('--lit', '0');
  return (
    <Tag ref={ref as never} onPointerMove={move} onPointerLeave={leave} className={`relative overflow-hidden ${className}`}>
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 transition-opacity duration-300"
        style={{
          opacity: 'var(--lit, 0)',
          background: 'radial-gradient(360px circle at var(--mx, 50%) var(--my, 50%), rgb(217 180 106 / 0.13), transparent 70%)',
        }}
      />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-[inherit] transition-opacity duration-300"
        style={{
          opacity: 'var(--lit, 0)',
          padding: '1px',
          background: 'radial-gradient(240px circle at var(--mx, 50%) var(--my, 50%), rgb(217 180 106 / 0.7), transparent 70%)',
          WebkitMask: 'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
          WebkitMaskComposite: 'xor',
          mask: 'linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0)',
        }}
      />
      <div className="relative">{children}</div>
    </Tag>
  );
}
