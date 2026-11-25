// The package as published: exports map, files, stylesheet, types. Uses the package's own name
// (self-reference) so it goes through the real exports map.
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const url = (p) => new URL(`../${p}`, import.meta.url);

test("metadata is publishable", () => {
  assert.equal(pkg.name, "kinfaces");
  assert.ok(!pkg.private);
  assert.equal(pkg.license, "MIT");
  assert.equal(pkg.sideEffects, false);
  assert.equal(pkg.type, "module");
  assert.ok(pkg.engines?.node);
  assert.ok(pkg.repository?.url && pkg.bugs?.url && pkg.homepage);
  assert.equal(pkg.peerDependenciesMeta?.react?.optional, true);
  assert.equal(pkg.dependencies, undefined, "no runtime dependencies");
});

test("every export target exists", () => {
  for (const [key, target] of Object.entries(pkg.exports)) {
    const files = typeof target === "string" ? [target] : Object.values(target);
    for (const f of files) assert.ok(existsSync(url(f)), `${key} -> ${f}`);
  }
  for (const f of ["README.md", "LICENSE", "CHANGELOG.md", "gallery.svg"]) assert.ok(existsSync(url(f)), f);
});

test("self-import through the exports map", async () => {
  const core = await import("kinfaces");
  const react = await import("kinfaces/react");
  assert.equal(typeof core.faceSvg, "function");
  assert.equal(typeof core.traitsFor, "function");
  assert.equal(typeof react.FamilyFace, "function");
  assert.equal(core.FamilyFace, undefined, "react stays out of the main entry");
});

test("faces.css matches FACE_CSS", async () => {
  const { FACE_CSS } = await import("kinfaces");
  assert.equal(readFileSync(url("dist/faces.css"), "utf8"), FACE_CSS);
});

test("type declarations are emitted and use no .ts import paths", () => {
  for (const f of ["index", "model", "svg", "react", "render"]) {
    const d = readFileSync(url(`dist/${f}.d.ts`), "utf8");
    assert.ok(!/from "\.\/[a-z]+\.ts"/.test(d), `${f}.d.ts`);
  }
  assert.match(readFileSync(url("dist/index.d.ts"), "utf8"), /faceSvg/);
});

test("the react build keeps its use-client directive", () => {
  assert.match(readFileSync(url("dist/react.js"), "utf8"), /^"use client";/);
});

test("the committed gallery matches what the package generates", async () => {
  const { buildGallery } = await import("../scripts/gallery-lib.mjs");
  // Ignore CRLF from Windows checkouts.
  assert.equal(readFileSync(url("gallery.svg"), "utf8").replaceAll("
", "
"), buildGallery());
});
