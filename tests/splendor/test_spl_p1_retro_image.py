# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-P1 — the PS1 image pipeline (pure Python, no bpy/gpu).

    python3 tests/splendor/test_spl_p1_retro_image.py

Behavioural, not incidental: the dither test proves ordered dithering actually
happens (a flat mid-tone field breaks into the palette cross-hatch, where plain
nearest-colour quantization would leave one solid block).
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor.retro import (  # noqa: E402
    bayer_matrix, dither_quantize, pixelate, reduce_color_depth, retro_frame,
)
from splendor.retro.palette import (  # noqa: E402
    count_colors, generate_palette, quantize_cpu, rgb_from_rgba_flat,
)

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    print("[1] Bayer matrix is a valid ordered-dither matrix")
    for n in (2, 4, 8):
        m = bayer_matrix(n)
        flat = sorted(v for row in m for v in row)
        check(flat == list(range(n * n)), f"bayer({n}) is a permutation of 0..{n*n-1}")
    try:
        bayer_matrix(3)
        check(False, "bayer(3) should reject non-power-of-two")
    except ValueError:
        check(True, "bayer(non-power-of-two) rejected")

    print("[2] Ordered dithering: a flat mid-tone breaks into the palette (vs. a solid block)")
    pal = [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]
    W = H = 8
    mid = [(0.5, 0.5, 0.5)] * (W * H)
    plain = quantize_cpu(mid, pal)
    dith = dither_quantize(mid, pal, W, H, bayer_n=4, spread=1.0)
    check(count_colors(plain) == 1, "plain quantize → 1 solid color (hard band)")
    check(count_colors(dith) == 2, "dither → both palette colors (cross-hatch)")
    check(set(dith) <= set(pal), "dither output ⊆ palette")
    check(dith == dither_quantize(mid, pal, W, H, bayer_n=4, spread=1.0), "dither is deterministic")

    print("[3] Pixelate: low-res framebuffer — each block is uniform")
    rgba = []
    for y in range(H):
        for x in range(W):
            rgba += [x / (W - 1), y / (H - 1), 0.0, 1.0]
    pix = pixelate(rgba, W, H, 4)

    def block_uniform(buf, w, f):
        for y in range(0, H, f):
            for x in range(0, w, f):
                base = buf[(y * w + x) * 4:(y * w + x) * 4 + 4]
                for dy in range(f):
                    for dx in range(f):
                        i = ((y + dy) * w + (x + dx)) * 4
                        if buf[i:i + 4] != base:
                            return False
        return True

    check(block_uniform(pix, W, 4), "factor-4 pixelate → uniform 4×4 blocks")
    check(pixelate(rgba, W, H, 1) == list(rgba), "factor-1 pixelate is identity")

    print("[4] Color-depth reduction (RGB555 family)")
    rd = reduce_color_depth([(0.51, 0.23, 0.99)], bits=1)[0]
    check(all(v in (0.0, 1.0) for v in rd), "bits=1 truncates each channel to {0,1}")
    rd5 = reduce_color_depth([(0.333, 0.777, 0.5)], bits=5)[0]
    check(all(abs(v * 31 - round(v * 31)) < 1e-9 for v in rd5), "bits=5 snaps to 32 levels")

    print("[5] retro_frame end-to-end honors the palette cap")
    pal16 = generate_palette(16)
    out = retro_frame(rgba, W, H, pal16, pixel_factor=2, bayer_n=4)
    check(len(out) == len(rgba), "output buffer same size as input")
    check(set(rgb_from_rgba_flat(out)) <= set(pal16), "every output color is in the 16-color palette")
    check(count_colors(rgb_from_rgba_flat(out)) <= 16, "≤ 16 distinct colors (hard PS1 palette cap)")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — PS1 image pipeline verified (dither, pixelate, depth, palette cap)")
    sys.exit(0)


if __name__ == "__main__":
    main()
