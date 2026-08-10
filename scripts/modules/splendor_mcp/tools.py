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
    def __init__(self, name, description, input_schema, build=None, verify=None, read=None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.build = build      # (args: dict) -> (Intent, ctx: dict)   [governed tools]
        self.verify = verify    # (ctx: dict) -> dict  (a checkable read-back)
        self.read = read        # (args: dict) -> dict  [read-only tools: no gate, no mutation]

    @property
    def readonly(self):
        return self.read is not None

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


def _build_flat_shade(args):
    import bpy
    # A two-face target so faceting is observable (starts smooth).
    mesh = bpy.data.meshes.new("mcp_flat")
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2), (0, 2, 3)])
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new("mcp_flat", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return dsl.FlatShade(faceted=bool(args.get("faceted", True))), {"object": obj}


def _verify_flat_shade(ctx):
    return {"faceted": all(not p.use_smooth for p in ctx["object"].data.polygons)}


def _read_get_state(args):
    """Read-only scene context for an external agent — no gate, no mutation."""
    import bpy
    s = bpy.context.scene

    def g(name, default=None):
        return getattr(s, name, default)
    return {
        "hic_level": g("splendor_hic_level", "?"),
        "palette_size": int(g("splendor_palette_size", 0) or 0),
        "tri_budget": int(g("splendor_tri_budget", 0) or 0),
        "run_state": g("splendor_run_state", "IDLE"),
        "eval_passed": bool(g("splendor_eval_passed", False)),
        "eval_score": float(g("splendor_eval_score", 0.0) or 0.0),
        "eval_tris": int(g("splendor_eval_tris", 0) or 0),
        "retro": {"pixel": int(g("splendor_retro_pixel", 0) or 0),
                  "bayer": int(g("splendor_retro_bayer", 0) or 0)},
        "lora_digest": g("splendor_lora_digest", ""),
    }


def _read_eval_run(args):
    """Score a subject with the Eval SDK (read-only feedback for the agent)."""
    import splendor_eval as ev
    tri_budget = int(args.get("tri_budget", 500))
    palette_limit = int(args.get("palette_limit", 16))
    subject = {"tri_count": int(args.get("tri_count", 0)),
               "palette_colors": int(args.get("palette_colors", palette_limit))}
    harness = ev.EvalHarness([ev.TriBudget(tri_budget), ev.PaletteAdherence(palette_limit)])
    rec = harness.evaluate(subject, str(args.get("subject_id", "mcp")), seed=0)
    return {"passed_all": rec.passed_all, "aggregate": rec.aggregate, "digest": rec.digest,
            "subject": subject, "tri_budget": tri_budget, "palette_limit": palette_limit}


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
    "flat_shade": ToolSpec(
        "flat_shade",
        "Faceted flat shading on a target mesh — the PS1/low-poly look (governed by HIC).",
        {"type": "object",
         "properties": {"faceted": {"type": "boolean"}}},
        _build_flat_shade, _verify_flat_shade,
    ),
    "get_state": ToolSpec(
        "get_state",
        "Read the current Splendor scene context (HIC level, palette, run + eval state). Read-only.",
        {"type": "object", "properties": {}},
        read=_read_get_state,
    ),
    "eval_run": ToolSpec(
        "eval_run",
        "Score a subject (tri_count + palette_colors) with the Eval SDK. Read-only feedback.",
        {"type": "object",
         "properties": {"tri_count": {"type": "integer"}, "palette_colors": {"type": "integer"},
                        "tri_budget": {"type": "integer"}, "palette_limit": {"type": "integer"}}},
        read=_read_eval_run,
    ),
}


def list_specs():
    return [s.as_dict() for s in _SPECS.values()]


def get(name):
    return _SPECS.get(name)


# MCP resources — read-only context an external agent can subscribe to / read.
_RESOURCES = [
    {"uri": "splendor://state", "name": "Splendor scene state",
     "description": "HIC level, palette, run + eval state", "mimeType": "application/json"},
    {"uri": "splendor://tools", "name": "Splendor tool catalog",
     "description": "The governed + read-only MCP tools", "mimeType": "application/json"},
    {"uri": "splendor://eval", "name": "Last eval",
     "description": "The most recent Eval SDK result in the scene", "mimeType": "application/json"},
]


def list_resources():
    return list(_RESOURCES)


def read_resource(uri):
    if uri == "splendor://state":
        return _read_get_state({})
    if uri == "splendor://tools":
        return {"tools": list_specs()}
    if uri == "splendor://eval":
        st = _read_get_state({})
        return {k: st[k] for k in ("eval_passed", "eval_score", "eval_tris", "run_state")}
    raise KeyError(uri)
