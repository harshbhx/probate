// Family faces as pure data: no React, no DOM.
//
// Gen 1's face comes from a fixed seed. Every child copies its parent's face and changes
// exactly one trait, so the family resembles itself down the line and every generation is
// still its own person. Same inputs, same face, in every app.

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

/** Which trait changed between a parent and generation `gen`, and to what. */
export function mutation(gen: number, parent: Traits): { trait: TraitName; value: Traits[TraitName] } {
  const trait = WEIGHTED[hash("trait", gen) % WEIGHTED.length];
  const opts = options(trait).filter((v) => v !== parent[trait]);
  const value = opts[hash("value", gen) % opts.length] as Traits[TraitName];
  return { trait, value };
}

const cache = new Map<number, Traits>();

/** The face of generation `gen` (1-based): the founder, then one inherited change per generation. */
export function traitsFor(gen: number): Traits {
  if (gen <= 1) return FOUNDER;
  const hit = cache.get(gen);
  if (hit) return hit;
  // Walk up from the founder; faster than recursion for long families.
  let t = FOUNDER;
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
    const { trait, value } = mutation(g, t);
    t = { ...t, [trait]: value };
    cache.set(g, t);
  }
  return t;
}

/** How many traits two generations share, out of 7: the family resemblance. */
export function resemblance(a: number, b: number): number {
  const ta = traitsFor(a);
  const tb = traitsFor(b);
  return TRAIT_NAMES.filter((k) => ta[k] === tb[k]).length;
}

/** Plain words for what a child got that its parent didn't have. */
export function inheritedChange(gen: number): string | null {
  if (gen <= 1) return null;
  const { trait } = mutation(gen, traitsFor(gen - 1));
  const words: Record<TraitName, string> = {
    head: "a new head shape",
    eyes: "new eyes",
    mouth: "a new smile",
    crown: "a new crown",
    cheeks: "new cheeks",
    skin: "a new colour",
    wide: "wider-set eyes",
  };
  if (trait === "wide" && !traitsFor(gen).wide) return "closer-set eyes";
  return words[trait];
}
