# SPDX-License-Identifier: GPL-2.0-or-later
"""Node-editor sidebar panel + the add-menu for Splendor workflow nodes."""
from __future__ import annotations

import bpy

from . import nodes


class SPLENDOR_PT_nodes(bpy.types.Panel):
    bl_label = "Splendor Workflow"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Splendor"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space and space.type == 'NODE_EDITOR'

    def draw(self, context):
        layout = self.layout
        space = context.space_data
        tree = getattr(space, "node_tree", None)
        is_splendor = tree is not None and tree.bl_idname == "SplendorNodeTree"

        layout.operator("splendor.graph_new", icon='ADD')
        col = layout.column(align=True)
        col.enabled = is_splendor
        col.operator("splendor.graph_serialize", icon='EXPORT')
        col.operator("splendor.graph_run", icon='PLAY')
        if is_splendor:
            layout.label(text=f"{len(tree.nodes)} nodes · {len(tree.links)} edges")
        else:
            layout.label(text="Open/create a Splendor Workflow tree", icon='INFO')


def _add_menu(self, context):
    if context.space_data and getattr(context.space_data, "tree_type", "") == "SplendorNodeTree":
        layout = self.layout
        layout.separator()
        col = layout.column()
        col.label(text="Splendor")
        for cls in nodes.NODE_CLASSES:
            op = col.operator("node.add_node", text=cls.bl_label)
            op.type = cls.bl_idname
            op.use_transform = True


PANELS = (SPLENDOR_PT_nodes,)


def register():
    for cls in PANELS:
        bpy.utils.register_class(cls)
    bpy.types.NODE_MT_add.append(_add_menu)


def unregister():
    bpy.types.NODE_MT_add.remove(_add_menu)
    for cls in reversed(PANELS):
        bpy.utils.unregister_class(cls)
