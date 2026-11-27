// Regenerates gallery.svg from the built package: `npm run build && npm run gallery`.
import { writeFileSync } from "node:fs";
import { buildGallery } from "./gallery-lib.mjs";

writeFileSync(new URL("../gallery.svg", import.meta.url), buildGallery());
console.log("wrote gallery.svg");

// A 4-generation family with two children per person, for the README.
import { familyTreeSvg } from "../dist/index.js";
writeFileSync(
  new URL("../family-tree.svg", import.meta.url),
  familyTreeSvg("ada", { generations: 4, branches: 2, background: "#0A0E17", title: "Four generations of the Ada family, two children each" }),
);
console.log("wrote family-tree.svg");
