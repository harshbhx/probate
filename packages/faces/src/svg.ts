// Framework-free output: a face as an SVG string. Works in Node, a browser, a worker, an edge
// function or a build script. No DOM, no React.
import { describeTraits, traitsFor, type Family, type Traits } from "./model.js";
import { glyph, type Child, type GlyphOptions, type VNode } from "./render.js";

/** The animation rules the faces use (breathing, blinking, a glint, the mood pop). */
export const FACE_CSS = `/* Family faces: the only motion is life (breathing, blinking, a glint) and the mood pop. */
@keyframes pf-breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.025); } }
@keyframes pf-blink { 0%, 92%, 100% { transform: scaleY(1); } 95% { transform: scaleY(0.1); } }
@keyframes pf-glint { 0%, 100% { opacity: 1; } 50% { opacity: 0.55; } }
@keyframes pf-pop { 0% { transform: scale(0); } 70% { transform: scale(1.15); } 100% { transform: scale(1); } }
.pf-breathe { animation: pf-breathe 3.6s ease-in-out infinite; }
.pf-blink { animation: pf-blink 4.6s ease-in-out infinite; }
.pf-glint { animation: pf-glint 2.4s ease-in-out infinite; }
.pf-pop { animation: pf-pop 0.35s cubic-bezier(.2,.8,.2,1) both; }
@media (prefers-reduced-motion: reduce) {
  .pf-breathe, .pf-blink, .pf-glint, .pf-pop { animation: none !important; }
}
`;

/**
 * What to draw: a generation number of the default family, a family name (its founder, or
 * pass `gen` for a later generation), or an explicit set of traits.
 */
export type FaceInput = number | string | Traits;

export interface FaceOptions extends Omit<GlyphOptions, "traits" | "family" | "animate"> {
  /** Generation when `input` is a family name. Default 1. */
  gen?: number;
  /** Pixel size of the square. Default 64. */
  size?: number;
  /** Accessible name. Without it the svg is marked decorative (aria-hidden). */
  title?: string;
  /** Longer accessible description (adds <desc>). */
  desc?: string;
  /** Class attribute on the <svg>. */
  className?: string;
  /** Add the pf-* animation classes and an embedded <style> with FACE_CSS. Default false. */
  animate?: boolean;
}

export interface ResolvedFace {
  traits: Traits;
  /** Undefined when the input was a bare traits object. */
  gen: number | undefined;
  family: Family;
}

/** Turn a seed (number, string or traits) into the traits that will be drawn. */
export function resolveFace(input: FaceInput, gen?: number): ResolvedFace {
  if (typeof input === "object" && input !== null) return { traits: input, gen, family: undefined };
  if (typeof input === "number") return { traits: traitsFor(input), gen: input, family: undefined };
  const g = gen ?? 1;
  return { traits: traitsFor(g, input), gen: g, family: input };
}

/** Alt text for a face, e.g. "squircle-headed face with dot eyes, a smile, ...". */
export function faceAlt(input: FaceInput, opts: { gen?: number } = {}): string {
  return describeTraits(resolveFace(input, opts.gen).traits);
}

/** The face as a standalone `<svg>` string. Same input, same string, every time. */
export function faceSvg(input: FaceInput, opts: FaceOptions = {}): string {
  const { size = 64, title, desc, className, animate = false, gen, ...rest } = opts;
  const r = resolveFace(input, gen);
  const body = glyph({ ...rest, traits: r.traits, gen: r.gen, family: r.family, animate });
  const attrs: Record<string, unknown> = {
    xmlns: "http://www.w3.org/2000/svg",
    width: size,
    height: size,
    viewBox: "0 0 64 64",
    class: className,
    role: title ? "img" : undefined,
    "aria-label": title,
    "aria-hidden": title ? undefined : "true",
    style: "overflow:visible",
  };
  const inner =
    (title ? `<title>${esc(title)}</title>` : "") +
    (desc ? `<desc>${esc(desc)}</desc>` : "") +
    (animate ? `<style>${FACE_CSS.replace(/\n/g, "")}</style>` : "") +
    serialize(body);
  return `<svg${attrsToString(attrs)}>${inner}</svg>`;
}

/** Serialise a glyph element tree to markup (no outer <svg>): what you embed in your own SVG. */
export function faceGlyphSvg(input: FaceInput, opts: Omit<FaceOptions, "size" | "title" | "desc" | "className"> = {}): string {
  const { animate = false, gen, ...rest } = opts;
  const r = resolveFace(input, gen);
  return serialize(glyph({ ...rest, traits: r.traits, gen: r.gen, family: r.family, animate }));
}

// ---------------------------------------------------------------- serialiser

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const kebab = (s: string) => s.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
// SVG attributes that are camelCase in the markup too.
const KEEP_CAMEL = new Set(["viewBox", "preserveAspectRatio"]);

function styleToString(style: Record<string, unknown>): string {
  return Object.entries(style)
    .filter(([, v]) => v !== undefined && v !== null && v !== false)
    .map(([k, v]) => `${kebab(k)}:${v}`)
    .join(";");
}

function attrsToString(props: Record<string, unknown>): string {
  let out = "";
  for (const [k, v] of Object.entries(props)) {
    if (v === undefined || v === null || v === false) continue;
    const name = k === "className" ? "class" : k === "style" && typeof v === "object" ? "style" : KEEP_CAMEL.has(k) ? k : kebab(k);
    const value = k === "style" && typeof v === "object" ? styleToString(v as Record<string, unknown>) : String(v);
    out += ` ${name}="${esc(value)}"`;
  }
  return out;
}

function serializeChild(c: Child): string {
  if (c === null || c === undefined || c === false) return "";
  if (Array.isArray(c)) return c.map(serializeChild).join("");
  if (typeof c === "string" || typeof c === "number") return esc(String(c));
  return serialize(c);
}

export function serialize(node: VNode): string {
  const kids = node.children.map(serializeChild).join("");
  return kids ? `<${node.tag}${attrsToString(node.props)}>${kids}</${node.tag}>` : `<${node.tag}${attrsToString(node.props)}/>`;
}
