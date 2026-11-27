# Changelog

All notable changes to this package are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-28

Backwards compatible: nothing in 0.1.x changed behaviour, and the faces of every generation are identical.

### Added

- `familyTree(seed, generations, branches)`: a branching family as plain data (`TreeNode`), deterministic, every child one inherited change from its parent. Also `flattenTree` and `MAX_TREE_NODES` (a guard against trees that would not fit).
- `familyTreeSvg(treeOrSeed, options)`: a whole family tree as one standalone SVG string (save it as a picture, or rasterise it to PNG with any SVG tool).
- `faceDataUri(input, options)`: a face as a `data:image/svg+xml` URI for `<img>`, CSS and email.
- `background` option (and `FamilyFace` prop): a rounded tile behind the face, so the pale skins read on white pages and in light mode.
- `examples/` (plain HTML + Node, Vite + React), a `family-tree.svg` gallery, and a README rewritten as a front door: quick starts, API table, inheritance, customisation, accessibility, size, FAQ and a migration note for the Probate app.

## [0.1.1] - 2026-11-26

- Documentation only: a fuller README with install, usage and links, now that the package is on the public registry.

## [0.1.0] - 2026-11-25

First public release, extracted from the Probate monorepo (`packages/faces`).

### Added

- `faceSvg(input, options)`: a face as a standalone SVG string. No React, no DOM.
- `faceGlyphSvg`, `faceAlt`, `resolveFace`, `FACE_CSS` and the model (`traitsFor`,
  `mutation`, `resemblance`, `inheritedChange`, `describeTraits`, `hash`, trait lists).
- Family names: `traitsFor(gen, family)` derives a separate deterministic line of faces from
  any string. Without a family, the original Probate family is unchanged.
- `kinfaces/react`: `FamilyFace` and `FaceGlyph` (React 18+, optional peer dependency).
- `kinfaces/faces.css`: the animation rules (breathing, blinking, glint, mood pop), with
  `prefers-reduced-motion` support.
- ESM build with `.d.ts` types, `sideEffects: false`, no runtime dependencies.

### Changed

- Renamed from the private `@probate/faces`. `FamilyFace` and `FaceGlyph` now live in
  `kinfaces/react`; the main entry point is framework-free.
- Returned traits objects are frozen.
