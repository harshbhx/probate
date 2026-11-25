"use client";
// A generation's portrait, drawn on a 64 × 64 grid.
// Alive: lit, breathing, blinking, a green halo; eyes can follow the pointer.
// Sealed: closed eyes and a quieter tone. Gold diamonds are the instincts it was born with.
import { useEffect, useRef, useState } from "react";
import { SKINS, hash, traitsFor, type Life, type Mood, type Traits } from "./model";

const INK = "#0A0E17";
const LIFE = "#5BE3A9";
const GILT = "#E2BE6A";
const MIST = "#8C95AB";
const BLUSH = "#FF8A8F";

export interface FaceProps {
  gen: number;
  life?: Life;
  mood?: Mood;
  instincts?: number;
  /** Eyes follow the pointer (alive faces only). */
  track?: boolean;
  /** Pixel size of the square. */
  size?: number;
  /** Accessible name, e.g. "Ada, generation 1". Without it the face is decorative. */
  title?: string;
  className?: string;
}

export function FamilyFace({ size = 64, title, className, ...props }: FaceProps) {
  const ref = useRef<SVGSVGElement>(null);
  const look = usePointerLook(ref, !!props.track && props.life === "alive");
  return (
    <svg
      ref={ref}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={className}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      style={{ overflow: "visible" }}
    >
      <FaceGlyph {...props} look={look} />
    </svg>
  );
}

/** The face as an SVG group, for drawing inside another SVG (64 × 64 units). */
export function FaceGlyph({
  gen,
  life = "alive",
  mood = "idle",
  instincts = 0,
  look = { x: 0, y: 0 },
}: Omit<FaceProps, "size" | "title" | "className" | "track"> & { look?: { x: number; y: number } }) {
  const t = traitsFor(gen);
  const sealed = life === "sealed";
  const unborn = life === "unborn";
  const skin = SKINS[t.skin];
  const delay = `${(hash("blink", gen) % 4000) / 1000}s`;
  const eyeMood: Mood = sealed ? "sleepy" : mood;

  return (
    <g opacity={unborn ? 0.18 : 1} style={{ transition: "opacity .4s" }}>
      {life === "alive" && (
        <circle
          cx="32"
          cy="34"
          r="29"
          fill={LIFE}
          opacity="0.14"
          className="pf-breathe"
          style={{ transformOrigin: "32px 34px" }}
        />
      )}
      <Crown t={t} sealed={sealed} />
      <g className={life === "alive" ? "pf-breathe" : undefined} style={{ transformOrigin: "32px 34px" }}>
        <Head t={t} fill={sealed ? mix(skin, "#7A8299", 0.28) : skin} stroke={life === "alive" ? LIFE : sealed ? MIST : skin} />
        <Cheeks t={t} sealed={sealed} />
        <g transform={`translate(${look.x} ${look.y})`} style={{ transition: "transform .18s ease-out" }}>
          <EyePair t={t} mood={eyeMood} sealed={sealed} delay={delay} />
          <MouthShape t={t} mood={sealed ? "idle" : mood} />
        </g>
      </g>
      <Pop mood={sealed ? "idle" : mood} />
      <Instincts n={instincts} dim={sealed} />
    </g>
  );
}

// ---------------------------------------------------------------- parts

function Head({ t, fill, stroke }: { t: Traits; fill: string; stroke: string }) {
  const common = { fill, stroke, strokeWidth: 1.6, strokeOpacity: 0.9 };
  switch (t.head) {
    case "round":
      return <circle cx="32" cy="34" r="20" {...common} />;
    case "tall":
      return <rect x="15" y="12" width="34" height="44" rx="17" {...common} />;
    case "wide":
      return <rect x="9" y="17" width="46" height="36" rx="16" {...common} />;
    default:
      return <rect x="12" y="14" width="40" height="40" rx="14" {...common} />;
  }
}

function Crown({ t, sealed }: { t: Traits; sealed: boolean }) {
  const top = t.head === "tall" ? 12 : t.head === "wide" ? 17 : 14;
  const leaf = sealed ? MIST : LIFE;
  const stem = { stroke: sealed ? MIST : "#C9D0DD", strokeWidth: 1.6, strokeLinecap: "round" as const, fill: "none" };
  switch (t.crown) {
    case "sprout":
      return (
        <g>
          <path d={`M32 ${top} V${top - 7}`} {...stem} />
          <path d={`M32 ${top - 5} C27 ${top - 6} 25.5 ${top - 10} 27 ${top - 12} C31 ${top - 11} 32 ${top - 8} 32 ${top - 5}Z`} fill={leaf} />
          <path d={`M32 ${top - 6} C37 ${top - 7} 38.5 ${top - 11} 37 ${top - 13} C33 ${top - 12} 32 ${top - 9} 32 ${top - 6}Z`} fill={leaf} opacity="0.8" />
        </g>
      );
    case "antenna":
      return (
        <g>
          <path d={`M32 ${top} V${top - 8}`} {...stem} />
          <circle cx="32" cy={top - 10} r="2.6" fill={sealed ? MIST : GILT} className={sealed ? undefined : "pf-glint"} />
        </g>
      );
    case "twin":
      return (
        <g>
          <path d={`M27 ${top + 1} L24 ${top - 6}`} {...stem} />
          <path d={`M37 ${top + 1} L40 ${top - 6}`} {...stem} />
          <circle cx="23.6" cy={top - 7.4} r="2" fill={leaf} />
          <circle cx="40.4" cy={top - 7.4} r="2" fill={leaf} />
        </g>
      );
    default:
      return null;
  }
}

function EyePair({ t, mood, sealed, delay }: { t: Traits; mood: Mood; sealed: boolean; delay: string }) {
  const dx = t.wide ? 9 : 7;
  const y = 33;
  if (sealed || mood === "sleepy") {
    // Closed: gentle downward arcs.
    return (
      <g stroke={INK} strokeWidth="1.8" strokeLinecap="round" fill="none">
        <path d={`M${32 - dx - 3} ${y} Q${32 - dx} ${y + 2.6} ${32 - dx + 3} ${y}`} />
        <path d={`M${32 + dx - 3} ${y} Q${32 + dx} ${y + 2.6} ${32 + dx + 3} ${y}`} />
      </g>
    );
  }
  if (mood === "happy" || (t.eyes === "kind" && mood === "idle")) {
    return (
      <g stroke={INK} strokeWidth="1.9" strokeLinecap="round" fill="none">
        <path d={`M${32 - dx - 3} ${y + 1} Q${32 - dx} ${y - 2.6} ${32 - dx + 3} ${y + 1}`} />
        <path d={`M${32 + dx - 3} ${y + 1} Q${32 + dx} ${y - 2.6} ${32 + dx + 3} ${y + 1}`} />
      </g>
    );
  }
  if (mood === "fooled") {
    // Dizzy little spirals.
    const spiral = (cx: number) => `M${cx} ${y} m-0.6 0 a0.6 0.6 0 1 1 1.2 0 a1.6 1.6 0 1 1 -3.2 0 a2.6 2.6 0 1 1 5.2 0`;
    return (
      <g stroke={INK} strokeWidth="1.2" fill="none" strokeLinecap="round">
        <path d={spiral(32 - dx)} />
        <path d={spiral(32 + dx)} />
      </g>
    );
  }
  const big = mood === "alert" ? 1.25 : 1;
  const blink = { className: "pf-blink", style: { animationDelay: delay, transformBox: "fill-box" as const, transformOrigin: "center" } };
  if (t.eyes === "visor") {
    return (
      <g>
        <rect x={32 - dx - 5} y={y - 3.4} width={dx * 2 + 10} height="6.8" rx="3.4" fill={INK} />
        <g {...blink}>
          <circle cx={32 - dx} cy={y} r={1.8 * big} fill={LIFE} />
          <circle cx={32 + dx} cy={y} r={1.8 * big} fill={LIFE} />
        </g>
        {mood === "alert" && <Brows dx={dx} y={y - 6.5} />}
      </g>
    );
  }
  return (
    <g>
      <g {...blink} fill={INK}>
        {t.eyes === "oval" ? (
          <>
            <ellipse cx={32 - dx} cy={y} rx={2.3 * big} ry={3.3 * big} />
            <ellipse cx={32 + dx} cy={y} rx={2.3 * big} ry={3.3 * big} />
          </>
        ) : (
          <>
            <circle cx={32 - dx} cy={y} r={2.7 * big} />
            <circle cx={32 + dx} cy={y} r={2.7 * big} />
          </>
        )}
        <circle cx={32 - dx + 0.9} cy={y - 1} r="0.8" fill="#fff" opacity="0.85" />
        <circle cx={32 + dx + 0.9} cy={y - 1} r="0.8" fill="#fff" opacity="0.85" />
      </g>
      {mood === "alert" && <Brows dx={dx} y={y - 6} />}
    </g>
  );
}

function Brows({ dx, y }: { dx: number; y: number }) {
  return (
    <g stroke={INK} strokeWidth="1.6" strokeLinecap="round">
      <path d={`M${32 - dx - 3} ${y - 1} L${32 - dx + 2.5} ${y + 1}`} />
      <path d={`M${32 + dx + 3} ${y - 1} L${32 + dx - 2.5} ${y + 1}`} />
    </g>
  );
}

function MouthShape({ t, mood }: { t: Traits; mood: Mood }) {
  const y = 42.5;
  const line = { stroke: INK, strokeWidth: 1.8, strokeLinecap: "round" as const, fill: "none" };
  if (mood === "alert") return <path d={`M28.5 ${y + 1} L35.5 ${y + 1}`} {...line} />;
  if (mood === "fooled") return <path d={`M27 ${y + 1} q2.5 -2 5 0 t5 0`} {...line} />;
  if (mood === "happy") return <path d={`M26.5 ${y - 1} Q32 ${y + 5.5} 37.5 ${y - 1} Z`} fill={INK} />;
  switch (t.mouth) {
    case "flat":
      return <path d={`M28.5 ${y + 0.5} L35.5 ${y + 0.5}`} {...line} />;
    case "small":
      return <circle cx="32" cy={y + 0.5} r="1.7" fill={INK} />;
    case "grin":
      return <path d={`M27 ${y - 0.5} Q32 ${y + 4.6} 37 ${y - 0.5} Z`} fill={INK} />;
    default:
      return <path d={`M28 ${y} Q32 ${y + 3.4} 36 ${y}`} {...line} />;
  }
}

function Cheeks({ t, sealed }: { t: Traits; sealed: boolean }) {
  if (t.cheeks === "none") return null;
  const o = sealed ? 0.15 : 0.4;
  if (t.cheeks === "blush")
    return (
      <g fill={BLUSH} opacity={o}>
        <ellipse cx="19.5" cy="40" rx="3" ry="1.8" />
        <ellipse cx="44.5" cy="40" rx="3" ry="1.8" />
      </g>
    );
  return (
    <g fill={INK} opacity={sealed ? 0.25 : 0.45}>
      {[
        [18.5, 39.5],
        [21, 40.8],
        [19.2, 42],
        [45.5, 39.5],
        [43, 40.8],
        [44.8, 42],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="0.6" />
      ))}
    </g>
  );
}

function Pop({ mood }: { mood: Mood }) {
  if (mood !== "alert" && mood !== "fooled") return null;
  const mark = mood === "alert" ? "!" : "?";
  return (
    <g className="pf-pop" style={{ transformOrigin: "52px 12px" }}>
      <circle cx="52" cy="12" r="6.5" fill={mood === "alert" ? GILT : "#F5A524"} />
      <text x="52" y="15.6" textAnchor="middle" fontSize="10" fontWeight="700" fill={INK} fontFamily="ui-sans-serif, system-ui">
        {mark}
      </text>
    </g>
  );
}

function Instincts({ n, dim }: { n: number; dim: boolean }) {
  if (n <= 0) return null;
  const shown = Math.min(n, 5);
  const gap = 6.2;
  const x0 = 32 - ((shown - 1) * gap) / 2;
  return (
    <g fill={GILT} opacity={dim ? 0.75 : 1}>
      {Array.from({ length: shown }).map((_, i) => (
        <path key={i} d={`M${x0 + i * gap} 58 l2.4 2.4 l-2.4 2.4 l-2.4 -2.4z`} />
      ))}
      {n > shown && (
        <text x={x0 + shown * gap + 1} y="62.6" fontSize="6.5" fill={GILT} fontFamily="ui-monospace, monospace">
          +{n - shown}
        </text>
      )}
    </g>
  );
}

// ---------------------------------------------------------------- helpers

function mix(a: string, b: string, k: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return `#${pa.map((v, i) => Math.round(v + (pb[i] - v) * k).toString(16).padStart(2, "0")).join("")}`;
}

/** Eyes drift toward the pointer, at most ~1.8 units. Off under reduced motion. */
function usePointerLook(ref: React.RefObject<SVGSVGElement | null>, on: boolean) {
  const [look, setLook] = useState({ x: 0, y: 0 });
  useEffect(() => {
    if (!on || typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const move = (e: PointerEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const el = ref.current;
        if (!el) return;
        const r = el.getBoundingClientRect();
        const dx = e.clientX - (r.left + r.width / 2);
        const dy = e.clientY - (r.top + r.height / 2);
        const d = Math.hypot(dx, dy) || 1;
        const k = Math.min(1, d / 260);
        setLook({ x: (dx / d) * 1.8 * k, y: (dy / d) * 1.4 * k });
      });
    };
    window.addEventListener("pointermove", move, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", move);
    };
  }, [on, ref]);
  return look;
}
