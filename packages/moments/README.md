# @probate/moments

Two one-shot pixel art moments, made with [pixelfx](https://github.com/patch-gg/pixelfx) (MIT, by patch-gg; its
simulation core adapts Hugo Duprez's Sprite Fusion effects, MIT):

| Moment | pixelfx effect | Palette | When it plays |
| --- | --- | --- | --- |
| `convicted` | `impacts/blunt-hit` | verdict reds | the court's stamp lands on a convicted item |
| `instinct` | `pickups/collect-burst` | gilt | the family learns a new instinct |

The sprite strips live in each app's `public/moments/` (quantized PNG, about 15 KB each). To re-export them from a
pixelfx checkout:

```bash
node tools/render.mjs impacts/blunt-hit --sheet --opts '{"palette":["#3a0d10","#7a1d22","#c9343a","#ff6b6b","#ffd6d6"]}'
node tools/render.mjs pickups/collect-burst --sheet --opts '{"palette":["#3b2a0e","#7a5a20","#b8913f","#d9b46a","#fff4d6"]}'
```

then cut each sheet's grid into one horizontal strip (frame size and count are in the sheet's JSON).

Rules (docs/04-DESIGN.md): each moment plays once, only when it means something, never loops, and never plays
under reduced motion.
