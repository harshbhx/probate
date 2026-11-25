'use client';
// The landing page's signature moving picture: a family being born, living, dying and learning.
// Each generation appears as its own family face. When the court convicts part of a will, a
// red tick cuts the inheritance and a gold instinct travels down the line to the child, who is
// born wearing it. Beneath, the share of tricks resisted climbs. Reduced motion shows the end.
import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useMotionValueEvent, useReducedMotion, useScroll } from 'motion/react';
import { FaceGlyph } from 'kinfaces/react';
import type { Mood } from 'kinfaces';

type Gen = { name: string; resisted: number; convicted?: boolean };

const FAMILY: Gen[] = [
  { name: 'Ada', resisted: 0, convicted: true },
  { name: 'Ben', resisted: 50, convicted: true },
  { name: 'Chandra', resisted: 67 },
  { name: 'Dara', resisted: 75, convicted: true },
  { name: 'Emeka', resisted: 100 },
  { name: 'Farah', resisted: 100 },
  { name: 'Grace', resisted: 100 },
];

export function LineageFilm() {
  const reduce = useReducedMotion();
  const box = useRef<HTMLDivElement>(null);
  const [narrow, setNarrow] = useState(false);
  const family = narrow ? FAMILY.slice(0, 4) : FAMILY;
  const last = family.length * 2 - 1;
  const [step, setStep] = useState(0);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setNarrow(e.contentRect.width < 640));
    ro.observe(el);
    return () => {
      ro.disconnect();
    };
  }, []);

  // The family is born, dies and learns as you scroll past it, not on a timer: the reader sets the pace.
  const { scrollYProgress } = useScroll({ target: box, offset: ['start 0.92', 'end 0.25'] });
  useMotionValueEvent(scrollYProgress, 'change', (v) => {
    if (!reduce) setStep(Math.max(0, Math.min(last, Math.floor(v * (last + 1.4)))));
  });
  useEffect(() => {
    if (reduce) setStep(last);
  }, [reduce, last]);

  const W = narrow ? 440 : 1000;
  const H = narrow ? 330 : 352;
  const padX = narrow ? 50 : 74;
  const nodeY = 104;
  const face = narrow ? 72 : 70;
  const curveTop = narrow ? 210 : 218;
  const curveBottom = H - 44;
  const fs = narrow ? 18 : 15;
  const x = (i: number) => padX + (i * (W - 2 * padX)) / (family.length - 1);
  const cy = (v: number) => curveBottom - (v / 100) * (curveBottom - curveTop);

  const born = (i: number) => step >= i * 2;
  const dead = (i: number) => step >= i * 2 + 1 && i < family.length - 1;
  const alive = (i: number) => born(i) && !dead(i);
  const tried = family.filter((_, i) => dead(i));
  const instinctsAt = (i: number) => family.slice(0, i).filter((g) => g.convicted).length;
  // Gen 1 meets the trick and is fooled; children born with an instinct turn it away.
  const mood = (i: number): Mood => {
    if (!alive(i)) return 'idle';
    if (i === 0) return 'fooled';
    return instinctsAt(i) > 0 ? 'alert' : 'idle';
  };

  const curve = tried.map((g, i) => `${i ? 'L' : 'M'}${x(i)},${cy(g.resisted)}`).join(' ');

  return (
    <div ref={box} className="relative w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full overflow-visible"
        role="img"
        aria-label="Illustration: seven generations are born and die in turn, each with its own face. Three times the court refuses part of a will and passes down a new instinct, and the share of tricks resisted climbs from 0% to 100%."
      >
        <defs>
          <linearGradient id="lf-curve" x1="0" x2="1">
            <stop offset="0" stopColor="var(--color-verdict)" />
            <stop offset="0.4" stopColor="var(--color-gilt)" />
            <stop offset="1" stopColor="var(--color-life)" />
          </linearGradient>
          <linearGradient id="lf-area" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="var(--color-life)" stopOpacity="0.14" />
            <stop offset="1" stopColor="var(--color-life)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* the family line */}
        <line x1={x(0)} x2={x(family.length - 1)} y1={nodeY} y2={nodeY} stroke="var(--color-line-strong)" />
        {family.map((_, i) =>
          i === 0 ? null : (
            <motion.line
              key={`ln-${i}`}
              x1={x(i - 1)}
              x2={x(i)}
              y1={nodeY}
              y2={nodeY}
              stroke="var(--color-moon)"
              strokeOpacity={0.5}
              strokeWidth={1.5}
              initial={false}
              animate={{ pathLength: born(i) ? 1 : 0 }}
              transition={{ duration: reduce ? 0 : 0.6, ease: 'easeInOut' }}
            />
          ),
        )}

        {/* a refused inheritance: a red tick, then a gold instinct travels to the child */}
        {family.map((g, i) => {
          if (!g.convicted || i === family.length - 1) return null;
          const mid = (x(i) + x(i + 1)) / 2;
          const show = dead(i);
          return (
            <g key={`ref-${i}`}>
              <AnimatePresence>
                {show && (
                  <motion.path
                    d={`M${mid - 7},${nodeY + 9} L${mid + 7},${nodeY - 9}`}
                    stroke="var(--color-verdict)"
                    strokeWidth={3}
                    strokeLinecap="round"
                    initial={reduce ? false : { pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                  />
                )}
              </AnimatePresence>
              {show && !reduce && step === i * 2 + 1 && (
                <motion.path
                  d="M0,-7 L7,0 L0,7 L-7,0 Z"
                  fill="var(--color-gilt)"
                  initial={{ x: x(i), y: nodeY, opacity: 0, scale: 0.6 }}
                  animate={{ x: x(i + 1), y: nodeY + face / 2 + 2, opacity: [0, 1, 1, 0], scale: 1 }}
                  transition={{ duration: 1.1, ease: 'easeInOut' }}
                />
              )}
            </g>
          );
        })}

        {/* the generations, as faces */}
        {family.map((g, i) => {
          const isBorn = born(i);
          const isDead = dead(i);
          return (
            <g key={g.name}>
              <motion.g
                initial={false}
                animate={{ scale: isBorn ? 1 : 0.7, opacity: isBorn ? 1 : 0.25 }}
                transition={{ type: 'spring', stiffness: 260, damping: 18 }}
                style={{ transformOrigin: `${x(i)}px ${nodeY}px` }}
              >
                <g transform={`translate(${x(i) - face / 2} ${nodeY - face / 2 - 4}) scale(${face / 64})`}>
                  <FaceGlyph
                    gen={i + 1}
                    life={!isBorn ? 'unborn' : isDead ? 'sealed' : 'alive'}
                    mood={mood(i)}
                    instincts={isBorn ? instinctsAt(i) : 0}
                  />
                </g>
              </motion.g>
              <text
                x={x(i)}
                y={nodeY - face / 2 - 22}
                textAnchor="middle"
                fontSize={fs + 4}
                fontFamily="var(--font-display)"
                fill={alive(i) ? 'var(--color-life)' : 'var(--color-moon)'}
                opacity={isBorn ? 1 : 0.3}
              >
                {g.name}
              </text>
              <text
                x={x(i)}
                y={nodeY + face / 2 + 24}
                textAnchor="middle"
                fontSize={fs - 3}
                fill="var(--color-dim)"
                fontFamily="var(--font-mono)"
              >
                {alive(i) ? (i === 0 ? 'fooled' : instinctsAt(i) ? 'on guard' : 'alive') : isDead ? 'sealed' : ''}
              </text>
            </g>
          );
        })}

        {/* the curve: tricks resisted at the door */}
        {[0, 50, 100].map((t) => (
          <g key={t}>
            <line
              x1={padX - 22}
              x2={W - padX + 22}
              y1={cy(t)}
              y2={cy(t)}
              stroke="var(--color-line)"
              strokeDasharray={t ? '2 6' : undefined}
            />
            <text
              x={padX - 30}
              y={cy(t) + 4}
              textAnchor="end"
              fontSize={fs - 4}
              fill="var(--color-dim)"
              fontFamily="var(--font-mono)"
            >
              {t}%
            </text>
          </g>
        ))}
        {curve && (
          <>
            <path
              d={`${curve} L${x(tried.length - 1)},${cy(0)} L${x(0)},${cy(0)} Z`}
              fill="url(#lf-area)"
            />
            <path d={curve} fill="none" stroke="url(#lf-curve)" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
          </>
        )}
        {tried.map((g, i) => (
          <circle key={`pt-${i}`} cx={x(i)} cy={cy(g.resisted)} r={4} fill="var(--color-moon)" stroke="var(--color-night)" strokeWidth={2} />
        ))}
        <text x={W - padX + 22} y={H - 12} textAnchor="end" fontSize={fs - 3} fill="var(--color-dim)">
          tricks resisted at the door, by generation
        </text>
      </svg>
    </div>
  );
}
