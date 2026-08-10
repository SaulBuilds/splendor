# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-P1 — affine texture mapping (the PS1 "swimming texture").

    python3 tests/splendor/test_spl_p1_affine.py

The proof is a controlled comparison against a perspective-correct reference: on
screen-parallel geometry the two are identical (nothing to warp); the instant a
triangle tilts in depth, affine interpolation diverges — that divergence *is* the
swim. Deterministic and mock-free.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor.retro.raster import checker_sampler, image_sampler, rasterize  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def _quad(iw_top, iw_bot):
    """A textured quad (two tris). `iw_*` are 1/w at the top / bottom edges —
    equal ⇒ screen-parallel; unequal ⇒ tilted in depth."""
    tl = (8, 8, iw_top, 0.0, 0.0)
    tr = (56, 8, iw_top, 1.0, 0.0)
    br = (56, 56, iw_bot, 1.0, 1.0)
    bl = (8, 56, iw_bot, 0.0, 1.0)
    return [(tl, tr, br), (tl, br, bl)]


def _diff(a, b):
    return sum(1 for i in range(0, len(a), 4) if a[i:i + 4] != b[i:i + 4])


def main():
    W = H = 64
    samp = checker_sampler(8)

    print("[1] Screen-parallel geometry: affine == perspective-correct (no warp)")
    par = _quad(1.0, 1.0)
    aff = rasterize(par, W, H, samp, perspective_correct=False)
    pc = rasterize(par, W, H, samp, perspective_correct=True)
    check(aff == pc, "affine and perspective agree exactly on a parallel quad")

    print("[2] Tilted-in-depth geometry: affine diverges — the swim")
    obl = _quad(0.3, 1.0)
    aff_o = rasterize(obl, W, H, samp, perspective_correct=False)
    pc_o = rasterize(obl, W, H, samp, perspective_correct=True)
    d = _diff(aff_o, pc_o)
    check(d > 100, f"affine differs from perspective on an oblique quad ({d} px swim)")
    check(aff_o == rasterize(obl, W, H, samp, perspective_correct=False), "affine is deterministic")

    print("[3] The divergence is the perspective term: affine UV is screen-linear")
    # At the vertical mid-scanline, the affine v is exactly 0.5 (screen-linear),
    # while perspective-correct v is pulled toward the near (bottom) edge (> 0.5).
    from splendor.retro.raster import rasterize as _r  # local alias for clarity
    # Instrument a single tall triangle: near-bottom, far-top.
    tri = [((32, 4, 0.25, 0.5, 0.0), (12, 60, 1.0, 0.0, 1.0), (52, 60, 1.0, 1.0, 1.0))]

    def capture(u_v_sink):
        def sample(u, v):
            u_v_sink.append((u, v))
            return (0.0, 0.0, 0.0, 1.0)
        return sample

    aff_uv, pc_uv = [], []
    _r(tri, W, H, capture(aff_uv), perspective_correct=False)
    _r(tri, W, H, capture(pc_uv), perspective_correct=True)
    aff_mid = sum(v for (_u, v) in aff_uv) / len(aff_uv)
    pc_mid = sum(v for (_u, v) in pc_uv) / len(pc_uv)
    check(pc_mid > aff_mid + 1e-3,
          f"perspective V is pulled toward the near edge ({pc_mid:.3f} > affine {aff_mid:.3f})")

    print("[4] image_sampler wraps and reads a real texture buffer")
    tex = [1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]  # 2×2 RGBA
    s = image_sampler(tex, 2, 2)
    check(s(0.0, 0.0) == (1.0, 0.0, 0.0, 1.0), "samples texel (0,0)")
    check(s(1.25, 0.0) == s(0.25, 0.0), "u wraps modulo 1.0")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — affine texture mapping verified (parallel == PC, tilt ⇒ swim)")
    sys.exit(0)


if __name__ == "__main__":
    main()
