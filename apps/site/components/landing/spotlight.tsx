'use client';
// A card with a soft light that follows the pointer (pattern after Aceternity's card spotlight).
import { type ReactNode, useRef } from 'react';

export function Spotlight({
  children,
  className = '',
  color = 'rgb(91 227 169 / 0.09)',
}: {
  children: ReactNode;
  className?: string;
  color?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <div
      ref={ref}
      onPointerMove={(e) => {
        const el = ref.current;
        if (!el) return;
        const r = el.getBoundingClientRect();
        el.style.setProperty('--mx', `${e.clientX - r.left}px`);
        el.style.setProperty('--my', `${e.clientY - r.top}px`);
      }}
      className={`group relative overflow-hidden rounded-2xl border border-line bg-night-2/70 ${className}`}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{ background: `radial-gradient(380px circle at var(--mx) var(--my), ${color}, transparent 65%)` }}
      />
      <div className="relative h-full">{children}</div>
    </div>
  );
}
