// Family faces as pure data: no React, no DOM.
//
// Gen 1's face comes from a fixed seed. Every child copies its parent's face and changes
// exactly one trait, so the family resembles itself down the line and every generation is
// still its own person. Same inputs, same face, in every app.
//
// Without a `family`, the founder is the built-in FOUNDER and generations follow the
// original sequence. With a `family` string, the founder and every mutation are derived from
// hash(family, ...), so each family name is its own deterministic line of faces.

export const HEADS = ["round", "squircle", "tall", "wide"] as const;
export const EYES = ["dot", "oval", "kind", "visor"] as const;
export const MOUTHS = ["smile", "flat", "small", "grin"] as const;
export const CROWNS = ["sprout", "none", "antenna", "twin"] as const;
export const CHEEKS = ["none", "blush", "freckles"] as const;
// Muted tones that sit well on the night background. Index 0 is Gen 1's.
export const SKINS = ["#C9D3E8", "#D8CDB6", "#B9D6CB", "#D3C6DA", "#DDC8B8", "#C3D2D8"] as const;

export type Head = (typeof HEADS)[number];
export type Eyes = (typeof EYES)[number];
export type Mouth = (typeof MOUTHS)[number];
export type Crown = (typeof CROWNS)[number];
export type Cheeks = (typeof CHEEKS)[number];

export interface Traits {
  head: Head;
  eyes: Eyes;
  mouth: Mouth;
  crown: Crown;
  cheeks: Cheeks;
  skin: number; // index into SKINS
  wide: boolean; // eye spacing
}

export type TraitName = keyof Traits;
const TRAIT_NAMES: TraitName[] = ["head", "eyes", "mouth", "crown", "cheeks", "skin", "wide"];
// How likely each trait is to be the one that changes: colour, head and crown most, so the
// family visibly drifts while staying recognisable.
const WEIGHTS: Record<TraitName, number> = { skin: 3, head: 2, crown: 2, eyes: 2, mouth: 2, cheeks: 1, wide: 1 };
const WEIGHTED: TraitName[] = TRAIT_NAMES.flatMap((t) => Array<TraitName>(WEIGHTS[t]).fill(t));

/** How the face looks right now. Life state first, then a passing mood. */
export type Life = "unborn" | "alive" | "sealed";
export type Mood = "idle" | "happy" | "alert" | "fooled" | "sleepy";

export const FOUNDER: Traits = {
  head: "squircle",
  eyes: "dot",
  mouth: "smile",
  crown: "sprout",
  cheeks: "blush",
  skin: 0,
  wide: false,
};

/** A small, stable integer hash (FNV-1a), so faces never depend on Math.random. */
export function hash(...parts: (string | number)[]): number {
  let h = 0x811c9dc5;
  for (const ch of parts.join("|")) {
    h ^= ch.codePointAt(0)!;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

export type Family = string | undefined;

/** FNV-1a mixes its low bits poorly (short names would collide mod 4), so family-derived
 * choices pass the hash through a murmur3-style finaliser first. The default family does not
 * use this, which keeps its faces identical to what they have always been. */
function famHash(...parts: (string | number)[]): number {
  let h = hash(...parts);
  h ^= h >>> 16;
  h = Math.imul(h, 0x85ebca6b) >>> 0;
  h ^= h >>> 13;
  h = Math.imul(h, 0xc2b2ae35) >>> 0;
  h ^= h >>> 16;
  return h >>> 0;
}

/** The founder of a family: the built-in one, or one derived from the family name. */
export function founderFor(family?: Family): Traits {
  if (!family) return FOUNDER;
  const pick = <T>(name: string, list: readonly T[]): T => list[famHash(family, "founder", name) % list.length];
  return {
    head: pick("head", HEADS),
    eyes: pick("eyes", EYES),
    mouth: pick("mouth", MOUTHS),
    crown: pick("crown", CROWNS),
    cheeks: pick("cheeks", CHEEKS),
    skin: famHash(family, "founder", "skin") % SKINS.length,
    wide: famHash(family, "founder", "wide") % 2 === 1,
  };
}

function options(t: TraitName): readonly (string | number | boolean)[] {
  switch (t) {
    case "head":
      return HEADS;
    case "eyes":
      return EYES;
    case "mouth":
      return MOUTHS;
    case "crown":
      return CROWNS;
    case "cheeks":
      return CHEEKS;
    case "skin":
      return SKINS.map((_, i) => i);
    case "wide":
      return [false, true];
  }
}

/** No face repeats within this many consecutive generations. */
export const FACE_WINDOW = 10;

const faceKey = (t: Traits): string => TRAIT_NAMES.map((n) => String(t[n])).join("/");

/**
 * Which trait changed between a parent and generation `gen`, and to what. `recent` is the faces
 * of the generations just before `gen`; a change that would repeat one of them is re-rolled
 * (deterministically), so no face repeats inside a FACE_WINDOW. The first roll is unchanged,
 * so every face that never collided keeps its look.
 */
export function mutation(
  gen: number,
  parent: Traits,
  family?: Family,
  recent: readonly Traits[] = [],
): { trait: TraitName; value: Traits[TraitName] } {
  const salt = family ? [family] : [];
  const hh = family ? famHash : hash;
  const taken = new Set(recent.map(faceKey));
  const roll = (n: number) => {
    const extra = n === 0 ? [] : [n];
    const trait = WEIGHTED[hh(...salt, "trait", gen, ...extra) % WEIGHTED.length];
    const opts = options(trait).filter((v) => v !== parent[trait]);
    const value = opts[hh(...salt, "value", gen, ...extra) % opts.length] as Traits[TraitName];
    return { trait, value };
  };
  const first = roll(0);
  const fresh = (m: { trait: TraitName; value: Traits[TraitName] }) =>
    !taken.has(faceKey({ ...parent, [m.trait]: m.value } as Traits));
  if (fresh(first)) return first;
  for (let n = 1; n <= 64; n++) {
    const m = roll(n);
    if (fresh(m)) return m;
  }
  // Exhaustive fallback: the first unused single-trait change.
  for (const trait of TRAIT_NAMES) {
    for (const value of options(trait)) {
      if (value === parent[trait]) continue;
      const m = { trait, value: value as Traits[TraitName] };
      if (fresh(m)) return m;
    }
  }
  return first;
}

const caches = new Map<string, Map<number, Traits>>();

/**
 * The face of generation `gen` (1-based): the founder, then one inherited change per generation.
 * Pass a `family` name for a different, equally deterministic line of faces.
 */
export function traitsFor(gen: number, family?: Family): Traits {
  const founder = founderFor(family);
  gen = Math.max(1, Math.floor(Number.isFinite(gen) ? gen : 1));
  if (gen <= 1) return founder;
  const key = family ?? "";
  let cache = caches.get(key);
  if (!cache) caches.set(key, (cache = new Map()));
  const hit = cache.get(gen);
  if (hit) return hit;
  // Walk up from the founder; faster than recursion for long families.
  let t = founder;
  let start = 2;
  for (let g = gen - 1; g >= 2; g--) {
    const c = cache.get(g);
    if (c) {
      t = c;
      start = g + 1;
      break;
    }
  }
  for (let g = start; g <= gen; g++) {
    const recent: Traits[] = [];
    for (let r = Math.max(1, g - FACE_WINDOW + 1); r < g; r++) recent.push(r === 1 ? founder : cache.get(r)!);
    const { trait, value } = mutation(g, t, family, recent);
    t = Object.freeze({ ...t, [trait]: value }) as Traits;
    cache.set(g, t);
  }
  return t;
}

/** How many traits two generations share, out of 7: the family resemblance. */
export function resemblance(a: number, b: number, family?: Family): number {
  const ta = traitsFor(a, family);
  const tb = traitsFor(b, family);
  return TRAIT_NAMES.filter((k) => ta[k] === tb[k]).length;
}

/** Plain words for what a child got that its parent didn't have. */
export function inheritedChange(gen: number, family?: Family): string | null {
  if (gen <= 1) return null;
  const recent: Traits[] = [];
  for (let r = Math.max(1, gen - FACE_WINDOW + 1); r < gen; r++) recent.push(traitsFor(r, family));
  const { trait } = mutation(gen, traitsFor(gen - 1, family), family, recent);
  const words: Record<TraitName, string> = {
    head: "a new head shape",
    eyes: "new eyes",
    mouth: "a new smile",
    crown: "a new crown",
    cheeks: "new cheeks",
    skin: "a new colour",
    wide: "wider-set eyes",
  };
  if (trait === "wide" && !traitsFor(gen, family).wide) return "closer-set eyes";
  return words[trait];
}

/** A plain-language description of a face, for alt text and aria-labels. */
export function describeTraits(t: Traits): string {
  const head: Record<Head, string> = { round: "round", squircle: "rounded-square", tall: "tall", wide: "wide" };
  const eyes: Record<Eyes, string> = { dot: "dot eyes", oval: "oval eyes", kind: "kind curved eyes", visor: "a dark visor over the eyes" };
  const mouth: Record<Mouth, string> = { smile: "a smile", flat: "a flat mouth", small: "a small round mouth", grin: "a grin" };
  const crown: Record<Crown, string> = {
    sprout: "a green sprout on top",
    none: "nothing on top",
    antenna: "a gold-tipped antenna",
    twin: "twin antennae",
  };
  const cheeks: Record<Cheeks, string> = { none: "", blush: ", blushing cheeks", freckles: ", freckles" };
  return `${head[t.head]}-headed face with ${eyes[t.eyes]}${t.wide ? " set wide apart" : ""}, ${mouth[t.mouth]}, ${crown[t.crown]}${cheeks[t.cheeks]}`;
}
