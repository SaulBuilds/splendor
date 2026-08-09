# SPDX-License-Identifier: GPL-2.0-or-later
"""Operators that drive Splendor intents through the governed action API.

These are one of the "front doors" to :func:`splendor.action_api.execute`; the
agent and MCP server are the others, and all share the single path (I-1). An
operator NEVER calls an intent executor directly — it builds a typed intent and
hands it to the action API, which runs the HIC gate first.

The interactive grant below is a placeholder for the real HIC layer + UI (the
SPL-S1 mock brings the HIC control bar that sets the level per action). It is a
*live, covering* grant so hand-use works; it is not a bypass of the gate — the
gate still runs and records every action.
"""
from __future__ import annotations

import bpy

import splendor
from splendor import dsl, hic


def _interactive_grant() -> hic.Grant:
    """A HIC-2 (Budgeted) grant covering the interactive action classes.

    Placeholder until the HIC control bar (SPL-S1 mock) issues real grants.
    """
    return hic.Grant(
        grant_id="interactive",
        principal="user",
        hic_level=hic.HicLevel.BUDGETED,
        action_classes=frozenset({"geometry", "scene_config"}),
    )


def _report_result(op: bpy.types.Operator, res) -> set:
    rec = res.record
    if res.executed:
        op.report({'INFO'}, f"Splendor: {res.outcome} [{rec.rule_code} · {rec.hic_level.name}]")
        return {'FINISHED'}
    level = {'require-approval': 'WARNING', 'deny': 'ERROR'}.get(res.verdict.value, 'WARNING')
    op.report({level}, f"Splendor: {res.verdict.value} [{rec.rule_code}] {rec.reason}")
    return {'CANCELLED'}


class SPLENDOR_OT_snap_vertices(bpy.types.Operator):
    """Snap the active mesh's vertices to a retro grid (governed)."""

    bl_idname = "splendor.snap_vertices"
    bl_label = "Snap Vertices (Retro)"
    bl_options = {'REGISTER', 'UNDO'}

    grid: bpy.props.FloatProperty(name="Grid", default=0.1, min=1e-4, soft_max=1.0)

    def execute(self, context):
        res = splendor.action_api.execute(
            dsl.SnapVertices(grid=self.grid),
            principal="user",
            grant=_interactive_grant(),
            ctx={"object": context.active_object},
        )
        return _report_result(self, res)


class SPLENDOR_OT_set_palette(bpy.types.Operator):
    """Set the scene's retro palette size (governed)."""

    bl_idname = "splendor.set_palette"
    bl_label = "Set Retro Palette"
    bl_options = {'REGISTER', 'UNDO'}

    colors: bpy.props.IntProperty(name="Colors", default=16, min=1, max=256)

    def execute(self, context):
        res = splendor.action_api.execute(
            dsl.SetPalette(colors=self.colors),
            principal="user",
            grant=_interactive_grant(),
            ctx={"scene": context.scene},
        )
        return _report_result(self, res)


_CLASSES = (SPLENDOR_OT_snap_vertices, SPLENDOR_OT_set_palette)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
