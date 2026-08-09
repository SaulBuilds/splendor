# SPDX-License-Identifier: GPL-2.0-or-later
"""S0.2 acceptance test — the first PS1 retro shader (GPU palette quantization).

Runs on the REAL GPU inside Blender (Vulkan on this GB10):

    blender --background --factory-startup --python tests/splendor/test_s0_2_retro_shader.py

Exits non-zero on any failure. Acceptance (feeds S0.6): a palette set to 17 on a
"≤16" target is detectable by the deterministic scorer.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor.retro import quantize_image_gpu  # noqa: E402
from splendor.retro.palette import (  # noqa: E402
    count_colors, generate_palette, hue_ramp_rgba, quantize_cpu, rgb_from_rgba_flat,
)
from splendor_eval import EvalHarness, PaletteAdherence  # noqa: E402

_FAIL = []
W = 256


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def drawn_from_palette(rgb_pixels, palette, tol=1e-4):
    for c in rgb_pixels:
        d = min((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 + (c[2] - p[2]) ** 2 for p in palette)
        if d > tol:
            return False
    return True


def gpu_quantize_to(n):
    src = hue_ramp_rgba(W, 1)
    palette = generate_palette(n)
    out = quantize_image_gpu(src, W, 1, palette)
    return src, palette, rgb_from_rgba_flat(out)


def test_gpu_pass_quantizes_to_palette():
    print("[1] Real GPU pass quantizes a hue ramp to exactly N palette colors")
    src, palette, out_rgb = gpu_quantize_to(16)
    check(count_colors(out_rgb) == 16, f"output has exactly 16 distinct colors ({count_colors(out_rgb)})")
    check(drawn_from_palette(out_rgb, palette), "every output pixel is drawn from the palette (real quantization)")


def test_gpu_matches_cpu_reference():
    print("[2] GPU pass agrees with the CPU ground truth (correctness)")
    src, palette, out_rgb = gpu_quantize_to(16)
    cpu_rgb = quantize_cpu(rgb_from_rgba_flat(src), palette)
    check(count_colors(cpu_rgb) == count_colors(out_rgb) == 16, "GPU and CPU both yield 16 colors")
    # Per-pixel nearest index should match (compare against palette membership).
    mism = sum(1 for a, b in zip(out_rgb, cpu_rgb)
               if min(range(len(palette)), key=lambda j: sum((a[k] - palette[j][k]) ** 2 for k in range(3)))
               != min(range(len(palette)), key=lambda j: sum((b[k] - palette[j][k]) ** 2 for k in range(3))))
    check(mism == 0, f"GPU and CPU map every pixel to the same palette entry ({mism} mismatches)")


def test_deterministic():
    print("[3] Deterministic: same input → identical GPU output")
    src = hue_ramp_rgba(W, 1)
    pal = generate_palette(16)
    a = quantize_image_gpu(src, W, 1, pal)
    b = quantize_image_gpu(src, W, 1, pal)
    check(a == b, "two GPU runs produce bit-identical output")


def test_palette_cap_detectable_by_eval():
    print("[4] ACCEPTANCE / NEG CONTROL: palette 17 vs ≤16 is caught by the Eval SDK (feeds S0.6)")
    _s16, _p16, rgb16 = gpu_quantize_to(16)
    _s17, _p17, rgb17 = gpu_quantize_to(17)
    n16, n17 = count_colors(rgb16), count_colors(rgb17)
    check(n16 == 16 and n17 == 17, f"measurer counts {n16} vs {n17} colors")
    harness = EvalHarness([PaletteAdherence(16)])
    ok = harness.evaluate({"palette_colors": n16}, "retro-16", seed=0)
    bad = harness.evaluate({"palette_colors": n17}, "retro-17", seed=0)
    check(ok.passed_all, "16-color output PASSES PaletteAdherence(16)")
    check(not bad.passed_all, "17-color output FAILS PaletteAdherence(16) — the cap is enforced + measured")


def main():
    for t in (test_gpu_pass_quantizes_to_palette, test_gpu_matches_cpu_reference,
              test_deterministic, test_palette_cap_detectable_by_eval):
        t()
    print()
    code = 1 if _FAIL else 0
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
    else:
        print("RESULT: PASS — S0.2 GPU retro palette-quantization pass verified (Vulkan, GB10)")
    # Headless Vulkan GPU-context teardown segfaults on Blender/interpreter exit
    # (a backend/driver quirk at context destruction, not in Splendor or this
    # test — all checks above ran to completion first). Hard-exit with the real
    # code after flushing so CI sees the actual result, not the teardown crash.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


if __name__ == "__main__":
    main()
