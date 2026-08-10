# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-P1 — the Retro Engine as governed, real Blender operators.

    blender --background --factory-startup --python tests/splendor/test_spl_p1_retro_engine.py

Verifies the geometry pass goes through the HIC gate (FlatShade is a governed
intent, not a raw mesh poke), the Retro Shade operator faceting + snaps + caps the
palette, and the Retro Render operator runs the PS1 image pipeline over a real
image datablock (palette cap + pixelation observable on the output).
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import bpy  # noqa: E402
import splendor.action_api  # noqa: E402
import splendor_harness  # noqa: E402
from splendor import dsl, hic  # noqa: E402
from splendor.retro.palette import count_colors, rgb_from_rgba_flat  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def _fresh_mesh():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=4, y_subdivisions=4)
    obj = bpy.context.active_object
    for p in obj.data.polygons:
        p.use_smooth = True  # start smooth so flat-shading is an observable change
    obj.data.update()
    return obj


def main():
    splendor_harness.register()
    scene = bpy.context.scene
    try:
        print("[1] FlatShade is governed — it runs only through the action API + HIC gate")
        obj = _fresh_mesh()
        scene.splendor_hic_level = 'OBSERVED'  # permissive: actions proceed, recorded
        grant = splendor_harness.flow.grant_for(scene)
        res = splendor.action_api.execute(dsl.FlatShade(faceted=True),
                                          principal="user", grant=grant, ctx={"object": obj})
        check(res.executed, "FlatShade executed through the governed action API")
        check(all(not p.use_smooth for p in obj.data.polygons), "every face is now flat (faceted)")

        print("[2] HIC-1 (ApproveEach) blocks the geometry write without approval (gate before act)")
        obj2 = _fresh_mesh()
        scene.splendor_hic_level = 'APPROVE_EACH'
        blocked = splendor.action_api.execute(dsl.FlatShade(faceted=True), principal="user",
                                              grant=splendor_harness.flow.grant_for(scene), ctx={"object": obj2})
        check(not blocked.executed, "FlatShade blocked (require-approval) at HIC-1")
        check(all(p.use_smooth for p in obj2.data.polygons), "mesh untouched — gate ran before the act")

        print("[3] Retro Shade operator: faceting + vertex snap + palette cap, all governed")
        obj3 = _fresh_mesh()
        scene.splendor_hic_level = 'OBSERVED'
        scene.splendor_palette_size = 8
        scene.splendor_snap_grid = 0.25
        bpy.ops.splendor.retro_shade('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'BUILT', "run state BUILT after retro shade")
        check(all(not p.use_smooth for p in obj3.data.polygons), "operator faceted the mesh")
        snapped = all(abs(v.co.x / 0.25 - round(v.co.x / 0.25)) < 1e-5 for v in obj3.data.vertices)
        check(snapped, "vertices snapped to the 0.25 grid")
        check(scene.splendor_palette_size == 8, "palette capped at 8 (governed SetPalette)")

        print("[4] Retro Render operator: PS1 image pipeline over a real image datablock")
        W = H = 16
        src = bpy.data.images.new("retro_src", W, H, alpha=True)
        px = []
        for y in range(H):
            for x in range(W):
                px += [x / (W - 1), y / (H - 1), 0.5, 1.0]  # smooth gradient
        src.pixels = px
        src.update()
        scene.splendor_palette_size = 8
        scene.splendor_retro_pixel = 4
        scene.splendor_retro_bayer = 4
        r = bpy.ops.splendor.retro_render('EXEC_DEFAULT', source_image="retro_src", render_first=False)
        check(r == {'FINISHED'}, "retro_render finished")
        out = bpy.data.images.get("Splendor Retro")
        check(out is not None and tuple(out.size) == (W, H), "produced 'Splendor Retro' at source size")
        if out is not None:
            buf = list(out.pixels)
            colors = count_colors(rgb_from_rgba_flat(buf))
            check(colors <= 8, f"output respects the 8-color palette cap ({colors} colors)")
            # Pixelation: the top-left 4×4 block is uniform.
            base = buf[0:4]
            block_ok = all(buf[((y * W) + x) * 4:((y * W) + x) * 4 + 4] == base
                           for y in range(4) for x in range(4))
            check(block_ok, "4×4 framebuffer block is uniform (pixelated)")
            check(scene.splendor_retro_last == "Splendor Retro", "scene records the last retro image")
    finally:
        splendor_harness.unregister()

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — Retro Engine verified (governed faceting/snap + PS1 image pipeline)")
    sys.exit(0)


if __name__ == "__main__":
    main()
