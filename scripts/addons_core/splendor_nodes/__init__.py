# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor Nodes — the node/edge workflow editor (P5, SPL-S2).

Authors a `prompt → model → eval → apply` agent workflow visually in Blender's
node editor, round-trips it to a LangGraph artifact (S0.7), and runs it across the
Router (P3) + Eval SDK (P4). One node/edge language shared with the MCP harness
(D-6.2). Thin: nodes carry config, `convert.py` bridges to `splendor.graph`, and
execution is `splendor.graph.run_graph`.
"""
from __future__ import annotations

import bpy

from . import nodes, ops, panels

bl_info = {
    "name": "Splendor Nodes",
    "author": "Splendor",
    "version": (0, 1, 0),
    "blender": (5, 3, 0),
    "location": "Node Editor > Splendor Workflow",
    "description": "Visual agent-workflow editor (prompt→model→eval→apply) ⇄ LangGraph, runs on the seams.",
    "category": "Splendor",
}


def register():
    for cls in nodes.CLASSES:
        bpy.utils.register_class(cls)
    for cls in ops.CLASSES:
        bpy.utils.register_class(cls)
    panels.register()


def unregister():
    panels.unregister()
    for cls in reversed(ops.CLASSES):
        bpy.utils.unregister_class(cls)
    for cls in reversed(nodes.CLASSES):
        bpy.utils.unregister_class(cls)
