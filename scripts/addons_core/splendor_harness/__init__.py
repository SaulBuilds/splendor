# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor Harness — the SPL-S1 in-Blender UI, wired to the verified seams.

Thin by design: operators and panels are *front doors* to the governed action API
(P2/P6), the model Router (P3), the Eval SDK (P4), and the deploy layer (P7). No
governance or scoring logic lives here — it lives in the `splendor*` modules. The
UI implements the SPL-S1 mock: the 6-step flow (Describe → Plan → Build → Score →
Approve → Ship), the HIC Control Bar, the Retro HUD, the Eval scorecard, and the
Citrate deploy boundary — Blender-native, Citrate-green accent.
"""
from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from . import backends, flow, hud, ops, panels, retro, training

bl_info = {
    "name": "Splendor Harness",
    "author": "Splendor",
    "version": (0, 1, 0),
    "blender": (5, 3, 0),
    "location": "3D Viewport > Sidebar (N) > Splendor · header autonomy bar",
    "description": "SPL-S1 governed AI flow: describe → plan → build → score → ship, wired to the seams.",
    "category": "Splendor",
}


def _hud_update(self, context):
    if self.splendor_hud_enabled:
        hud.enable()
    else:
        hud.disable()


def _register_props():
    S = bpy.types.Scene
    S.splendor_palette_size = IntProperty(
        name="Splendor Palette Size", description="Retro palette size (colors), read by the retro engine",
        default=16, min=1, max=256)
    S.splendor_tri_budget = IntProperty(name="Tri Budget", default=500, min=1)
    S.splendor_snap_grid = FloatProperty(name="Vertex Snap", default=0.1, min=1e-4, soft_max=1.0)
    S.splendor_hic_level = EnumProperty(name="Autonomy", items=flow.HIC_ENUM, default='BUDGETED')
    S.splendor_prompt = StringProperty(name="Prompt", default="")
    S.splendor_plan = StringProperty(name="Plan", default="")
    S.splendor_plan_backend = StringProperty(name="Plan Backend", default="")
    S.splendor_run_state = StringProperty(name="Run State", default="IDLE")
    S.splendor_retro_enabled = BoolProperty(name="Retro", default=True)
    S.splendor_retro_pixel = IntProperty(
        name="Pixelate", description="Low-res framebuffer block size (nearest upscale)",
        default=4, min=1, max=32)
    S.splendor_retro_bayer = IntProperty(
        name="Dither", description="Ordered (Bayer) dither matrix size — 2, 4 or 8",
        default=4, min=2, max=8)
    S.splendor_retro_spread = FloatProperty(
        name="Dither Spread", description="Dither strength (color nudge before palette snap)",
        default=0.12, min=0.0, max=1.0)
    S.splendor_retro_last = StringProperty(name="Last Retro Image", default="")
    S.splendor_affine_texture = StringProperty(
        name="Affine Texture", default="",
        description="Image datablock to affine-map (blank = procedural checker)")
    S.splendor_hud_enabled = BoolProperty(name="Retro HUD", default=False, update=_hud_update)
    S.splendor_eval_passed = BoolProperty(name="Eval Passed", default=False)
    S.splendor_eval_digest = StringProperty(name="Eval Digest", default="")
    S.splendor_eval_score = FloatProperty(name="Eval Score", default=0.0)
    S.splendor_eval_tris = IntProperty(name="Eval Tris", default=0)
    S.splendor_ship_cid = StringProperty(name="Ship CID", default="")
    S.splendor_ship_pin = StringProperty(name="Ship Pin", default="")
    S.splendor_ship_mint = StringProperty(name="Ship Mint", default="")


def _unregister_props():
    S = bpy.types.Scene
    for name in ("splendor_palette_size", "splendor_tri_budget", "splendor_snap_grid",
                 "splendor_hic_level", "splendor_prompt", "splendor_plan", "splendor_plan_backend",
                 "splendor_run_state", "splendor_retro_enabled", "splendor_hud_enabled",
                 "splendor_eval_passed", "splendor_eval_digest", "splendor_eval_score",
                 "splendor_eval_tris", "splendor_ship_cid", "splendor_ship_pin",
                 "splendor_ship_mint", "splendor_retro_pixel", "splendor_retro_bayer",
                 "splendor_retro_spread", "splendor_retro_last", "splendor_affine_texture"):
        if hasattr(S, name):
            delattr(S, name)


def register():
    _register_props()
    ops.register()
    for cls in flow.CLASSES:
        bpy.utils.register_class(cls)
    bpy.utils.register_class(hud.SPLENDOR_OT_toggle_hud)
    panels.register()
    retro.register()
    backends.register()
    training.register()


def unregister():
    training.unregister()
    backends.unregister()
    retro.unregister()
    panels.unregister()
    bpy.utils.unregister_class(hud.SPLENDOR_OT_toggle_hud)
    for cls in reversed(flow.CLASSES):
        bpy.utils.unregister_class(cls)
    ops.unregister()
    hud.disable()
    _unregister_props()
