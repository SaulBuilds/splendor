# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S1 UI surfaces as Blender panels + a header HIC bar.

Mirrors the mock's component inventory: Harness Panel (the 6-step flow + run
state), Eval scorecard, Deploy panel (the Citrate chain boundary, GPL line made
visible), and the HIC Control Bar in the viewport header (legible autonomy).
Blender conventions are kept (N-panel category, header strip) so muscle memory
holds; the one Splendor addition per surface is the AI/chain legibility.
"""
from __future__ import annotations

import bpy

_STEPS = ["Describe", "Plan", "Build", "Score", "Approve", "Ship"]
_STATE_STEP = {"IDLE": 0, "NEEDS_APPROVAL": 2, "BUILT": 2, "SCORED": 3,
               "AWAITING_MINT_APPROVAL": 4, "SHIPPED": 5}
_HIC_LABEL = {'OBSERVED': "HIC-0 Observed", 'APPROVE_EACH': "HIC-1 ApproveEach",
              'BUDGETED': "HIC-2 Budgeted", 'POST_HOC': "HIC-3 PostHoc",
              'UNGOVERNED': "X Ungoverned"}


def draw_hic_header(self, context):
    """Append to the 3D viewport header: the HIC Control Bar."""
    scene = context.scene
    row = self.layout.row(align=True)
    row.label(text="AUTONOMY")
    lvl = scene.splendor_hic_level
    icon = 'CHECKMARK' if lvl != 'UNGOVERNED' else 'ERROR'
    row.prop(scene, "splendor_hic_level", text="", icon=icon)


class SPLENDOR_PT_harness(bpy.types.Panel):
    bl_label = "Splendor Harness"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splendor"

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        # 6-step flow, current step highlighted.
        step = _STATE_STEP.get(scene.splendor_run_state, 0)
        flow = layout.row(align=True)
        for i, name in enumerate(_STEPS):
            flow.label(text=f"{i + 1} {name}", icon=('RADIOBUT_ON' if i == step else 'RADIOBUT_OFF'))

        col = layout.column(align=True)
        col.scale_y = 1.15
        col.operator("splendor.describe", icon='CONSOLE')
        row = col.row(align=True)
        row.operator("splendor.plan", icon='OUTLINER_OB_LIGHT')
        row.operator("splendor.build", icon='MOD_BUILD')
        row = col.row(align=True)
        row.operator("splendor.score", icon='CHECKMARK')
        row.operator("splendor.ship", icon='EXPORT')

        # Inline HIC-1 approval — appears only when an action is pending (legible autonomy).
        if scene.splendor_run_state in ('NEEDS_APPROVAL', 'AWAITING_MINT_APPROVAL'):
            appr = layout.box()
            appr.alert = True
            what = "build" if scene.splendor_run_state == 'NEEDS_APPROVAL' else "mint"
            appr.label(text=f"HIC-1 · {what} needs your approval", icon='ERROR')
            appr.operator("splendor.approve", icon='CHECKMARK')

        # Retro HUD toggle (summoned overlay).
        layout.prop(scene, "splendor_hud_enabled", text="Retro HUD", toggle=True, icon='OVERLAY')

        box = layout.box()
        box.label(text=f"Run · {scene.splendor_run_state}")
        if scene.splendor_prompt:
            box.label(text=scene.splendor_prompt, icon='OUTLINER_OB_FONT')
        if scene.splendor_plan:
            box.label(text=f"Plan · {scene.splendor_plan_backend}", icon='OUTLINER_OB_LIGHT')
        box.label(text=f"Autonomy · {_HIC_LABEL.get(scene.splendor_hic_level, '?')}")


class SPLENDOR_PT_eval(bpy.types.Panel):
    bl_label = "Eval / Leaderboard"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splendor"
    bl_parent_id = "SPLENDOR_PT_harness"

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        if scene.splendor_run_state in ("IDLE", "BUILT", "NEEDS_APPROVAL"):
            layout.label(text="No score yet — run Score.", icon='INFO')
            return
        verdict = "PASS" if scene.splendor_eval_passed else "FAIL"
        row = layout.row()
        row.label(text="Run #1 score")
        row.label(text=verdict, icon=('CHECKMARK' if scene.splendor_eval_passed else 'ERROR'))
        col = layout.column(align=True)
        col.label(text=f"Tri budget · {scene.splendor_eval_tris} / {scene.splendor_tri_budget}")
        col.label(text=f"Palette · {scene.splendor_palette_size}")
        col.label(text=f"Aggregate · {scene.splendor_eval_score:.2f}")
        layout.label(text=scene.splendor_eval_digest[:22] + "…" if scene.splendor_eval_digest else "")


class SPLENDOR_PT_deploy(bpy.types.Panel):
    bl_label = "Deploy · Splendor × Citrate"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splendor"
    bl_parent_id = "SPLENDOR_PT_harness"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        free = layout.box()
        free.label(text="EXPORT · FREE · IN-APP", icon='CHECKMARK')
        free.label(text="glTF 2.0 · Retro variant (affine baked)")
        free.label(text="PROVENANCE · FREE · seeds the loop")
        if scene.splendor_ship_cid:
            free.label(text=f"attest · {scene.splendor_ship_cid[:18]}…")

        paid = layout.box()
        paid.label(text="CITRATE PROTOCOL · PROTOCOL FEE", icon='WORLD')
        paid.label(text="Mint · Citrate testnet 40204")
        paid.label(text=f"Pin · {scene.splendor_ship_pin or '—'}")
        paid.label(text="Identity · smart account · non-custodial")
        if scene.splendor_ship_mint:
            paid.label(text=f"Mint verdict · {scene.splendor_ship_mint}",
                       icon=('CHECKMARK' if scene.splendor_ship_mint == 'proceed' else 'ERROR'))
        layout.operator("splendor.ship", text="Ship & witness", icon='EXPORT')

        gal = layout.box()
        gal.label(text="WEB GALLERY · self-contained · IPFS", icon='WORLD')
        gal.operator("splendor.publish_gallery", text="Publish to Gallery", icon='URL')
        if scene.splendor_gallery_url:
            gal.label(text=scene.splendor_gallery_url[:44],
                      icon=('CHECKMARK' if scene.splendor_gallery_cid else 'ERROR'))
        layout.label(text="EXPORT IS FREE · PROTOCOL FEES FUND STEWARDSHIP")


PANELS = (SPLENDOR_PT_harness, SPLENDOR_PT_eval, SPLENDOR_PT_deploy)


def register():
    for cls in PANELS:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_HT_header.append(draw_hic_header)


def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_hic_header)
    for cls in reversed(PANELS):
        bpy.utils.unregister_class(cls)
