// Clean dist, compile with tsc (JS + .d.ts), then write dist/faces.css from the one source of
// truth (FACE_CSS in src/svg.ts), so the stylesheet and the embedded <style> never drift.
// Run through npm (`npm run build`) so node_modules/.bin is on PATH.
import { rmSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
rmSync(join(root, "dist"), { recursive: true, force: true });
execSync("tsc -p .", { stdio: "inherit", cwd: root });
const { FACE_CSS } = await import(pathToFileURL(join(root, "dist", "svg.js")).href);
writeFileSync(join(root, "dist", "faces.css"), FACE_CSS);
console.log("built dist/");
