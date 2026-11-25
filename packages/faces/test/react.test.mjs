// The React entry point: SSR output, parity with the string renderer, no-React core.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createElement as e } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { FaceGlyph, FamilyFace } from "../dist/react.js";
import { faceGlyphSvg } from "../dist/index.js";

const norm = (s) => s.replace(/<([a-zA-Z]+)([^>]*?)\/>/g, "<$1$2></$1>");

test("FamilyFace renders on the server and is decorative without a title", () => {
  const html = renderToStaticMarkup(e(FamilyFace, { gen: 3 }));
  assert.match(html, /^<svg /);
  assert.match(html, /aria-hidden="true"/);
  assert.match(html, /width="64" height="64"/);
});

test("FamilyFace with a title is an accessible image", () => {
  const html = renderToStaticMarkup(e(FamilyFace, { gen: 3, title: "Ada, generation 3", size: 96 }));
  assert.match(html, /role="img"/);
  assert.match(html, /aria-label="Ada, generation 3"/);
  assert.match(html, /width="96"/);
  assert.ok(!html.includes("aria-hidden"));
});

test("React and string renderers draw the same face", () => {
  for (const gen of [1, 2, 5, 9, 12, 30]) {
    for (const mood of ["idle", "happy", "alert", "fooled", "sleepy"]) {
      for (const life of ["alive", "sealed", "unborn"]) {
        const react = norm(renderToStaticMarkup(e("svg", null, e(FaceGlyph, { gen, mood, life, instincts: gen % 7 }))));
        const str = norm(faceGlyphSvg(gen, { mood, life, instincts: gen % 7, animate: true }));
        assert.equal(react, `<svg>${str}</svg>`, `${gen} ${mood} ${life}`);
      }
    }
  }
});

test("family and traits props work in React", () => {
  const a = renderToStaticMarkup(e(FamilyFace, { gen: 2, family: "ada" }));
  const b = renderToStaticMarkup(e(FamilyFace, { gen: 2, family: "bob" }));
  assert.notEqual(a, b);
});

test("the framework-free entry never imports react", () => {
  for (const f of ["index.js", "model.js", "svg.js", "render.js"]) {
    const src = readFileSync(new URL(`../dist/${f}`, import.meta.url), "utf8");
    assert.ok(!/from\s+["']react/.test(src), `${f} imports react`);
  }
});
