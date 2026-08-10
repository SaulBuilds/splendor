# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-P7 — the Publish to Gallery operator, end-to-end in the product.

    blender --background --factory-startup --python tests/splendor/test_spl_web_gallery_ui.py

Builds a real retro image, sets scene provenance, runs the publish operator, and
checks it produced a content-addressed page (a real IPFS CID + gateway URL) or failed
honestly with no daemon — never a fabricated URL.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import bpy  # noqa: E402
import splendor_harness  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    splendor_harness.register()
    scene = bpy.context.scene
    try:
        # A real image datablock as the piece.
        W = H = 16
        img = bpy.data.images.new("Splendor Retro", W, H, alpha=True)
        img.pixels = [c for _ in range(W * H) for c in (0.55, 0.80, 0.035, 1.0)]
        img.update()
        scene.splendor_retro_last = "Splendor Retro"
        scene.splendor_prompt = "PS1 health potion, dithered"
        scene.splendor_palette_size = 16
        scene.splendor_eval_score = 0.94
        scene.splendor_eval_passed = True
        scene.splendor_eval_tris = 120
        scene.splendor_ship_cid = "sha256:deadbeef"

        r = bpy.ops.splendor.publish_gallery('EXEC_DEFAULT')
        check(r == {'FINISHED'}, "publish operator finished")
        url = scene.splendor_gallery_url
        if scene.splendor_gallery_cid:
            check(url.endswith(scene.splendor_gallery_cid) and "/ipfs/" in url,
                  f"published → content-addressed IPFS URL ({url[:52]}…)")
        else:
            check("unreachable" in url, f"no daemon → honest failure, no fake URL ({url[:52]}…)")
    finally:
        splendor_harness.unregister()

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — Publish to Gallery verified (content-addressed page, honest when offline)")
    sys.exit(0)


if __name__ == "__main__":
    main()
