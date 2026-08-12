# SPDX-License-Identifier: GPL-2.0-or-later
"""In-GUI MCP server controls — start/stop a persistent Splendor MCP server.

A running Blender can serve external agents live: this starts the threaded server
(`splendor_mcp.threaded`) whose socket I/O runs on a background thread while every
governed `tools/call` is marshalled to Blender's main thread via `bpy.app.timers`.
The session's autonomy is the **scene HIC level** — the in-viewport Control Bar
governs external agents exactly as it governs in-app actions. `Ungoverned` grants no
session grant, so external acts require approval (safe by default).
"""
from __future__ import annotations

import bpy
from bpy.props import IntProperty

from splendor import hic
from splendor_mcp.threaded import ThreadedMCPServer

_SERVER = None  # the single running instance (module-global; one per Blender process)

_LEVELS = {
    'OBSERVED': hic.HicLevel.OBSERVED,
    'APPROVE_EACH': hic.HicLevel.APPROVE_EACH,
    'BUDGETED': hic.HicLevel.BUDGETED,
    'POST_HOC': hic.HicLevel.POST_HOC,
}


def _grant_from_scene(scene):
    """Grant the MCP session the scene's HIC level; Ungoverned → no grant (approval-gated)."""
    level = _LEVELS.get(scene.splendor_hic_level)
    if level is None:
        return None
    return hic.Grant("mcp-session", "mcp:external", level, frozenset({"geometry", "scene_config"}))


def is_running():
    return _SERVER is not None


class SPLENDOR_OT_mcp_start(bpy.types.Operator):
    """Start the persistent MCP server (external agents drive this Blender, HIC-governed)."""

    bl_idname = "splendor.mcp_start"
    bl_label = "Start MCP Server"

    def execute(self, context):
        global _SERVER
        if _SERVER is not None:
            self.report({'INFO'}, f"MCP already serving on 127.0.0.1:{_SERVER.bound_port}")
            return {'FINISHED'}
        scene = context.scene
        _SERVER = ThreadedMCPServer(grant=_grant_from_scene(scene))
        port = _SERVER.start(register_timer=True)
        scene.splendor_mcp_port = port
        self.report({'INFO'}, f"Splendor MCP serving on 127.0.0.1:{port} "
                              f"(bridge: python -m splendor_mcp bridge --port {port})")
        return {'FINISHED'}


class SPLENDOR_OT_mcp_stop(bpy.types.Operator):
    """Stop the persistent MCP server."""

    bl_idname = "splendor.mcp_stop"
    bl_label = "Stop MCP Server"

    def execute(self, context):
        global _SERVER
        if _SERVER is not None:
            _SERVER.stop()
            _SERVER = None
        context.scene.splendor_mcp_port = 0
        self.report({'INFO'}, "Splendor MCP stopped")
        return {'FINISHED'}


class SPLENDOR_PT_mcp(bpy.types.Panel):
    """MCP server — serve external agents from this running Blender."""

    bl_label = "MCP Server (live)"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splendor"
    bl_parent_id = "SPLENDOR_PT_harness"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        col = self.layout.column(align=True)
        if is_running():
            col.label(text=f"● serving on :{scene.splendor_mcp_port}", icon='CHECKMARK')
            col.label(text=f"session HIC · {scene.splendor_hic_level}")
            col.operator("splendor.mcp_stop", icon='PAUSE')
            col.label(text=f"bridge → :{scene.splendor_mcp_port}", icon='URL')
        else:
            col.label(text="○ stopped", icon='RADIOBUT_OFF')
            col.operator("splendor.mcp_start", icon='PLAY')


_CLASSES = (SPLENDOR_OT_mcp_start, SPLENDOR_OT_mcp_stop, SPLENDOR_PT_mcp)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.splendor_mcp_port = IntProperty(name="MCP Port", default=0)


def unregister():
    global _SERVER
    if _SERVER is not None:  # never leak a running server across a reload
        _SERVER.stop()
        _SERVER = None
    del bpy.types.Scene.splendor_mcp_port
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
