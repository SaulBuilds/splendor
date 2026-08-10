# SPDX-License-Identifier: GPL-2.0-or-later
"""Affine texture rasterizer (P1) — the PS1 "swimming texture" done for real.

Affine texture mapping is a *rasterization-time* effect: the console interpolated
UVs **linearly in screen space** and never did the per-pixel perspective divide, so
textures warp and swim across large triangles at oblique angles. You can't recover
that from a finished perspective-correct render (the information is gone), and node
materials can't express a `noperspective` varying — so the honest way to get the
authentic look is to rasterize it ourselves, exactly as the hardware did.

Pure Python (no bpy/gpu), deterministic. The caller supplies triangles already
projected to screen space as `((sx, sy, inv_w, u, v), ×3)` and a texture `sample(u,
v) -> (r,g,b,a)`. `perspective_correct=True` switches to the modern reference used as
the negative control in tests — the two agree on screen-parallel geometry and diverge
(the swim) the moment a triangle tilts in depth.
"""
from __future__ import annotations


def _bbox(t, width, height):
    xs = (t[0][0], t[1][0], t[2][0])
    ys = (t[0][1], t[1][1], t[2][1])
    return (max(0, int(min(xs))), min(width - 1, int(max(xs)) + 1),
            max(0, int(min(ys))), min(height - 1, int(max(ys)) + 1))


def checker_sampler(cells: int = 8, a=(0.05, 0.05, 0.06, 1.0), b=(0.9, 0.85, 0.2, 1.0)):
    """A procedural checker texture in UV space — makes the affine warp legible."""
    def sample(u, v):
        return a if (int(u * cells) + int(v * cells)) % 2 == 0 else b
    return sample


def image_sampler(pixels, tex_w, tex_h, wrap: bool = True):
    """Sample a flat RGBA buffer (row-major) with nearest-neighbour at (u, v)."""
    def sample(u, v):
        if wrap:
            u -= int(u); v -= int(v)
            if u < 0:
                u += 1.0
            if v < 0:
                v += 1.0
        else:
            u = min(1.0, max(0.0, u)); v = min(1.0, max(0.0, v))
        x = min(tex_w - 1, int(u * tex_w)); y = min(tex_h - 1, int(v * tex_h))
        i = (y * tex_w + x) * 4
        return (pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3])
    return sample


def rasterize(triangles, width, height, sample, perspective_correct: bool = False,
              background=(0.0, 0.0, 0.0, 1.0)):
    """Rasterize `triangles` into a flat RGBA buffer of size `width*height*4`.

    Each triangle is `((sx, sy, inv_w, u, v), ×3)` — screen coords, 1/w for the depth
    test (and perspective-correct UVs), and texture coordinates. Affine by default:
    UVs are interpolated with the raw screen-space barycentrics. With
    `perspective_correct`, UVs are weighted by 1/w and renormalised — the correct-but-
    un-retro reference.
    """
    fb = list(background) * (width * height)
    depth = [-1e30] * (width * height)
    for tri in triangles:
        (x0, y0, iw0, u0, v0), (x1, y1, iw1, u1, v1), (x2, y2, iw2, u2, v2) = tri
        area = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(area) < 1e-12:
            continue
        minx, maxx, miny, maxy = _bbox(tri, width, height)
        for py in range(miny, maxy + 1):
            fy = py + 0.5
            for px in range(minx, maxx + 1):
                fx = px + 0.5
                w0 = ((y1 - y2) * (fx - x2) + (x2 - x1) * (fy - y2)) / area
                w1 = ((y2 - y0) * (fx - x2) + (x0 - x2) * (fy - y2)) / area
                w2 = 1.0 - w0 - w1
                if w0 < 0.0 or w1 < 0.0 or w2 < 0.0:
                    continue
                iw = w0 * iw0 + w1 * iw1 + w2 * iw2  # screen-linear 1/w = depth key
                idx = py * width + px
                if iw <= depth[idx]:
                    continue
                depth[idx] = iw
                if perspective_correct:
                    inv = 1.0 / iw if iw != 0.0 else 0.0
                    u = (w0 * u0 * iw0 + w1 * u1 * iw1 + w2 * u2 * iw2) * inv
                    v = (w0 * v0 * iw0 + w1 * v1 * iw1 + w2 * v2 * iw2) * inv
                else:
                    u = w0 * u0 + w1 * u1 + w2 * u2  # affine: raw screen-linear UV
                    v = w0 * v0 + w1 * v1 + w2 * v2
                r, g, b, a = sample(u, v)
                fb[idx * 4:idx * 4 + 4] = [r, g, b, a]
    return fb
