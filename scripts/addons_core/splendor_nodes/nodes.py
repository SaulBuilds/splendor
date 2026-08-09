# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor workflow node tree + node types (P5, SPL-S2).

Surfaces `splendor.graph` in Blender's node editor: a `prompt → model → eval →
apply` agent workflow authored visually, that round-trips to a LangGraph artifact
and runs across the Router (P3) + Eval SDK (P4) + action API (P2/P6). Nodes carry
the same config the DSL does; conversion lives in `convert.py`. One language for
the node editor and the MCP harness (D-6.2).
"""
from __future__ import annotations

import bpy
from bpy.props import IntProperty, StringProperty

_GREEN = (0.557, 0.800, 0.035, 1.0)


class SplendorFlowSocket(bpy.types.NodeSocket):
    bl_idname = "SplendorFlowSocket"
    bl_label = "Flow"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return _GREEN


class SplendorNodeTree(bpy.types.NodeTree):
    bl_idname = "SplendorNodeTree"
    bl_label = "Splendor Workflow"
    bl_icon = 'NODETREE'


class _SplendorNode(bpy.types.Node):
    splendor_type = "generic"

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == "SplendorNodeTree"

    def to_config(self) -> dict:
        return {}


class SPLENDOR_ND_prompt(_SplendorNode):
    bl_idname = "SPLENDOR_ND_prompt"
    bl_label = "Prompt"
    splendor_type = "prompt"

    text: StringProperty(name="Text", default="a low-poly PS1 potion, ≤16 colors")

    def init(self, context):
        self.outputs.new("SplendorFlowSocket", "flow")

    def draw_buttons(self, context, layout):
        layout.prop(self, "text", text="")

    def to_config(self):
        return {"text": self.text}


class SPLENDOR_ND_model(_SplendorNode):
    bl_idname = "SPLENDOR_ND_model"
    bl_label = "Model (Router)"
    splendor_type = "model"

    def init(self, context):
        self.inputs.new("SplendorFlowSocket", "flow")
        self.outputs.new("SplendorFlowSocket", "flow")

    def draw_buttons(self, context, layout):
        layout.label(text="local-first · honest offline")


class SPLENDOR_ND_eval(_SplendorNode):
    bl_idname = "SPLENDOR_ND_eval"
    bl_label = "Eval"
    splendor_type = "eval"

    tri_budget: IntProperty(name="Tri budget", default=500, min=1)
    palette: IntProperty(name="Palette", default=16, min=1, max=256)

    def init(self, context):
        self.inputs.new("SplendorFlowSocket", "flow")
        self.outputs.new("SplendorFlowSocket", "flow")

    def draw_buttons(self, context, layout):
        layout.prop(self, "tri_budget")
        layout.prop(self, "palette")

    def to_config(self):
        # The subject the Eval SDK scores; measurers fill tri_count in a live run.
        return {"subject": {"tri_count": 12, "palette_colors": self.palette},
                "subject_id": "wf", "tri_budget": self.tri_budget}


class SPLENDOR_ND_apply(_SplendorNode):
    bl_idname = "SPLENDOR_ND_apply"
    bl_label = "Apply"
    splendor_type = "apply"

    def init(self, context):
        self.inputs.new("SplendorFlowSocket", "flow")

    def draw_buttons(self, context, layout):
        layout.label(text="governed action")


NODE_CLASSES = (SPLENDOR_ND_prompt, SPLENDOR_ND_model, SPLENDOR_ND_eval, SPLENDOR_ND_apply)
CLASSES = (SplendorFlowSocket, SplendorNodeTree) + NODE_CLASSES
