"use client";
// React bindings. `react` is an optional peer dependency: import from "kinfaces/react" only if
// you use React; the main entry point never touches it.
//
// Alive: lit, breathing, blinking, a green halo; eyes can follow the pointer.
// Sealed: closed eyes and a quieter tone. Gold diamonds are the instincts it was born with.
import { createElement, useEffect, useRef, useState, type ReactElement, type ReactNode, type RefObject } from "react";
import type { Family, Life, Mood, Traits } from "./model.js";
import { glyph, type Child, type VNode } from "./render.js";

export interface FaceProps {
  /** Generation, 1-based (of `family`, or of the default family). */
  gen?: number;
  /** Family name: a different deterministic line of faces. */
  family?: Family;
  /** Draw exactly these traits instead of deriving them from `gen`. */
  traits?: Traits;
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
  /** A CSS colour for a rounded tile behind the face (the pale skins suit dark backgrounds). */
  background?: string;
}

function toReact(c: Child, key?: number): ReactNode {
  if (c === null || c === undefined || c === false) return null;
  if (Array.isArray(c)) return c.map((x, i) => toReact(x, i));
  if (typeof c === "string" || typeof c === "number") return c;
  const n = c as VNode;
  return createElement(n.tag, { ...n.props, key }, ...n.children.map((x, i) => toReact(x, i)));
}

export function FamilyFace({ size = 64, title, className, background, ...props }: FaceProps): ReactElement {
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
      {background ? <rect width="64" height="64" rx="14" fill={background} /> : null}
      <FaceGlyph {...props} look={look} />
    </svg>
  );
}

/** The face as an SVG group, for drawing inside another SVG (64 x 64 units). */
export function FaceGlyph({
  gen = 1,
  family,
  traits,
  life = "alive",
  mood = "idle",
  instincts = 0,
  look = { x: 0, y: 0 },
}: Omit<FaceProps, "size" | "title" | "className" | "track"> & { look?: { x: number; y: number } }): ReactElement {
  return toReact(glyph({ gen, family, traits, life, mood, instincts, look, animate: true })) as ReactElement;
}

/** Eyes drift toward the pointer, at most ~1.8 units. Off under reduced motion. */
function usePointerLook(ref: RefObject<SVGSVGElement | null>, on: boolean) {
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
