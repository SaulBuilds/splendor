# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-P7 — the multi-piece gallery flow in the product.

    blender --background --factory-startup --python tests/splendor/test_spl_gallery_index_ui.py

Adds two real image pieces to the gallery collection, then publishes the index and
checks it produced a content-addressed index URL over IPFS (or failed honestly with
no daemon). Never fabricates a URL.
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


def _mk_image(name, rgba):
    img = bpy.data.images.new(name, 8, 8, alpha=True)
    img.pixels = [c for _ in range(8 * 8) for c in rgba]
    img.update()
    return img


def main():
    splendor_harness.register()
    scene = bpy.context.scene
    try:
        print("[1] Publish with an empty gallery → refuses honestly")
        r = bpy.ops.splendor.publish_index('EXEC_DEFAULT')
        check(r == {'CANCELLED'}, "empty gallery → CANCELLED (no fake index)")

        print("[2] Add two pieces to the gallery collection")
        _mk_image("Splendor Retro", (0.55, 0.80, 0.035, 1.0))
        scene.splendor_retro_last = "Splendor Retro"
        scene.splendor_prompt = "PS1 health potion"
        scene.splendor_palette_size = 16
        scene.splendor_eval_score = 0.94
        scene.splendor_eval_passed = True
        bpy.ops.splendor.gallery_add('EXEC_DEFAULT')

        _mk_image("Splendor Affine", (0.80, 0.20, 0.10, 1.0))
        scene.splendor_retro_last = "Splendor Affine"
        scene.splendor_prompt = "low-poly rusty sword"
        scene.splendor_palette_size = 8
        bpy.ops.splendor.gallery_add('EXEC_DEFAULT')
        check(len(scene.splendor_gallery_items) == 2, "two pieces accumulated in the collection")

        print("[3] Publish the gallery index")
        r = bpy.ops.splendor.publish_index('EXEC_DEFAULT')
        check(r == {'FINISHED'}, "publish_index finished")
        url = scene.splendor_gallery_index_url
        if scene.splendor_gallery_index_cid:
            check(url.endswith(scene.splendor_gallery_index_cid) and "/ipfs/" in url,
                  f"content-addressed index URL ({url[:52]}…)")
            # The index page references both pieces.
            from splendor.deploy import IpfsPinning
            page = IpfsPinning().fetch(scene.splendor_gallery_index_cid).decode("utf-8")
            check(page.count('href="/ipfs/') == 2, "index links both pieces via relative /ipfs/ paths")
        else:
            check("unreachable" in url, f"no daemon → honest failure, no fake URL ({url[:52]}…)")

        print("[4] Clear resets the collection")
        bpy.ops.splendor.gallery_clear('EXEC_DEFAULT')
        check(len(scene.splendor_gallery_items) == 0 and not scene.splendor_gallery_index_cid,
              "gallery cleared")
    finally:
        splendor_harness.unregister()

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — multi-piece gallery index verified (collect → publish → linked index)")
    sys.exit(0)


if __name__ == "__main__":
    main()
