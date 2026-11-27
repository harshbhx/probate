// Node, no framework: write one SVG per generation and one picture of a whole family tree.
//   npm install kinfaces && node make-avatars.mjs
import { mkdirSync, writeFileSync } from "node:fs";
import { faceSvg, familyTree, familyTreeSvg, flattenTree, inheritedChange } from "kinfaces";

mkdirSync("out", { recursive: true });

for (let gen = 1; gen <= 6; gen++) {
  writeFileSync(`out/ada-gen-${gen}.svg`, faceSvg("ada", { gen, size: 128, background: "#0A0E17", title: `Ada, generation ${gen}` }));
  console.log(`gen ${gen}:`, inheritedChange(gen, "ada") ?? "the founder");
}

// A whole family in one image: 4 generations, 2 children each.
writeFileSync("out/ada-family.svg", familyTreeSvg("ada", { generations: 4, branches: 2, background: "#0A0E17", title: "The Ada family" }));

// Or walk the tree yourself.
const tree = familyTree("ada", 3, 2);
console.log(flattenTree(tree).map((p) => `${p.id} (gen ${p.gen})${p.changed ? " changed " + p.changed : ""}`).join("\n"));

// PNG: any SVG rasteriser works, for example `npm i @resvg/resvg-js`:
//   import { Resvg } from "@resvg/resvg-js";
//   writeFileSync("out/ada-family.png", new Resvg(svg, { fitTo: { mode: "width", value: 1024 } }).render().asPng());
