// familyTree, familyTreeSvg, faceDataUri and the background option, via the built package.
import { test } from "node:test";
import assert from "node:assert/strict";
import { familyTree, familyTreeSvg, flattenTree, faceDataUri, faceSvg, traitsFor, MAX_TREE_NODES } from "../dist/index.js";

const KEYS = ["head", "eyes", "mouth", "crown", "cheeks", "skin", "wide"];
const diff = (a, b) => KEYS.filter((k) => a[k] !== b[k]);

test("familyTree is deterministic, sized right, and the founder matches traitsFor", () => {
  const t = familyTree("ada", 4, 2);
  assert.deepEqual(JSON.parse(JSON.stringify(t)), JSON.parse(JSON.stringify(familyTree("ada", 4, 2))));
  assert.equal(flattenTree(t).length, 1 + 2 + 4 + 8);
  assert.deepEqual(t.traits, traitsFor(1, "ada"));
  assert.equal(familyTree(undefined, 1).id, "1");
  assert.notDeepEqual(familyTree("ada", 3).children[0].traits, familyTree("bob", 3).children[0].traits);
});

test("every child differs from its parent in exactly the trait it reports", () => {
  for (const seed of ["ada", "grace", undefined, 7]) {
    const walk = (n) => {
      for (const c of n.children) {
        assert.equal(c.gen, n.gen + 1);
        assert.deepEqual(diff(n.traits, c.traits), [c.changed], `${seed} ${c.id}`);
        walk(c);
      }
    };
    walk(familyTree(seed, 5, 3));
  }
});

test("siblings are not all the same, and per-generation branches work", () => {
  const t = familyTree("ada", 4, [3, 1]);
  assert.equal(t.children.length, 3);
  assert.equal(t.children[0].children.length, 1);
  const kids = familyTree("ada", 2, 6).children.map((c) => JSON.stringify(c.traits));
  assert.ok(new Set(kids).size > 1);
});

test("bad input is clamped and absurd sizes are refused", () => {
  assert.equal(flattenTree(familyTree("x", NaN, 0)).length, 1);
  assert.equal(flattenTree(familyTree("x", 3, -2)).length, 3);
  assert.throws(() => familyTree("x", 30, 4), RangeError);
  assert.ok(MAX_TREE_NODES > 100);
});

test("familyTreeSvg is a standalone, accessible svg", () => {
  const svg = familyTreeSvg("ada", { generations: 3, branches: 2, title: "The Ada family" });
  assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
  assert.match(svg, /role="img" aria-label="The Ada family"/);
  assert.equal(svg, familyTreeSvg(familyTree("ada", 3, 2), { title: "The Ada family" }));
  assert.equal((svg.match(/scale\(/g) ?? []).length, 7);
  assert.match(familyTreeSvg("ada"), /aria-hidden="true"/);
  assert.match(familyTreeSvg("ada", { title: 'a"<b' }), /a&quot;&lt;b/);
});

test("faceDataUri round-trips and background draws a tile", () => {
  const uri = faceDataUri(3, { title: "Gen 3" });
  assert.ok(uri.startsWith("data:image/svg+xml;charset=utf-8,"));
  assert.equal(decodeURIComponent(uri.split(",").slice(1).join(",")), faceSvg(3, { title: "Gen 3" }));
  assert.match(faceSvg(3, { background: "#0A0E17" }), /<rect width="64" height="64" rx="14" fill="#0A0E17"\/>/);
  assert.doesNotMatch(faceSvg(3), /<rect width="64"/);
});
