import { test } from "node:test";
import assert from "node:assert/strict";
import { FOUNDER, mutation, resemblance, traitsFor } from "./model.ts";

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
