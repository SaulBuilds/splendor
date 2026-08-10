---
created: 2026-08-09
branch: feat/spl-p1-retro-engine
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# SPL-P1 — the Retro Engine (the PS1 look)

The product's core visual identity, built as **real, governed features** — not a filter
bolted on the side. Two passes, each wired to a verified seam.

## Geometry pass (governed)
Through the single governed action API (invariant I-1) + the HIC gate:
- **`FlatShade`** (`dsl.FlatShade`, class `geometry`) — hard per-face normals (faceting).
- **`SnapVertices`** (existing) — low-precision vertex snap (the PS1 wobble).
- **`SetPalette`** — the hard colour cap the image pass enforces.

`SPLENDOR_OT_retro_shade` composes all three. Because they run through the gate, HIC-1
blocks them before the mesh is touched (verified: `test_spl_p1_retro_engine.py [2]`).

## Image pass (pure Python, deterministic)
`splendor.retro.postprocess` — the PlayStation-era frame, composable via `retro_frame`:
1. **`pixelate`** — nearest-neighbour low-res framebuffer (chunky pixels).
2. **`dither_quantize`** — ordered (Bayer 2/4/8) dithering to the palette. The signature
   cross-hatch: a flat mid-tone breaks into the palette instead of banding
   (`test_spl_p1_retro_image.py [2]` proves it vs. plain quantize).
3. **`reduce_color_depth`** — optional RGB555 (15-bit) truncation.

`SPLENDOR_OT_retro_render` runs it over a render (or any image) → a `Splendor Retro`
image datablock. Exposed in the **Retro Engine (PS1)** sub-panel with Pixelate / Dither /
Spread controls.

## Verified
- `test_spl_p1_retro_image.py` — pure pipeline: Bayer validity, dither-vs-quantize,
  block-uniform pixelation, depth truncation, palette cap.
- `test_spl_p1_retro_engine.py` — governed faceting/snap through the gate, the Retro
  Shade + Retro Render operators on the real binary.
- Visual proof: `spl-p1-retro.png` (a faceted, snapped Suzanne rendered then run through
  the pipeline — pixelated, dithered, 13 colours under a 16-colour cap) vs.
  `spl-p1-original.png`.

## Still open (honest)
- **Affine (perspective-incorrect) texture warp** — the swimming-texture hallmark. Needs a
  per-vertex UV/W shader in EEVEE; scoped as the next P1 step, not in this seam.
- The image pass is CPU (deterministic, testable); a GPU path can reuse `retro/gpu_pass.py`.
