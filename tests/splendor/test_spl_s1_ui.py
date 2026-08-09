# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S1 UI wiring test — the bpy front end is wired to the real seams.

    blender --background --factory-startup --python tests/splendor/test_spl_s1_ui.py

Exits non-zero on any failure. Verifies the addon registers, the flow operators
(Describe → Plan → Build → Score → Ship) drive the verified backend, the HIC gate
is respected from the UI, the Plan step calls the Router (offline = honest), the
Retro HUD toggles its viewport draw handler, and the accent applies. Panels can't
be *rendered* headlessly, but registration + operator wiring + the HUD metrics are
what this checks.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))
sys.path.insert(0, os.path.dirname(__file__))

import bpy  # noqa: E402
import splendor_harness  # noqa: E402
from splendor_harness import hud  # noqa: E402
import _openai_compat_server  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    os.environ.pop("SPLENDOR_MODEL_URL", None)
    os.environ.pop("SPLENDOR_CITRATE_PINNING", None)
    # Keep the UI test hermetic: force IPFS + chain RPC unreachable and clear any signer
    # so Ship/mint exercise the honest failure paths deterministically. The real pin→fetch
    # round-trip and the real on-chain attestation are verified live in
    # tests/splendor/test_s0_8_citrate_live.py and test_s0_9_signer.py.
    os.environ["CITRATE_IPFS_API"] = "http://127.0.0.1:59999"
    os.environ["CITRATE_RPC_URL"] = "http://127.0.0.1:59999"
    for _k in ("SPLENDOR_CITRATE_SIGNER", "CITRATE_SIGNER_KEY"):
        os.environ.pop(_k, None)
    splendor_harness.register()
    scene = bpy.context.scene
    try:
        for pt in ("SPLENDOR_PT_harness", "SPLENDOR_PT_eval", "SPLENDOR_PT_deploy"):
            check(hasattr(bpy.types, pt), f"panel {pt} registered")
        for op in ("describe", "plan", "build", "score", "ship", "apply_accent", "toggle_hud"):
            check(hasattr(bpy.types, "SPLENDOR_OT_" + op), f"operator splendor.{op} registered")

        print("[1] Describe → Build: governed build (HIC-2) drives the action API")
        scene.splendor_hic_level = 'BUDGETED'
        bpy.ops.splendor.describe('EXEC_DEFAULT', prompt="a PS1 potion", colors=8, grid=0.1)
        check(scene.splendor_run_state == 'DESCRIBED', "Describe → DESCRIBED (captures prompt)")
        bpy.ops.splendor.build('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'BUILT', "Build → BUILT after governed build")
        check(scene.splendor_palette_size == 8, "SetPalette applied real scene state via action API")

        print("[2] HIC gate + inline Approve: APPROVE_EACH build blocks, then Approve clears it")
        scene.splendor_hic_level = 'APPROVE_EACH'
        scene.splendor_palette_size = 8
        bpy.ops.splendor.build('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'NEEDS_APPROVAL', "HIC-1 blocks the build (require-approval)")
        bpy.ops.splendor.approve('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'BUILT', "Approve (HIC-1) clears the build → BUILT (proceeds, not bypass)")

        print("[3] Plan (offline) → honest, no fabricated plan")
        scene.splendor_hic_level = 'BUDGETED'
        bpy.ops.splendor.plan('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'PLAN_OFFLINE', "no local model → PLAN_OFFLINE (honest)")
        check("offline" in scene.splendor_plan, "plan text says offline, not a faked plan")

        print("[4] Plan (online) → Router calls a real local OpenAI-compatible backend")
        _srv, port = _openai_compat_server.start(reply="1 box 2 snap 0.1 3 palette 16")
        os.environ["SPLENDOR_MODEL_URL"] = f"http://127.0.0.1:{port}/v1"
        bpy.ops.splendor.plan('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'PLANNED', "reachable model → PLANNED")
        check("box" in scene.splendor_plan and scene.splendor_plan_backend == "configured",
              "plan came from the configured local backend (real completion)")
        os.environ.pop("SPLENDOR_MODEL_URL", None)

        print("[5] Score → real Eval SDK record")
        bpy.ops.splendor.build('EXEC_DEFAULT')
        bpy.ops.splendor.score('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'SCORED', "run state SCORED")
        check(scene.splendor_eval_passed and scene.splendor_eval_digest.startswith("sha256:"),
              "eval passed + real content digest")

        print("[6] Ship → honest deploy: attest+pin free, mint HIC-1 gated, then Approve attests")
        bpy.ops.splendor.ship('EXEC_DEFAULT')
        check(scene.splendor_ship_cid.startswith("sha256:"), "asset content-addressed (CID)")
        check("unreachable" in scene.splendor_ship_pin, "pin fails honestly when IPFS is unreachable (no fake CID)")
        check(scene.splendor_ship_mint == 'require-approval', "mint HIC-1 gated (require-approval)")
        check(scene.splendor_run_state == 'AWAITING_MINT_APPROVAL', "run state awaits mint approval")
        bpy.ops.splendor.approve('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'SHIPPED', "Approve (HIC-1) clears the on-chain step → SHIPPED")
        # No signer + unreachable RPC → honest 'unsigned' (never a fabricated tx); a
        # configured, funded, authorised signer would read 'attested <txhash>…'.
        check(scene.splendor_ship_mint.startswith("unsigned "),
              "on-chain attest honestly deferred without a signer (no fake mint)")

        print("[7] Retro HUD: metrics correct + toggle drives the viewport draw handler")
        m = hud.hud_metrics(scene)
        check(m["tris"] == scene.splendor_eval_tris and m["budget"] == 500 and not m["over"],
              f"hud_metrics reads run state ({m['tris']}/{m['budget']} tris)")
        scene.splendor_hud_enabled = True
        check(hud.is_enabled(), "HUD on → draw handler installed")
        scene.splendor_hud_enabled = False
        check(not hud.is_enabled(), "HUD off → draw handler removed")

        print("[8] Citrate-green accent applies")
        bpy.ops.splendor.apply_accent('EXEC_DEFAULT')
        active = tuple(round(c, 3) for c in bpy.context.preferences.themes[0].view_3d.object_active)
        check(active == (0.557, 0.800, 0.035), f"accent is Citrate green {active}")
    finally:
        splendor_harness.unregister()
        check(not hasattr(bpy.types, "SPLENDOR_PT_harness"), "clean unregister")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — SPL-S1 UI: Plan (Router) + Retro HUD wired, flow governed & honest")
    sys.exit(0)


if __name__ == "__main__":
    main()
