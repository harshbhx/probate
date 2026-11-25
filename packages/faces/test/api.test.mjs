// Public API, exercised through the built package (dist), the way a consumer sees it.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  FACE_CSS,
  FOUNDER,
  describeTraits,
  faceAlt,
  faceGlyphSvg,
  faceSvg,
  inheritedChange,
  resemblance,
  resolveFace,
  traitsFor,
} from "../dist/index.js";

test("faceSvg is deterministic and standalone", () => {
  const a = faceSvg(7);
  assert.equal(a, faceSvg(7));
  assert.match(a, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" width="64" height="64" viewBox="0 0 64 64"/);
  assert.ok(a.endsWith("</svg>"));
  assert.notEqual(a, faceSvg(8));
});

test("number, family name and traits inputs", () => {
  assert.equal(faceSvg(1), faceSvg(FOUNDER));
  assert.equal(faceSvg(1), faceSvg(traitsFor(1)));
  assert.equal(faceSvg("ada"), faceSvg("ada", { gen: 1 }));
  assert.notEqual(faceSvg("ada"), faceSvg("bob"));
  assert.notEqual(faceSvg("ada", { gen: 1 }), faceSvg("ada", { gen: 4 }));
  assert.deepEqual(resolveFace("ada", 3).traits, traitsFor(3, "ada"));
});

test("a family name is its own line, and inheritance holds inside it", () => {
  for (const family of ["ada", "grace", "probate", "x"]) {
    for (let g = 2; g <= 40; g++) {
      assert.equal(resemblance(g, g - 1, family), 6, `${family} gen ${g}`);
    }
    assert.ok(inheritedChange(2, family));
    assert.equal(inheritedChange(1, family), null);
  }
  assert.notDeepEqual(traitsFor(1, "ada"), traitsFor(1, "grace"));
});

test("the default family is pinned: adding families did not change gens 1-12", () => {
  const sig = (t) => [t.head, t.eyes, t.mouth, t.crown, t.cheeks, t.skin, t.wide ? 1 : 0].join("/");
  assert.deepEqual(
    Array.from({ length: 12 }, (_, i) => sig(traitsFor(i + 1))),
    [
      "squircle/dot/smile/sprout/blush/0/0",
      "round/dot/smile/sprout/blush/0/0",
      "round/dot/smile/sprout/blush/0/1",
      "round/dot/smile/none/blush/0/1",
      "round/dot/smile/twin/blush/0/1",
      "round/dot/smile/twin/blush/1/1",
      "round/dot/smile/twin/freckles/1/1",
      "round/dot/smile/antenna/freckles/1/1",
      "round/dot/small/antenna/freckles/1/1",
      "squircle/dot/small/antenna/freckles/1/1",
      "tall/dot/small/antenna/freckles/1/1",
      "tall/kind/small/antenna/freckles/1/1",
    ],
  );
});

test("traits are frozen and gen is sanitised", () => {
  assert.ok(Object.isFrozen(traitsFor(5)));
  assert.deepEqual(traitsFor(0), traitsFor(1));
  assert.deepEqual(traitsFor(-3), traitsFor(1));
  assert.deepEqual(traitsFor(Number.NaN), traitsFor(1));
  assert.deepEqual(traitsFor(3.9), traitsFor(3));
});

test("accessibility: decorative by default, labelled with a title", () => {
  const plain = faceSvg(2);
  assert.match(plain, /aria-hidden="true"/);
  assert.ok(!plain.includes("role="));
  const named = faceSvg(2, { title: "Ada, generation 2", desc: "A friendly face" });
  assert.match(named, /role="img"/);
  assert.match(named, /aria-label="Ada, generation 2"/);
  assert.match(named, /<title>Ada, generation 2<\/title>/);
  assert.match(named, /<desc>A friendly face<\/desc>/);
  assert.ok(!named.includes("aria-hidden"));
});

test("titles are escaped", () => {
  const s = faceSvg(1, { title: `<b>"x" & y</b>` });
  assert.ok(!s.includes("<b>"));
  assert.match(s, /&lt;b&gt;&quot;x&quot; &amp; y&lt;\/b&gt;/);
});

test("faceAlt and describeTraits give plain words", () => {
  assert.equal(faceAlt(1), describeTraits(FOUNDER));
  assert.match(faceAlt(1), /rounded-square-headed face with dot eyes, a smile, a green sprout on top, blushing cheeks/);
  assert.equal(faceAlt("ada", { gen: 3 }), describeTraits(traitsFor(3, "ada")));
});

test("options: size, life, mood, instincts, animate", () => {
  assert.match(faceSvg(1, { size: 120 }), /width="120" height="120"/);
  assert.ok(faceSvg(1, { life: "unborn" }).includes('opacity="0.18"'));
  assert.notEqual(faceSvg(1, { life: "sealed" }), faceSvg(1));
  assert.notEqual(faceSvg(1, { mood: "alert" }), faceSvg(1));
  assert.ok(faceSvg(1, { mood: "alert" }).includes(">!</text>"));
  assert.ok(faceSvg(1, { mood: "fooled" }).includes(">?</text>"));
  assert.ok(faceSvg(1, { instincts: 8 }).includes("+3"));
  assert.ok(!faceSvg(1).includes("pf-"), "static by default");
  const anim = faceSvg(1, { animate: true });
  assert.ok(anim.includes("pf-breathe") && anim.includes("<style>"));
  assert.ok(anim.includes("prefers-reduced-motion"));
});

test("every face is balanced markup with no undefined or NaN", () => {
  for (let g = 1; g <= 40; g++) {
    for (const mood of ["idle", "happy", "alert", "fooled", "sleepy"]) {
      for (const life of ["alive", "sealed", "unborn"]) {
        const s = faceSvg(g, { mood, life, instincts: g % 7, animate: g % 2 === 0 });
        assert.ok(!/undefined|NaN|null/.test(s), `${g} ${mood} ${life}`);
        const tags = [...s.matchAll(/<(\/?)([a-z]+)[^>]*?(\/?)>/g)];
        const stack = [];
        for (const [, closing, name, selfClose] of tags) {
          if (selfClose) continue;
          if (closing) assert.equal(stack.pop(), name, `${g} ${mood} ${life}`);
          else stack.push(name);
        }
        assert.equal(stack.length, 0, `${g} ${mood} ${life}`);
      }
    }
  }
});

test("faceGlyphSvg has no outer svg and FACE_CSS has the keyframes", () => {
  const g = faceGlyphSvg(3);
  assert.ok(g.startsWith("<g") && !g.includes("<svg"));
  assert.ok(FACE_CSS.includes("@keyframes pf-breathe"));
});

test("sixty faces in the default family do not collapse into a few", () => {
  const seen = new Set(Array.from({ length: 60 }, (_, i) => faceSvg(i + 1)));
  assert.ok(seen.size >= 50, `only ${seen.size}`);
});

test("family names give varied founders (short names do not collide)", () => {
  const names = Array.from({ length: 100 }, (_, i) => `family-${i}`).concat(["a", "b", "c", "x", "y", "z", "ada", "grace"]);
  const seen = new Set(names.map((n) => JSON.stringify(traitsFor(1, n))));
  assert.ok(seen.size >= 90, `only ${seen.size} distinct founders in ${names.length}`);
});
