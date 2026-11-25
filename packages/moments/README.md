# @probate/moments

Five one-shot pixel art moments, made with [pixelfx](https://github.com/patch-gg/pixelfx) (MIT, by patch-gg; its
simulation core adapts Hugo Duprez's Sprite Fusion effects, MIT):

| Moment | pixelfx effect | Palette | When it plays |
| --- | --- | --- | --- |
| `convicted` | `impacts/blunt-hit` | verdict reds | the court's stamp lands on a convicted item |
| `instinct` | `pickups/collect-burst` | gilt | the family learns a new instinct; also the newest card on the Instincts page |
| `death` | `spawn/soul-rise` | moon and silver | a dead generation's face, the first time it is in view on its page |
| `birth` | `spawn/spawn-portal` | gilt | the newest living generation's face on Home, once in view |
| `resisted` | `holy/divine-shield` | life green | the stamp on an approved or contested item in a trial, quieter than `convicted` |

The sprite strips live in each app's `public/moments/` (quantized PNG, about 15 KB each). To re-export them from a
pixelfx checkout:

```bash
node tools/render.mjs impacts/blunt-hit --sheet --opts '{"palette":["#3a0d10","#7a1d22","#c9343a","#ff6b6b","#ffd6d6"]}'
node tools/render.mjs pickups/collect-burst --sheet --opts '{"palette":["#3b2a0e","#7a5a20","#b8913f","#d9b46a","#fff4d6"]}'
```

The v6 lifecycle strips were rendered the same way with `--no-actor` and these palettes:

```bash
node tools/render.mjs spawn/soul-rise --sheet --no-actor --opts '{"palette":["#14141c","#3a3a52","#6b6b8a","#a9a9c4","#ecebf5"]}'
node tools/render.mjs spawn/spawn-portal --sheet --no-actor --opts '{"palette":["#3b2a0e","#7a5a20","#b8913f","#d9b46a","#fff4d6"]}'
node tools/render.mjs holy/divine-shield --sheet --no-actor --opts '{"palette":["#0d2a1f","#1f5c43","#3f9a6e","#8fd1a8","#e9f7d9"]}'
```

then cut each sheet's grid into one horizontal strip (frame size and count are in the sheet's JSON). The lifecycle
strips keep every 2nd frame (`death`, `resisted`, 15 fps) or every 3rd (`birth`, 10 fps), end before the trailing
empty frames, and are quantized to 8 to 12 colours (about 24 KB each, `birth` about 49 KB because it is wider).
`death` and `birth` adapt Sprite Fusion effects, already credited in `NOTICE-pixelfx.md`. The strips live in
`apps/web/public/moments/` only; the site does not use the new ones.

Rules (docs/04-DESIGN.md): each moment plays once, only when it means something, never loops, and never plays
under reduced motion.
