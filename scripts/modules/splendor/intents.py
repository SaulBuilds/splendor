# SPDX-License-Identifier: GPL-2.0-or-later
"""Intent executors — the ONLY code that mutates Blender state for an intent.

Every executor is private (``_exec_*``) and reachable *solely* through
:data:`REGISTRY`, which :func:`splendor.action_api.execute` dispatches. This is
invariant **I-1**'s single governed action path: nothing outside the action API
may call an executor or dispatch the registry. The S0.3 source-scan test asserts
exactly that — if a second path appears, the test fails.

``bpy`` is imported lazily inside each executor so this module (and the whole
governance layer) imports cleanly outside Blender.
"""
from __future__ import annotations

from . import dsl


def _exec_snap_vertices(intent: "dsl.SnapVertices", ctx: dict) -> str:
    import bpy  # noqa: F401  (lazy: only needed at execution time)

    obj = ctx.get("object") or bpy.context.active_object
    if obj is None or obj.type != "MESH":
        raise RuntimeError("snap_vertices requires a target mesh object")
    g = intent.grid
    mesh = obj.data
    for v in mesh.vertices:
        v.co.x = round(v.co.x / g) * g
        v.co.y = round(v.co.y / g) * g
        v.co.z = round(v.co.z / g) * g
    mesh.update()
    return f"snapped {len(mesh.vertices)} verts to grid {g}"


def _exec_set_palette(intent: "dsl.SetPalette", ctx: dict) -> str:
    import bpy

    scene = ctx.get("scene") or bpy.context.scene
    # `splendor_palette_size` is registered by the splendor_harness addon; the
    # retro engine (P1) reads it. Setting it is a real, checkable state change.
    scene.splendor_palette_size = intent.colors
    return f"palette set to {intent.colors}"


# The single dispatch registry: intent class -> executor. The action API is the
# only module permitted to read this (asserted by the source-scan test, I-1).
REGISTRY = {
    dsl.SnapVertices: _exec_snap_vertices,
    dsl.SetPalette: _exec_set_palette,
}
