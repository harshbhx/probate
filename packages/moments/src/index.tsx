'use client';
// One-shot pixel art moments from pixelfx (see README). A moment plays once when it mounts, centred on its
// parent's positioning box, then removes itself. Nothing plays under prefers-reduced-motion.
import { useEffect, useRef, useState } from 'react';

export type MomentKind = 'convicted' | 'instinct';

const MOMENTS: Record<MomentKind, { w: number; h: number; frames: number; fps: number; cy: number }> = {
  // cy is the vertical centre of the burst inside a frame, so the burst lands on its target
  convicted: { w: 128, h: 88, frames: 28, fps: 30, cy: 44 },
  instinct: { w: 112, h: 108, frames: 42, fps: 30, cy: 52 },
};

type Props = {
  kind: MomentKind;
  /** Pixel scale; the effects are drawn at 1x pixel art. */
  scale?: number;
  /** Where the strips are served from. */
  base?: string;
  /** Wait before playing, in milliseconds (to land with a stamp). */
  delay?: number;
  className?: string;
};

export function PixelMoment({ kind, scale = 2, base = '/moments', delay = 0, className = '' }: Props) {
  const m = MOMENTS[kind];
  const ref = useRef<HTMLDivElement>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setDone(true);
      return;
    }
    let raf = 0;
    let start = 0;
    const timer = window.setTimeout(() => {
      const step = (now: number) => {
        if (!start) start = now;
        const f = Math.floor(((now - start) / 1000) * m.fps);
        const el = ref.current;
        if (!el) return;
        if (f >= m.frames) {
          setDone(true);
          return;
        }
        el.style.opacity = '1';
        el.style.backgroundPosition = `${-f * m.w * scale}px 0`;
        raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    }, delay);
    return () => {
      window.clearTimeout(timer);
      cancelAnimationFrame(raf);
    };
  }, [m, scale, delay]);

  if (done) return null;
  return (
    <div
      ref={ref}
      aria-hidden
      className={className}
      style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        width: m.w * scale,
        height: m.h * scale,
        marginLeft: (-m.w * scale) / 2,
        marginTop: -m.cy * scale,
        pointerEvents: 'none',
        opacity: 0,
        backgroundImage: `url(${base}/${kind}.png)`,
        backgroundRepeat: 'no-repeat',
        backgroundSize: `${m.w * m.frames * scale}px ${m.h * scale}px`,
        imageRendering: 'pixelated',
        zIndex: 0,
      }}
    />
  );
}
