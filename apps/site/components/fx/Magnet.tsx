'use client';
// A button that leans a few pixels toward the pointer. Pattern from React Bits "Magnet" (MIT). A response to the
// pointer only: mouse users get it, touch and reduced-motion users get a plain button.
import { useRef } from 'react';
import { useReducedMotion } from 'motion/react';

export function Magnet({ children, strength = 0.22, className = '' }: { children: React.ReactNode; strength?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduce = useReducedMotion();
  const move = (e: React.PointerEvent) => {
    if (reduce || e.pointerType !== 'mouse' || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    ref.current.style.transform = `translate(${(e.clientX - (r.left + r.width / 2)) * strength}px, ${(e.clientY - (r.top + r.height / 2)) * strength}px)`;
  };
  const leave = () => {
    if (ref.current) ref.current.style.transform = '';
  };
  return (
    <span ref={ref} onPointerMove={move} onPointerLeave={leave} className={`flex transition-transform duration-200 ease-out ${className}`}>
      {children}
    </span>
  );
}
