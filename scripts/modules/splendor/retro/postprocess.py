# SPDX-License-Identifier: GPL-2.0-or-later
"""The PS1 image pipeline (P1) — ordered dithering, pixelation, colour-depth cut.

Pure Python (no bpy/gpu) so it runs anywhere and is deterministic under test. These
are the *image-side* effects of the retro engine; the geometry side (vertex snap,
flat/faceted shading) lives in the DSL (:mod:`splendor.dsl`). Composed by
:func:`retro_frame`, they turn a normal render into a PlayStation-era frame:

  1. **pixelate** — sample a low-resolution framebuffer with nearest neighbour, the
     chunky low-res look (PS1 rendered ~320×240, point-sampled).
  2. **dither_quantize** — ordered (Bayer) dithering to a hard palette cap. The
     signature cross-hatch gradient of 15-bit consoles under a tight palette.
  3. **reduce_color_depth** — optional RGB555 (15-bit) channel truncation.

The palette + nearest-colour ground truth come from :mod:`splendor.retro.palette`.
"""
from __future__ import annotations

from .palette import _nearest, rgb_from_rgba_flat


def bayer_matrix(n: int):
    """The n×n ordered-dither (Bayer) matrix, n a power of two, values 0…n²−1."""
    if n < 1 or (n & (n - 1)) != 0:
        raise ValueError("bayer_matrix size must be a power of two")
    if n == 1:
        return [[0]]
    half = bayer_matrix(n // 2)
    h = n // 2
    m = [[0] * n for _ in range(n)]
    for y in range(h):
        for x in range(h):
            v = half[y][x] * 4
            m[y][x] = v + 0
            m[y][x + h] = v + 2
            m[y + h][x] = v + 3
            m[y + h][x + h] = v + 1
    return m


def _threshold(matrix, n, x, y):
    """The signed dither threshold at (x, y), in [-0.5, 0.5)."""
    return (matrix[y % n][x % n] + 0.5) / (n * n) - 0.5


def dither_quantize(rgb_pixels, palette, width, height, bayer_n: int = 4, spread: float = 0.12):
    """Ordered-dither `rgb_pixels` (a row-major list of (r,g,b)) to `palette`.

    Each pixel is nudged by its Bayer threshold × `spread` before snapping to the
    nearest palette colour, so smooth gradients break into the palette's cross-hatch
    instead of hard banding. Deterministic: same input → same output.
    """
    matrix = bayer_matrix(bayer_n)
    out = []
    for idx, (r, g, b) in enumerate(rgb_pixels):
        x, y = idx % width, idx // width
        t = _threshold(matrix, bayer_n, x, y) * spread
        out.append(_nearest((r + t, g + t, b + t), palette))
    return out


def pixelate(rgba_flat, width: int, height: int, factor: int):
    """Nearest-neighbour downsample→upsample: each `factor`×`factor` block becomes
    the block's top-left pixel — the crisp, point-sampled low-res PS1 framebuffer."""
    factor = max(1, int(factor))
    if factor == 1:
        return list(rgba_flat)
    out = [0.0] * len(rgba_flat)
    for y in range(height):
        by = (y // factor) * factor
        for x in range(width):
            bx = (x // factor) * factor
            si, di = (by * width + bx) * 4, (y * width + x) * 4
            out[di:di + 4] = rgba_flat[si:si + 4]
    return out


def reduce_color_depth(rgb_pixels, bits: int = 5):
    """Truncate each channel to 2^`bits` levels (default RGB555 — 15-bit console)."""
    levels = (1 << max(1, int(bits))) - 1
    return [(round(r * levels) / levels, round(g * levels) / levels, round(b * levels) / levels)
            for (r, g, b) in rgb_pixels]


def rgb_to_rgba_flat(rgb_pixels, alpha: float = 1.0):
    """[(r,g,b), …] → flat [r,g,b,a, …]."""
    out = []
    for (r, g, b) in rgb_pixels:
        out += [r, g, b, alpha]
    return out


def retro_frame(rgba_flat, width: int, height: int, palette,
                pixel_factor: int = 4, bayer_n: int = 4, spread: float = 0.12, depth_bits: int = 0):
    """The full PS1 image pipeline on a flat RGBA buffer → flat RGBA buffer.

    pixelate → (optional colour-depth cut) → ordered dither to `palette`. `depth_bits`
    of 0 skips the truncation (the palette cap already bounds colour).
    """
    pix = pixelate(rgba_flat, width, height, pixel_factor)
    rgb = rgb_from_rgba_flat(pix)
    if depth_bits:
        rgb = reduce_color_depth(rgb, depth_bits)
    dithered = dither_quantize(rgb, palette, width, height, bayer_n=bayer_n, spread=spread)
    return rgb_to_rgba_flat(dithered)
