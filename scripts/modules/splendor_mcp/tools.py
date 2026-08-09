# SPDX-License-Identifier: GPL-2.0-or-later
"""MCP tool specs — each maps a tool name to a typed Splendor intent.

A tool NEVER touches Blender or the executor directly: it builds a
:class:`splendor.dsl.Intent` and hands it to the action API, which runs the HIC
gate first. ``bpy`` is imported lazily inside the builders so this module loads
without Blender (the server needs bpy at call time, not import time).
"""
from __future__ import annotations

from splendor import dsl

# Deterministic off-grid mesh used when snap_vertices has no target — keeps the
# tool self-contained and its result verifiable.
_OFFGRID = [(0.137, -0.052, 0.311), (1.031, 0.984, -0.446), (-0.628, 0.207, 0.079)]


class ToolSpec:
    def __init__(self, name, description, input_schema, build, verify=None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.build = build      # (args: dict) -> (Intent, ctx: dict)
        self.verify = verify    # (ctx: dict) -> dict  (a checkable read-back)

    def as_dict(self):
        return {"name": self.name, "description": self.description, "inputSchema": self.input_schema}


def _build_set_palette(args):
    import bpy
    return dsl.SetPalette(colors=int(args.get("colors", 16))), {"scene": bpy.context.scene}


def _verify_set_palette(ctx):
    return {"palette_size": int(ctx["scene"].splendor_palette_size)}


def _build_snap_vertices(args):
    import bpy
    grid = float(args.get("grid", 0.1))
    mesh = bpy.data.meshes.new("mcp_target")
    mesh.from_pydata(list(_OFFGRID), [], [])
    mesh.update()
    obj = bpy.data.objects.new("mcp_target", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return dsl.SnapVertices(grid=grid), {"object": obj, "_grid": grid}


def _verify_snap_vertices(ctx):
    obj, g = ctx["object"], ctx["_grid"]
    aligned = all(abs(c / g - round(c / g)) < 1e-4 for v in obj.data.vertices for c in v.co)
    return {"aligned": aligned, "verts": len(obj.data.vertices)}


_SPECS = {
    "set_palette": ToolSpec(
        "set_palette",
        "Set the scene's retro palette size (governed by HIC).",
        {"type": "object",
         "properties": {"colors": {"type": "integer", "minimum": 1, "maximum": 256}},
         "required": ["colors"]},
        _build_set_palette, _verify_set_palette,
    ),
    "snap_vertices": ToolSpec(
        "snap_vertices",
        "Snap a target mesh's vertices to a retro grid (governed by HIC).",
        {"type": "object",
         "properties": {"grid": {"type": "number", "exclusiveMinimum": 0}}},
        _build_snap_vertices, _verify_snap_vertices,
    ),
}


def list_specs():
    return [s.as_dict() for s in _SPECS.values()]


def get(name):
    return _SPECS.get(name)
