# Changelog

All notable changes to this package are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

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
