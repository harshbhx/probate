// Framework-free entry point: the model and the SVG string renderer. No React.
export * from "./model.js";
export {
  FACE_CSS,
  faceAlt,
  faceDataUri,
  faceGlyphSvg,
  faceSvg,
  resolveFace,
  type FaceInput,
  type FaceOptions,
  type ResolvedFace,
} from "./svg.js";
export {
  MAX_TREE_NODES,
  familyTree,
  familyTreeSvg,
  flattenTree,
  type TreeNode,
  type TreeSvgOptions,
} from "./tree.js";
