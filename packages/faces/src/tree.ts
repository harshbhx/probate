// Family trees: one founder, several children per person, every child one inherited change
// away from its parent. Pure data plus an SVG-string exporter, no DOM and no React.
import { mutation, traitsFor, type Traits, type TraitName } from "./model.js";
import { faceGlyphSvg, type FaceOptions } from "./svg.js";

export interface TreeNode {
  /** Stable path id: "1" for the founder, "1.2" for its second child, "1.2.1", ... */
  id: string;
  /** Generation, 1 for the founder. */
  gen: number;
  traits: Traits;
  /** The one trait this person changed relative to their parent (null for the founder). */
  changed: TraitName | null;
  children: TreeNode[];
}

/** The most people one tree may hold. A tree of 4 branches over 8 generations would not fit. */
export const MAX_TREE_NODES = 5000;

/**
 * A branching family. `seed` is a family name (a number is read as its decimal string);
 * leave it undefined for the built-in founder. `branches` is how many children each person
 * has: one number for every generation, or an array giving it per generation (the last entry
 * repeats). Same arguments, same tree, on every machine. The founder equals
 * `traitsFor(1, seed)`, and every child differs from its parent in exactly one trait.
 */
export function familyTree(
  seed: string | number | undefined,
  generations: number,
  branches: number | readonly number[] = 2,
): TreeNode {
  const family = seed === undefined ? undefined : String(seed);
  const gens = Math.max(1, Math.floor(Number.isFinite(generations) ? generations : 1));
  const per = (depth: number): number => {
    const raw = typeof branches === "number" ? branches : (branches[Math.min(depth, branches.length - 1)] ?? 1);
    return Math.max(1, Math.floor(Number.isFinite(raw) ? raw : 1));
  };
  let total = 1;
  for (let d = 1, width = 1; d < gens; d++) {
    width *= per(d - 1);
    total += width;
    if (total > MAX_TREE_NODES) {
      throw new RangeError(`familyTree: more than ${MAX_TREE_NODES} people; use fewer generations or branches`);
    }
  }
  const salt = family === undefined ? "kin" : `${family}/kin`;
  const grow = (node: TreeNode): void => {
    if (node.gen >= gens) return;
    for (let i = 1; i <= per(node.gen - 1); i++) {
      const id = `${node.id}.${i}`;
      const { trait, value } = mutation(node.gen + 1, node.traits, `${salt}/${id}`);
      const child: TreeNode = {
        id,
        gen: node.gen + 1,
        traits: Object.freeze({ ...node.traits, [trait]: value }) as Traits,
        changed: trait,
        children: [],
      };
      node.children.push(child);
      grow(child);
    }
  };
  const root: TreeNode = { id: "1", gen: 1, traits: traitsFor(1, family), changed: null, children: [] };
  grow(root);
  return root;
}

/** Every person in the tree, parents before children (depth-first). */
export function flattenTree(root: TreeNode): TreeNode[] {
  const out: TreeNode[] = [];
  const walk = (n: TreeNode) => {
    out.push(n);
    n.children.forEach(walk);
  };
  walk(root);
  return out;
}

export interface TreeSvgOptions extends Pick<FaceOptions, "title" | "background" | "className"> {
  /** Pixel size of each face. Default 48. */
  faceSize?: number;
  /** Space between faces. Default 12. */
  gap?: number;
  /** Colour of the lines from parent to child. Default "#8C95AB". */
  lineColor?: string;
  /** Add the pf-* animation classes and an embedded style. Default false. */
  animate?: boolean;
  /** Used when the first argument is not already a tree. Default 4. */
  generations?: number;
  /** Used when the first argument is not already a tree. Default 2. */
  branches?: number | readonly number[];
}

/**
 * The whole tree as one standalone `<svg>` string: the thing to save as an image of a family,
 * or to convert to PNG with any SVG rasteriser. Pass a tree from `familyTree`, or a seed
 * (with `generations` and `branches` in the options). A `title` makes it an image with a
 * name; without one it is decorative.
 */
export function familyTreeSvg(root: TreeNode | string | number | undefined, opts: TreeSvgOptions = {}): string {
  const { faceSize = 48, gap = 12, lineColor = "#8C95AB", title, className, background, animate = false, generations = 4, branches = 2 } = opts;
  const tree = typeof root === "object" ? root : familyTree(root, generations, branches);
  const cell = faceSize + gap;
  const rowH = faceSize + gap * 2;
  const pos = new Map<TreeNode, { x: number; y: number }>();
  let leaf = 0;
  let depth = 0;
  const place = (n: TreeNode, d: number): number => {
    depth = Math.max(depth, d);
    const x = n.children.length ? mean(n.children.map((c) => place(c, d + 1))) : leaf++ * cell + faceSize / 2;
    pos.set(n, { x, y: d * rowH + faceSize / 2 });
    return x;
  };
  place(tree, 0);
  const width = Math.max(leaf, 1) * cell - gap;
  const height = depth * rowH + faceSize;
  const k = faceSize / 64;
  let lines = "";
  let faces = "";
  for (const [n, p] of pos) {
    for (const c of n.children) {
      const q = pos.get(c)!;
      const y1 = p.y + faceSize / 2;
      const y2 = q.y - faceSize / 2;
      const m = (y1 + y2) / 2;
      lines += `<path d="M${r(p.x)} ${r(y1)}C${r(p.x)} ${r(m)} ${r(q.x)} ${r(m)} ${r(q.x)} ${r(y2)}"/>`;
    }
    const bg = background ? `<rect width="64" height="64" rx="14" fill="${esc(background)}"/>` : "";
    faces += `<g transform="translate(${r(p.x - faceSize / 2)} ${r(p.y - faceSize / 2)}) scale(${r(k)})">${bg}${faceGlyphSvg(n.traits, { animate })}</g>`;
  }
  const attrs =
    `xmlns="http://www.w3.org/2000/svg" width="${r(width)}" height="${r(height)}" viewBox="0 0 ${r(width)} ${r(height)}"` +
    (className ? ` class="${esc(className)}"` : "") +
    (title ? ` role="img" aria-label="${esc(title)}"` : ` aria-hidden="true"`);
  return `<svg ${attrs}>${title ? `<title>${esc(title)}</title>` : ""}<g fill="none" stroke="${esc(lineColor)}" stroke-width="1.5">${lines}</g>${faces}</svg>`;
}

const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
const r = (n: number) => Math.round(n * 100) / 100;
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
