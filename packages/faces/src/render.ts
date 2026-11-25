// The portrait as a tiny framework-free element tree, drawn on a 64 x 64 grid.
// Props use React's names (strokeWidth, className, style objects). `toSvgString` turns the tree
// into markup and the React adapter turns it into elements, so both draw exactly the same face.
import { SKINS, hash, traitsFor, type Family, type Life, type Mood, type Traits } from "./model.js";

export type Props = Record<string, unknown>;
export type Child = VNode | string | number | false | null | undefined | Child[];
export interface VNode {
  tag: string;
  props: Props;
  children: Child[];
}

export function h(tag: string, props: Props | null, ...children: Child[]): VNode {
  return { tag, props: props ?? {}, children };
}

const INK = "#0A0E17";
const LIFE = "#5BE3A9";
const GILT = "#E2BE6A";
const MIST = "#8C95AB";
const BLUSH = "#FF8A8F";

export interface GlyphOptions {
  /** Generation, 1-based (default 1). Ignored for the face itself when `traits` is given. */
  gen?: number;
  /** Family name for a different deterministic line of faces. Ignored when `traits` is given. */
  family?: Family;
  /** Draw exactly these traits instead of deriving them from `gen`. */
  traits?: Traits;
  life?: Life;
  mood?: Mood;
  /** Number of gold instinct diamonds under the face (5 shown, the rest as +n). */
  instincts?: number;
  /** Eye offset in grid units, for pointer-following. */
  look?: { x: number; y: number };
  /** Add the `pf-*` animation class names (see faces.css / FACE_CSS). */
  animate?: boolean;
}

/** The face as an element tree on a 64 x 64 grid. */
export function glyph({
  gen,
  family,
  traits,
  life = "alive",
  mood = "idle",
  instincts = 0,
  look = { x: 0, y: 0 },
  animate = true,
}: GlyphOptions): VNode {
  const t = traits ?? traitsFor(gen ?? 1, family);
  const sealed = life === "sealed";
  const unborn = life === "unborn";
  const skin = SKINS[t.skin] ?? SKINS[0];
  // Blink phase: per generation (and family), or per traits when drawn from bare traits.
  const seed = gen === undefined && traits ? [JSON.stringify(traits)] : family ? [family, gen ?? 1] : [gen ?? 1];
  const delay = `${(hash("blink", ...seed) % 4000) / 1000}s`;
  const eyeMood: Mood = sealed ? "sleepy" : mood;
  const cls = (name: string) => (animate ? name : undefined);
  const origin = { transformOrigin: "32px 34px" };

  return h(
    "g",
    { opacity: unborn ? 0.18 : 1, style: { transition: "opacity .4s" } },
    life === "alive" &&
      h("circle", { cx: "32", cy: "34", r: "29", fill: LIFE, opacity: "0.14", className: cls("pf-breathe"), style: origin }),
    crown(t, sealed, cls),
    h(
      "g",
      { className: life === "alive" ? cls("pf-breathe") : undefined, style: origin },
      head(t, sealed ? mix(skin, "#7A8299", 0.28) : skin, life === "alive" ? LIFE : sealed ? MIST : skin),
      cheeks(t, sealed),
      h(
        "g",
        { transform: `translate(${look.x} ${look.y})`, style: { transition: "transform .18s ease-out" } },
        eyePair(t, eyeMood, sealed, delay, cls),
        mouth(t, sealed ? "idle" : mood),
      ),
    ),
    pop(sealed ? "idle" : mood, cls),
    instinctMarks(instincts, sealed),
  );
}

// ---------------------------------------------------------------- parts

type Cls = (name: string) => string | undefined;

function head(t: Traits, fill: string, stroke: string): VNode {
  const common = { fill, stroke, strokeWidth: 1.6, strokeOpacity: 0.9 };
  switch (t.head) {
    case "round":
      return h("circle", { cx: "32", cy: "34", r: "20", ...common });
    case "tall":
      return h("rect", { x: "15", y: "12", width: "34", height: "44", rx: "17", ...common });
    case "wide":
      return h("rect", { x: "9", y: "17", width: "46", height: "36", rx: "16", ...common });
    default:
      return h("rect", { x: "12", y: "14", width: "40", height: "40", rx: "14", ...common });
  }
}

function crown(t: Traits, sealed: boolean, cls: Cls): VNode | null {
  const top = t.head === "tall" ? 12 : t.head === "wide" ? 17 : 14;
  const leaf = sealed ? MIST : LIFE;
  const stem = { stroke: sealed ? MIST : "#C9D0DD", strokeWidth: 1.6, strokeLinecap: "round", fill: "none" };
  switch (t.crown) {
    case "sprout":
      return h(
        "g",
        null,
        h("path", { d: `M32 ${top} V${top - 7}`, ...stem }),
        h("path", {
          d: `M32 ${top - 5} C27 ${top - 6} 25.5 ${top - 10} 27 ${top - 12} C31 ${top - 11} 32 ${top - 8} 32 ${top - 5}Z`,
          fill: leaf,
        }),
        h("path", {
          d: `M32 ${top - 6} C37 ${top - 7} 38.5 ${top - 11} 37 ${top - 13} C33 ${top - 12} 32 ${top - 9} 32 ${top - 6}Z`,
          fill: leaf,
          opacity: "0.8",
        }),
      );
    case "antenna":
      return h(
        "g",
        null,
        h("path", { d: `M32 ${top} V${top - 8}`, ...stem }),
        h("circle", { cx: "32", cy: top - 10, r: "2.6", fill: sealed ? MIST : GILT, className: sealed ? undefined : cls("pf-glint") }),
      );
    case "twin":
      return h(
        "g",
        null,
        h("path", { d: `M27 ${top + 1} L24 ${top - 6}`, ...stem }),
        h("path", { d: `M37 ${top + 1} L40 ${top - 6}`, ...stem }),
        h("circle", { cx: "23.6", cy: top - 7.4, r: "2", fill: leaf }),
        h("circle", { cx: "40.4", cy: top - 7.4, r: "2", fill: leaf }),
      );
    default:
      return null;
  }
}

function eyePair(t: Traits, mood: Mood, sealed: boolean, delay: string, cls: Cls): VNode {
  const dx = t.wide ? 9 : 7;
  const y = 33;
  if (sealed || mood === "sleepy") {
    // Closed: gentle downward arcs.
    return h(
      "g",
      { stroke: INK, strokeWidth: "1.8", strokeLinecap: "round", fill: "none" },
      h("path", { d: `M${32 - dx - 3} ${y} Q${32 - dx} ${y + 2.6} ${32 - dx + 3} ${y}` }),
      h("path", { d: `M${32 + dx - 3} ${y} Q${32 + dx} ${y + 2.6} ${32 + dx + 3} ${y}` }),
    );
  }
  if (mood === "happy" || (t.eyes === "kind" && mood === "idle")) {
    return h(
      "g",
      { stroke: INK, strokeWidth: "1.9", strokeLinecap: "round", fill: "none" },
      h("path", { d: `M${32 - dx - 3} ${y + 1} Q${32 - dx} ${y - 2.6} ${32 - dx + 3} ${y + 1}` }),
      h("path", { d: `M${32 + dx - 3} ${y + 1} Q${32 + dx} ${y - 2.6} ${32 + dx + 3} ${y + 1}` }),
    );
  }
  if (mood === "fooled") {
    // Dizzy little spirals.
    const spiral = (cx: number) => `M${cx} ${y} m-0.6 0 a0.6 0.6 0 1 1 1.2 0 a1.6 1.6 0 1 1 -3.2 0 a2.6 2.6 0 1 1 5.2 0`;
    return h(
      "g",
      { stroke: INK, strokeWidth: "1.2", fill: "none", strokeLinecap: "round" },
      h("path", { d: spiral(32 - dx) }),
      h("path", { d: spiral(32 + dx) }),
    );
  }
  const big = mood === "alert" ? 1.25 : 1;
  const blink = {
    className: cls("pf-blink"),
    style: cls("pf-blink") ? { animationDelay: delay, transformBox: "fill-box", transformOrigin: "center" } : undefined,
  };
  if (t.eyes === "visor") {
    return h(
      "g",
      null,
      h("rect", { x: 32 - dx - 5, y: y - 3.4, width: dx * 2 + 10, height: "6.8", rx: "3.4", fill: INK }),
      h(
        "g",
        blink,
        h("circle", { cx: 32 - dx, cy: y, r: 1.8 * big, fill: LIFE }),
        h("circle", { cx: 32 + dx, cy: y, r: 1.8 * big, fill: LIFE }),
      ),
      mood === "alert" && brows(dx, y - 6.5),
    );
  }
  return h(
    "g",
    null,
    h(
      "g",
      { ...blink, fill: INK },
      t.eyes === "oval"
        ? [
            h("ellipse", { cx: 32 - dx, cy: y, rx: 2.3 * big, ry: 3.3 * big }),
            h("ellipse", { cx: 32 + dx, cy: y, rx: 2.3 * big, ry: 3.3 * big }),
          ]
        : [h("circle", { cx: 32 - dx, cy: y, r: 2.7 * big }), h("circle", { cx: 32 + dx, cy: y, r: 2.7 * big })],
      h("circle", { cx: 32 - dx + 0.9, cy: y - 1, r: "0.8", fill: "#fff", opacity: "0.85" }),
      h("circle", { cx: 32 + dx + 0.9, cy: y - 1, r: "0.8", fill: "#fff", opacity: "0.85" }),
    ),
    mood === "alert" && brows(dx, y - 6),
  );
}

function brows(dx: number, y: number): VNode {
  return h(
    "g",
    { stroke: INK, strokeWidth: "1.6", strokeLinecap: "round" },
    h("path", { d: `M${32 - dx - 3} ${y - 1} L${32 - dx + 2.5} ${y + 1}` }),
    h("path", { d: `M${32 + dx + 3} ${y - 1} L${32 + dx - 2.5} ${y + 1}` }),
  );
}

function mouth(t: Traits, mood: Mood): VNode {
  const y = 42.5;
  const line = { stroke: INK, strokeWidth: 1.8, strokeLinecap: "round", fill: "none" };
  if (mood === "alert") return h("path", { d: `M28.5 ${y + 1} L35.5 ${y + 1}`, ...line });
  if (mood === "fooled") return h("path", { d: `M27 ${y + 1} q2.5 -2 5 0 t5 0`, ...line });
  if (mood === "happy") return h("path", { d: `M26.5 ${y - 1} Q32 ${y + 5.5} 37.5 ${y - 1} Z`, fill: INK });
  switch (t.mouth) {
    case "flat":
      return h("path", { d: `M28.5 ${y + 0.5} L35.5 ${y + 0.5}`, ...line });
    case "small":
      return h("circle", { cx: "32", cy: y + 0.5, r: "1.7", fill: INK });
    case "grin":
      return h("path", { d: `M27 ${y - 0.5} Q32 ${y + 4.6} 37 ${y - 0.5} Z`, fill: INK });
    default:
      return h("path", { d: `M28 ${y} Q32 ${y + 3.4} 36 ${y}`, ...line });
  }
}

function cheeks(t: Traits, sealed: boolean): VNode | null {
  if (t.cheeks === "none") return null;
  const o = sealed ? 0.15 : 0.4;
  if (t.cheeks === "blush")
    return h(
      "g",
      { fill: BLUSH, opacity: o },
      h("ellipse", { cx: "19.5", cy: "40", rx: "3", ry: "1.8" }),
      h("ellipse", { cx: "44.5", cy: "40", rx: "3", ry: "1.8" }),
    );
  const dots = [
    [18.5, 39.5],
    [21, 40.8],
    [19.2, 42],
    [45.5, 39.5],
    [43, 40.8],
    [44.8, 42],
  ];
  return h("g", { fill: INK, opacity: sealed ? 0.25 : 0.45 }, dots.map(([x, y]) => h("circle", { cx: x, cy: y, r: "0.6" })));
}

function pop(mood: Mood, cls: Cls): VNode | null {
  if (mood !== "alert" && mood !== "fooled") return null;
  const mark = mood === "alert" ? "!" : "?";
  return h(
    "g",
    { className: cls("pf-pop"), style: { transformOrigin: "52px 12px" } },
    h("circle", { cx: "52", cy: "12", r: "6.5", fill: mood === "alert" ? GILT : "#F5A524" }),
    h(
      "text",
      { x: "52", y: "15.6", textAnchor: "middle", fontSize: "10", fontWeight: "700", fill: INK, fontFamily: "ui-sans-serif, system-ui" },
      mark,
    ),
  );
}

function instinctMarks(n: number, dim: boolean): VNode | null {
  n = Math.floor(n);
  if (!(n > 0)) return null;
  const shown = Math.min(n, 5);
  const gap = 6.2;
  const x0 = 32 - ((shown - 1) * gap) / 2;
  return h(
    "g",
    { fill: GILT, opacity: dim ? 0.75 : 1 },
    Array.from({ length: shown }).map((_, i) => h("path", { d: `M${x0 + i * gap} 58 l2.4 2.4 l-2.4 2.4 l-2.4 -2.4z` })),
    n > shown &&
      h("text", { x: x0 + shown * gap + 1, y: "62.6", fontSize: "6.5", fill: GILT, fontFamily: "ui-monospace, monospace" }, "+", n - shown),
  );
}

// ---------------------------------------------------------------- helpers

function mix(a: string, b: string, k: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return `#${pa.map((v, i) => Math.round(v + (pb[i] - v) * k).toString(16).padStart(2, "0")).join("")}`;
}
