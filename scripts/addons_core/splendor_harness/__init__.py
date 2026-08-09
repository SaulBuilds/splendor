# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor Harness — the Blender integration for the governed action core.

Thin by design: it registers the scene state the retro engine reads and the
operators that let the UI (and, later, the mock's chat modals / HIC control bar)
drive intents. Every operator calls the *same* :func:`splendor.action_api.execute`
that the agent and MCP server use — one governed path, two (soon many) front
doors (invariant I-1). No governance logic lives here; it lives in
:mod:`splendor.hic`.
"""
from __future__ import annotations

import bpy

from . import ops

bl_info = {
    "name": "Splendor Harness",
    "author": "Splendor",
    "version": (0, 0, 1),
    "blender": (5, 3, 0),
    "location": "3D Viewport > Sidebar > Splendor (UI arrives with the SPL-S1 mock)",
    "description": "Governed action API + HIC gate (S0.3 seam). Operators route "
                   "through splendor.action_api.execute.",
    "category": "Splendor",
}


def register() -> None:
    bpy.types.Scene.splendor_palette_size = bpy.props.IntProperty(
        name="Splendor Palette Size",
        description="Retro palette size (colors). Read by the retro engine (P1).",
        default=16, min=1, max=256,
    )
    ops.register()


def unregister() -> None:
    ops.unregister()
    del bpy.types.Scene.splendor_palette_size
