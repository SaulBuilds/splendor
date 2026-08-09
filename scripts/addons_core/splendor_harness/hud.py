# SPDX-License-Identifier: GPL-2.0-or-later
"""The Retro Target HUD — a summoned viewport overlay (P1 legibility).

The mock's "budget meter · dithered live readout": a small overlay bottom-left of
the 3D viewport showing the tri budget bar (green within budget, yellow over),
palette count, and the eval score. Drawn with the ``gpu`` + ``blf`` viewport draw
API. The pure :func:`hud_metrics` holds the data (testable headlessly); the draw
callback only paints it. Summoned via a toggle, off by default (soft, not
in-your-face).
"""
from __future__ import annotations

import bpy

_GREEN = (0.557, 0.800, 0.035, 1.0)
_YELLOW = (1.000, 0.741, 0.063, 1.0)
_HANDLE = None


def hud_metrics(scene) -> dict:
    tris = int(scene.splendor_eval_tris)
    budget = int(scene.splendor_tri_budget)
    return {
        "tris": tris,
        "budget": budget,
        "tri_frac": min(1.0, tris / budget) if budget else 0.0,
        "over": tris > budget,
        "palette": int(scene.splendor_palette_size),
        "score": float(scene.splendor_eval_score),
        "passed": bool(scene.splendor_eval_passed),
        "state": scene.splendor_run_state,
    }


def _rect(shader, x, y, w, h, color):
    from gpu_extras.batch import batch_for_shader
    batch = batch_for_shader(shader, 'TRI_FAN',
                             {"pos": [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw():
    scene = bpy.context.scene
    if not getattr(scene, "splendor_hud_enabled", False):
        return
    try:
        import blf
        import gpu
        m = hud_metrics(scene)
        x, y, w, h = 18, 18, 236, 60
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        _rect(shader, x, y, w, h, (0.06, 0.06, 0.05, 0.86))         # panel
        _rect(shader, x + 12, y + 12, w - 24, 6, (0.12, 0.12, 0.10, 1.0))  # bar track
        _rect(shader, x + 12, y + 12, int((w - 24) * m["tri_frac"]), 6,
              _YELLOW if m["over"] else _GREEN)                      # bar fill
        gpu.state.blend_set('NONE')
        font = 0
        blf.size(font, 12)
        blf.color(font, 0.85, 0.85, 0.84, 1.0)
        blf.position(font, x + 12, y + 40, 0)
        blf.draw(font, f"RETRO · {m['tris']}/{m['budget']} tris · pal {m['palette']}")
        blf.position(font, x + 12, y + 24, 0)
        blf.draw(font, f"score {m['score']:.2f} · {m['state']}")
    except Exception:
        pass   # never let a HUD draw error disrupt the viewport


def enable():
    global _HANDLE
    if _HANDLE is None:
        _HANDLE = bpy.types.SpaceView3D.draw_handler_add(_draw, (), 'WINDOW', 'POST_PIXEL')


def disable():
    global _HANDLE
    if _HANDLE is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_HANDLE, 'WINDOW')
        _HANDLE = None


def is_enabled() -> bool:
    return _HANDLE is not None


class SPLENDOR_OT_toggle_hud(bpy.types.Operator):
    """Summon / dismiss the Retro Target HUD overlay."""

    bl_idname = "splendor.toggle_hud"
    bl_label = "Retro HUD"

    def execute(self, context):
        scene = context.scene
        scene.splendor_hud_enabled = not scene.splendor_hud_enabled
        if scene.splendor_hud_enabled:
            enable()
        else:
            disable()
        # nudge a redraw where a viewport exists
        for area in context.screen.areas if context.screen else []:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        self.report({'INFO'}, f"Retro HUD {'on' if scene.splendor_hud_enabled else 'off'}")
        return {'FINISHED'}
