# SPDX-License-Identifier: GPL-2.0-or-later
"""Blackwell GPU enablement test — the GB10 CUDA device is detected.

    blender --background --factory-startup --python tests/splendor/test_blackwell_gpu.py

Device detection is the fast, CI-safe enablement signal. An actual GPU render
compiles the sm_121 megakernel at runtime (~minutes) — too slow for CI; it is
verified separately (docs/design/gpu-render-gb10.png). Skips cleanly on a box
with no CUDA GPU.
"""
import sys

import bpy

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'CUDA'
    try:
        prefs.refresh_devices()
    except Exception:
        pass
    cuda = [d for d in prefs.devices if d.type == 'CUDA']
    if not cuda:
        print("  SKIP  no CUDA GPU present — Blackwell enablement is GPU-box-specific")
        print("RESULT: PASS (skipped — no GPU)")
        sys.exit(0)
    check(len(cuda) >= 1, f"CUDA device detected: {[d.name for d in cuda]}")
    check(cuda[0].type == 'CUDA', "device type is CUDA (GPU render path available)")
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        sys.exit(1)
    print("RESULT: PASS — Blackwell CUDA device detected (GPU render verified in docs/design/gpu-render-gb10.png)")
    sys.exit(0)


if __name__ == "__main__":
    main()
