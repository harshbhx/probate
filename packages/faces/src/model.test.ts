import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { FACE_WINDOW, FOUNDER, HEADS, SKINS, inheritedChange, mutation, resemblance, traitsFor } from "./model.ts";

test("gen 1 is the founder", () => {
  assert.deepEqual(traitsFor(1), FOUNDER);
});

test("every child differs from its parent in exactly one trait", () => {
  for (let g = 2; g <= 60; g++) {
    assert.equal(resemblance(g, g - 1), 6, `gen ${g}`);
  }
});

test("faces are deterministic", () => {
  const a = JSON.stringify(Array.from({ length: 30 }, (_, i) => traitsFor(i + 1)));
  const b = JSON.stringify(Array.from({ length: 30 }, (_, i) => traitsFor(i + 1)));
  assert.equal(a, b);
});

test("a mutation always changes the trait", () => {
  for (let g = 2; g <= 60; g++) {
    const parent = traitsFor(g - 1);
    const m = mutation(g, parent);
    assert.notEqual(parent[m.trait], m.value);
  }
});

test("the family drifts: by gen 12 most faces are distinct", () => {
  const seen = new Set(Array.from({ length: 12 }, (_, i) => JSON.stringify(traitsFor(i + 1))));
  assert.ok(seen.size >= 10, `only ${seen.size} distinct faces`);
});

test("no face repeats within any window of FACE_WINDOW consecutive generations", () => {
  for (const family of [undefined, "probate", "Ada"]) {
    for (let g = 1; g <= 400; g++) {
      for (let h = g + 1; h < g + FACE_WINDOW; h++) {
        assert.notDeepEqual(traitsFor(g, family), traitsFor(h, family), `${family}: gens ${g} and ${h}`);
      }
    }
  }
});

test("children still differ from their parent by exactly one trait after the window fix", () => {
  for (const family of [undefined, "probate"]) {
    for (let g = 2; g <= 400; g++) assert.equal(resemblance(g, g - 1, family), 6, `${family} gen ${g}`);
  }
});

test("inheritedChange names a change for every generation", () => {
  for (let g = 2; g <= 120; g++) assert.ok(inheritedChange(g), `gen ${g}`);
});

test("every name in config/names.yaml has a face (name n is generation n), within the window", () => {
  const yaml = readFileSync(new URL("../../../config/names.yaml", import.meta.url), "utf8");
  const names = [...yaml.matchAll(/^- \{name:\s*(\w+),/gm)].map((m) => m[1]);
  assert.ok(names.length >= 120, `only ${names.length} names`);
  assert.equal(new Set(names.map((n) => n.toLowerCase())).size, names.length);
  // Past the list the names repeat with a numeral; faces keep going by generation number.
  const last = names.length * 2 + 5;
  for (let g = 1; g <= last; g++) {
    const t = traitsFor(g);
    assert.ok(HEADS.includes(t.head) && SKINS[t.skin], `gen ${g} has no face`);
  }
  for (let g = 1; g + FACE_WINDOW - 1 <= last; g++) {
    const faces = new Set(Array.from({ length: FACE_WINDOW }, (_, i) => JSON.stringify(traitsFor(g + i))));
    assert.equal(faces.size, FACE_WINDOW, `window starting at gen ${g}`);
  }
});
