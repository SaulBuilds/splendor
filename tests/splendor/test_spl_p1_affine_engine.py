# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-P1 — the affine render operator on a real mesh + camera.

    blender --background --factory-startup --python tests/splendor/test_spl_p1_affine_engine.py

Projects an angled, textured plane through the scene camera and rasterizes it with
the affine rasterizer — proving the bpy projection wiring feeds the (separately
unit-tested) rasterizer and yields a real textured image. Then confirms the affine
result differs from a perspective-correct rasterization of the *same* projected
geometry (the swim), on the real binary.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import bpy  # noqa: E402
from mathutils import Euler  # noqa: E402
import splendor_harness  # noqa: E402
from splendor.retro import checker_sampler, rasterize  # noqa: E402
from splendor.retro.palette import count_colors, rgb_from_rgba_flat  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    # A large ground plane tilted away from the camera — maximal affine warp.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 2, 0))
    plane = bpy.context.active_object
    plane.rotation_euler = Euler((1.15, 0.0, 0.0))  # lay it back toward the horizon
    bpy.ops.object.camera_add(location=(0, -3, 1.4), rotation=(1.25, 0.0, 0.0))
    scene = bpy.context.scene
    scene.camera = bpy.context.object
    bpy.context.view_layer.objects.active = plane

    splendor_harness.register()
    try:
        scene.splendor_palette_size = 8
        scene.splendor_retro_pixel = 2
        r = bpy.ops.splendor.retro_affine('EXEC_DEFAULT', resolution=160, retro_post=True)
        check(r == {'FINISHED'}, "retro_affine finished")
        img = bpy.data.images.get("Splendor Affine")
        check(img is not None and tuple(img.size) == (160, 120), "produced 'Splendor Affine' at 160×120 (4:3)")
        if img is not None:
            buf = list(img.pixels)
            colors = count_colors(rgb_from_rgba_flat(buf))
            check(1 < colors <= 8, f"textured + palette-capped ({colors} colors)")
            covered = sum(1 for i in range(0, len(buf), 4) if buf[i:i + 3] != [0.0, 0.0, 0.0])
            check(covered > 160 * 120 * 0.15, f"the plane actually rasterized ({covered} px covered)")

        # Same projected geometry, affine vs perspective-correct → the swim, on the binary.
        from splendor_harness.retro import _project_mesh
        tris = _project_mesh(plane, scene, 160, 120)
        check(len(tris) >= 2, f"projected {len(tris)} triangles through the camera")
        samp = checker_sampler(8)
        aff = rasterize(tris, 160, 120, samp, perspective_correct=False)
        pc = rasterize(tris, 160, 120, samp, perspective_correct=True)
        diff = sum(1 for i in range(0, len(aff), 4) if aff[i:i + 4] != pc[i:i + 4])
        check(diff > 50, f"affine diverges from perspective-correct on the real projection ({diff} px)")
    finally:
        splendor_harness.unregister()

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — affine render operator verified (real projection → swim)")
    sys.exit(0)


if __name__ == "__main__":
    main()
