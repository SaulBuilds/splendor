# SPDX-License-Identifier: GPL-2.0-or-later
"""Retro palette generation, a CPU reference quantizer, and a color measurer.

Pure Python (no bpy/gpu) so it runs anywhere: it generates the target palette,
provides the ground-truth CPU quantization the GPU pass is checked against, and
measures how many distinct colors an image actually has — the measurement that
feeds the Eval SDK's ``PaletteAdherence`` (S0.6). PS1-era art lived under hard
palette caps; this is the seam that enforces and measures that.
"""
from __future__ import annotations

import colorsys


def generate_palette(n: int):
    """A deterministic n-color retro palette: n evenly spaced full-sat hues."""
    n = max(1, int(n))
    palette = []
    for i in range(n):
        r, g, b = colorsys.hsv_to_rgb(i / n, 1.0, 1.0)
        palette.append((round(r, 6), round(g, 6), round(b, 6)))
    return palette


def _nearest(color, palette):
    best, best_d = palette[0], 1e18
    for p in palette:
        d = (color[0] - p[0]) ** 2 + (color[1] - p[1]) ** 2 + (color[2] - p[2]) ** 2
        if d < best_d:
            best_d, best = d, p
    return best


def quantize_cpu(rgb_pixels, palette):
    """Ground-truth nearest-color quantization (list of (r,g,b) -> list)."""
    return [_nearest(c, palette) for c in rgb_pixels]


def rgb_from_rgba_flat(rgba_flat):
    """Flat [r,g,b,a, r,g,b,a, ...] -> [(r,g,b), ...]."""
    out = []
    for i in range(0, len(rgba_flat), 4):
        out.append((rgba_flat[i], rgba_flat[i + 1], rgba_flat[i + 2]))
    return out


def count_colors(rgb_pixels, precision: int = 5) -> int:
    """Distinct colors at a fixed precision — the palette-adherence measurement."""
    return len({(round(r, precision), round(g, precision), round(b, precision))
                for (r, g, b) in rgb_pixels})


def hue_ramp_rgba(width: int, height: int = 1):
    """A test image: a full hue ramp across the width (flat RGBA), so quantizing
    to N palette hues exercises all N entries."""
    px = []
    for _y in range(height):
        for x in range(width):
            r, g, b = colorsys.hsv_to_rgb(x / max(1, width), 1.0, 1.0)
            px += [r, g, b, 1.0]
    return px
