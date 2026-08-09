# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S1 UI wiring test — the bpy front end is wired to the real seams.

    blender --background --factory-startup --python tests/splendor/test_spl_s1_ui.py

Exits non-zero on any failure. Verifies the addon registers, the flow operators
drive the verified backend (governed build, real eval, honest deploy), the HIC
gate is respected from the UI (APPROVE_EACH → build blocked), and the accent
applies. Panels can't be *rendered* headlessly, but their registration + the
operator wiring are what this checks.
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
        # Panels + operators + header registered.
        for pt in ("SPLENDOR_PT_harness", "SPLENDOR_PT_eval", "SPLENDOR_PT_deploy"):
            check(hasattr(bpy.types, pt), f"panel {pt} registered")
        for op in ("describe", "score", "ship", "set_hic", "apply_accent"):
            check(hasattr(bpy.types, "SPLENDOR_OT_" + op), f"operator splendor.{op} registered")

        print("[1] Describe → governed build (HIC-2 Budgeted) drives the action API")
        scene.splendor_hic_level = 'BUDGETED'
        scene.splendor_palette_size = 16
        bpy.ops.splendor.describe('EXEC_DEFAULT', prompt="a PS1 potion", colors=8, grid=0.1)
        check(scene.splendor_run_state == 'BUILT', "run state BUILT after governed build")
        check(scene.splendor_palette_size == 8, "SetPalette applied real scene state via action API")

        print("[2] HIC gate respected from the UI: APPROVE_EACH → build requires approval")
        scene.splendor_hic_level = 'APPROVE_EACH'
        bpy.ops.splendor.describe('EXEC_DEFAULT', prompt="again", colors=12, grid=0.1)
        check(scene.splendor_run_state == 'NEEDS_APPROVAL', "HIC-1 blocks the build (require-approval)")
        check(scene.splendor_palette_size == 8, "palette NOT changed while awaiting approval (gate before act)")

        print("[3] Score → real Eval SDK record")
        scene.splendor_hic_level = 'BUDGETED'
        bpy.ops.splendor.describe('EXEC_DEFAULT', prompt="potion", colors=16, grid=0.1)
        bpy.ops.splendor.score('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'SCORED', "run state SCORED")
        check(scene.splendor_eval_passed and scene.splendor_eval_digest.startswith("sha256:"),
              "eval passed + carries a real content digest")

        print("[4] Ship → honest deploy: free attest+pin, mint requires HIC-1")
        bpy.ops.splendor.ship('EXEC_DEFAULT')
        check(scene.splendor_ship_cid.startswith("sha256:"), "asset content-addressed (CID)")
        check("unconfigured" in scene.splendor_ship_pin, "pin honestly 'unconfigured' (no fake success)")
        check(scene.splendor_ship_mint == 'require-approval', "mint is HIC-1 gated (require-approval)")
        check(scene.splendor_run_state == 'AWAITING_MINT_APPROVAL', "run state awaits mint approval")

        print("[5] Citrate-green accent applies (green replaces Blender blue)")
        bpy.ops.splendor.apply_accent('EXEC_DEFAULT')
        active = tuple(round(c, 3) for c in bpy.context.preferences.themes[0].view_3d.object_active)
        check(active == (0.557, 0.800, 0.035), f"active-object accent is Citrate green {active}")
    finally:
        splendor_harness.unregister()
        check(not hasattr(bpy.types, "SPLENDOR_PT_harness"), "clean unregister (panel gone)")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — SPL-S1 UI wired to the seams (governed, evaluated, honest deploy)")
    sys.exit(0)


if __name__ == "__main__":
    main()
