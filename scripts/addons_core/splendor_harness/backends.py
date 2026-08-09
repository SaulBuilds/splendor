# SPDX-License-Identifier: GPL-2.0-or-later
"""Model / Backend Manager (P3 surface, SPL-S2).

The mock's "backend list · capability chips · local/cloud policy toggle". Backends
are configured entries (name, base_url, model, is_local); a reachability check
probes each; a policy (local-first / local-only / cloud-only) governs selection.
`router_from_manager` builds a `splendor.models.Router` from the configured
backends — the same Router the Plan step drives. Local-first by default.
"""
from __future__ import annotations

import bpy
from bpy.props import (
    BoolProperty, CollectionProperty, EnumProperty, IntProperty, StringProperty,
)

from splendor.models import OpenAICompatBackend, RoutePolicy, Router

_PRESETS = {
    'OLLAMA': ("Ollama", "http://127.0.0.1:11434/v1", "llama3", True),
    'LLAMACPP': ("llama.cpp", "http://127.0.0.1:8080/v1", "local", True),
    'LMSTUDIO': ("LM Studio", "http://127.0.0.1:1234/v1", "local", True),
    'OPENAI': ("OpenAI (cloud)", "https://api.openai.com/v1", "gpt-4o-mini", False),
}
POLICY_ENUM = [
    ('LOCAL_FIRST', "Local-first", "Prefer local, fall back to cloud"),
    ('LOCAL_ONLY', "Local-only", "Only local backends"),
    ('CLOUD_ONLY', "Cloud-only", "Only cloud backends"),
]
_POLICY = {'LOCAL_FIRST': RoutePolicy.LOCAL_FIRST, 'LOCAL_ONLY': RoutePolicy.LOCAL_ONLY,
           'CLOUD_ONLY': RoutePolicy.CLOUD_ONLY}


class SplendorBackend(bpy.types.PropertyGroup):
    name: StringProperty(default="backend")
    base_url: StringProperty(default="http://127.0.0.1:11434/v1")
    model: StringProperty(default="local")
    is_local: BoolProperty(default=True)
    status: StringProperty(default="unknown")   # unknown | reachable | offline


def router_from_manager(scene) -> Router:
    router = Router(policy=_POLICY.get(scene.splendor_route_policy, RoutePolicy.LOCAL_FIRST))
    for b in scene.splendor_backends:
        router.register(OpenAICompatBackend(b.name, b.base_url, b.model, is_local=b.is_local))
    return router


class SPLENDOR_OT_backend_add(bpy.types.Operator):
    """Add a backend from a preset."""

    bl_idname = "splendor.backend_add"
    bl_label = "Add backend"

    preset: EnumProperty(items=[(k, v[0], "") for k, v in _PRESETS.items()], default='OLLAMA')

    def execute(self, context):
        scene = context.scene
        name, url, model, is_local = _PRESETS[self.preset]
        b = scene.splendor_backends.add()
        b.name, b.base_url, b.model, b.is_local, b.status = name, url, model, is_local, "unknown"
        scene.splendor_backends_index = len(scene.splendor_backends) - 1
        self.report({'INFO'}, f"Added {name}")
        return {'FINISHED'}


class SPLENDOR_OT_backend_remove(bpy.types.Operator):
    """Remove the selected backend."""

    bl_idname = "splendor.backend_remove"
    bl_label = "Remove backend"

    def execute(self, context):
        scene = context.scene
        i = scene.splendor_backends_index
        if 0 <= i < len(scene.splendor_backends):
            scene.splendor_backends.remove(i)
            scene.splendor_backends_index = max(0, i - 1)
        return {'FINISHED'}


class SPLENDOR_OT_backend_check(bpy.types.Operator):
    """Check reachability of every configured backend."""

    bl_idname = "splendor.backend_check"
    bl_label = "Check reachability"

    def execute(self, context):
        scene = context.scene
        reachable = 0
        for b in scene.splendor_backends:
            ok = OpenAICompatBackend(b.name, b.base_url, b.model, is_local=b.is_local).reachable(timeout=1.0)
            b.status = "reachable" if ok else "offline"
            reachable += int(ok)
        self.report({'INFO'}, f"{reachable}/{len(scene.splendor_backends)} reachable")
        return {'FINISHED'}


class SPLENDOR_PT_backends(bpy.types.Panel):
    bl_label = "Model / Backend Manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splendor"
    bl_parent_id = "SPLENDOR_PT_harness"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.prop(scene, "splendor_route_policy", text="Policy")

        if not len(scene.splendor_backends):
            layout.label(text="No backends — add one below (local-first).", icon='INFO')
        for b in scene.splendor_backends:
            row = layout.box().row(align=True)
            row.label(text=b.name, icon=('HOME' if b.is_local else 'WORLD'))
            row.label(text="LOCAL" if b.is_local else "CLOUD")
            row.label(text=b.status,
                      icon={'reachable': 'CHECKMARK', 'offline': 'ERROR'}.get(b.status, 'QUESTION'))

        r = layout.row(align=True)
        r.operator("splendor.backend_add", text="Ollama").preset = 'OLLAMA'
        r.operator("splendor.backend_add", text="llama.cpp").preset = 'LLAMACPP'
        r = layout.row(align=True)
        r.operator("splendor.backend_add", text="LM Studio").preset = 'LMSTUDIO'
        r.operator("splendor.backend_add", text="OpenAI").preset = 'OPENAI'
        r = layout.row(align=True)
        r.operator("splendor.backend_check", icon='FILE_REFRESH')
        r.operator("splendor.backend_remove", icon='X')


_UI = (SPLENDOR_OT_backend_add, SPLENDOR_OT_backend_remove, SPLENDOR_OT_backend_check, SPLENDOR_PT_backends)


def register():
    bpy.utils.register_class(SplendorBackend)
    bpy.types.Scene.splendor_backends = CollectionProperty(type=SplendorBackend)
    bpy.types.Scene.splendor_backends_index = IntProperty(default=0)
    bpy.types.Scene.splendor_route_policy = EnumProperty(items=POLICY_ENUM, default='LOCAL_FIRST')
    for cls in _UI:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_UI):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.splendor_route_policy
    del bpy.types.Scene.splendor_backends_index
    del bpy.types.Scene.splendor_backends
    bpy.utils.unregister_class(SplendorBackend)
