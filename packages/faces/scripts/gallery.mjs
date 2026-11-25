// Regenerates gallery.svg from the built package: `npm run build && npm run gallery`.
import { writeFileSync } from "node:fs";
import { buildGallery } from "./gallery-lib.mjs";

writeFileSync(new URL("../gallery.svg", import.meta.url), buildGallery());
console.log("wrote gallery.svg");
