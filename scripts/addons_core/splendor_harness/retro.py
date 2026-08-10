# SPDX-License-Identifier: GPL-2.0-or-later
"""The Retro Engine surface (P1) — the PS1 look as real, governed operators.

Two passes, both wired to the verified seams:

- **Retro Shade** (geometry) — faceted flat shading + vertex snap + palette cap,
  each applied *through the governed action API* (so the HIC gate still decides).
- **Retro Render** (image) — runs the pure-Python PS1 image pipeline
  (:func:`splendor.retro.retro_frame`: pixelate → ordered dither → palette) over a
  source image (a render, or any loaded image) into a new ``Splendor Retro`` image.

No effect logic lives here — geometry goes through :mod:`splendor.intents`, the
image pipeline through :mod:`splendor.retro.postprocess`. This module is only the
Blender front door.
"""
from __future__ import annotations

import os
import tempfile

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty

import splendor.action_api
from splendor import dsl
from splendor.retro import checker_sampler, image_sampler, rasterize, retro_frame
from splendor.retro.palette import count_colors, generate_palette, rgb_from_rgba_flat

from .flow import _ensure_target, grant_for


def _project_mesh(obj, scene, width, height):
    """Project `obj`'s triangles to screen space via the scene camera →
    [((sx, sy, inv_w, u, v), ×3), …]. Triangles fully behind the camera are dropped.
    Pure geometry math on top of bpy — the rasterizer itself stays bpy-free."""
    cam = scene.camera
    if cam is None:
        return []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    proj = cam.calc_matrix_camera(depsgraph, x=width, y=height)
    view = cam.matrix_world.inverted()
    pv = proj @ view
    world = obj.matrix_world
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data if mesh.uv_layers.active else None
    tris = []
    for lt in mesh.loop_triangles:
        verts = []
        ok = True
        for k in range(3):
            co = world @ mesh.vertices[lt.vertices[k]].co
            clip = pv @ co.to_4d()
            if clip.w <= 1e-6:  # at/behind the camera plane
                ok = False
                break
            ndc_x, ndc_y = clip.x / clip.w, clip.y / clip.w
            sx = (ndc_x * 0.5 + 0.5) * width
            sy = (ndc_y * 0.5 + 0.5) * height  # bottom-up, matches Blender image rows
            u, v = (uv[lt.loops[k]].uv if uv else (0.0, 0.0))
            verts.append((sx, sy, 1.0 / clip.w, float(u), float(v)))
        if ok:
            tris.append((verts[0], verts[1], verts[2]))
    return tris


class SPLENDOR_OT_retro_shade(bpy.types.Operator):
    """Faceted flat shading + vertex snap + palette cap, all through the HIC gate."""

    bl_idname = "splendor.retro_shade"
    bl_label = "Retro Shade (governed)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        obj = _ensure_target(context)
        grant = grant_for(scene)
        results = [
            splendor.action_api.execute(dsl.FlatShade(faceted=True),
                                        principal="user", grant=grant, ctx={"object": obj}),
            splendor.action_api.execute(dsl.SnapVertices(grid=float(scene.splendor_snap_grid)),
                                        principal="user", grant=grant, ctx={"object": obj}),
            splendor.action_api.execute(dsl.SetPalette(colors=int(scene.splendor_palette_size)),
                                        principal="user", grant=grant, ctx={"scene": scene}),
        ]
        codes = "/".join(r.record.rule_code for r in results)
        if all(r.executed for r in results):
            scene.splendor_run_state = 'BUILT'
            self.report({'INFO'}, f"Retro-shaded (flat + snap + palette) [{codes}]")
        else:
            scene.splendor_run_state = 'NEEDS_APPROVAL'
            blocked = next(r for r in results if not r.executed)
            self.report({'WARNING'}, f"Governed: {blocked.verdict.value} [{codes}]")
        return {'FINISHED'}


class SPLENDOR_OT_retro_render(bpy.types.Operator):
    """Apply the PS1 image pipeline to a source image → a new 'Splendor Retro' image."""

    bl_idname = "splendor.retro_render"
    bl_label = "Retro Render"

    source_image: StringProperty(
        name="Source Image", default="Render Result",
        description="Image datablock to process (a render, or any loaded image)")
    render_first: BoolProperty(
        name="Render First", default=False,
        description="Render the scene to a temp file and use that as the source")

    def execute(self, context):
        scene = context.scene
        src = None
        if self.render_first:
            tmp = os.path.join(tempfile.gettempdir(), "splendor_retro_src.png")
            scene.render.filepath = tmp
            bpy.ops.render.render(write_still=True)
            src = bpy.data.images.load(tmp, check_existing=False)
        else:
            src = bpy.data.images.get(self.source_image)
        if src is None:
            self.report({'ERROR'}, f"source image '{self.source_image}' not found "
                                   "(render first, or load an image)")
            return {'CANCELLED'}
        w, h = int(src.size[0]), int(src.size[1])
        if w == 0 or h == 0 or len(src.pixels) < w * h * 4:
            self.report({'ERROR'}, f"source image '{src.name}' has no readable pixels")
            return {'CANCELLED'}

        palette = generate_palette(int(scene.splendor_palette_size))
        out = retro_frame(list(src.pixels), w, h, palette,
                          pixel_factor=int(scene.splendor_retro_pixel),
                          bayer_n=int(scene.splendor_retro_bayer),
                          spread=float(scene.splendor_retro_spread))

        name = "Splendor Retro"
        img = bpy.data.images.get(name)
        if img is not None and tuple(img.size) != (w, h):
            bpy.data.images.remove(img)
            img = None
        if img is None:
            img = bpy.data.images.new(name, w, h, alpha=True)
        img.pixels = out
        img.update()
        colors = count_colors(rgb_from_rgba_flat(out))
        scene.splendor_retro_last = name
        self.report({'INFO'}, f"Retro render '{name}' {w}×{h} · ≤{len(palette)} palette · {colors} colors")
        return {'FINISHED'}


class SPLENDOR_OT_retro_affine(bpy.types.Operator):
    """Software affine rasterizer — the PS1 'swimming texture' (no perspective-correct UV)."""

    bl_idname = "splendor.retro_affine"
    bl_label = "Retro Affine Render"

    resolution: IntProperty(name="Resolution", default=160, min=16, max=512)
    retro_post: BoolProperty(name="Dither + Palette", default=True)

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "affine render needs an active mesh")
            return {'CANCELLED'}
        if scene.camera is None:
            self.report({'ERROR'}, "affine render needs a scene camera")
            return {'CANCELLED'}
        w = int(self.resolution)
        h = max(16, w * 3 // 4)  # 4:3, PS1-ish
        tris = _project_mesh(obj, scene, w, h)
        if not tris:
            self.report({'ERROR'}, "no visible triangles to rasterize (mesh behind camera?)")
            return {'CANCELLED'}
        tex = bpy.data.images.get(scene.splendor_affine_texture) if scene.splendor_affine_texture else None
        if tex is not None and len(tex.pixels) >= tex.size[0] * tex.size[1] * 4:
            sample = image_sampler(list(tex.pixels), int(tex.size[0]), int(tex.size[1]))
        else:
            sample = checker_sampler(8)
        fb = rasterize(tris, w, h, sample, perspective_correct=False)
        if self.retro_post:
            pal = generate_palette(int(scene.splendor_palette_size))
            fb = retro_frame(fb, w, h, pal, pixel_factor=int(scene.splendor_retro_pixel),
                             bayer_n=int(scene.splendor_retro_bayer), spread=float(scene.splendor_retro_spread))
        name = "Splendor Affine"
        img = bpy.data.images.get(name)
        if img is not None and tuple(img.size) != (w, h):
            bpy.data.images.remove(img)
            img = None
        if img is None:
            img = bpy.data.images.new(name, w, h, alpha=True)
        img.pixels = fb
        img.update()
        scene.splendor_retro_last = name
        self.report({'INFO'}, f"Affine render '{name}' {w}×{h} · {len(tris)} tris"
                              f"{' · dithered' if self.retro_post else ''}")
        return {'FINISHED'}


class SPLENDOR_PT_retro(bpy.types.Panel):
    """Retro Engine sub-panel — the PS1 passes."""

    bl_label = "Retro Engine (PS1)"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splendor"
    bl_parent_id = "SPLENDOR_PT_harness"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        col = self.layout.column(align=True)
        col.prop(scene, "splendor_palette_size")
        row = col.row(align=True)
        row.prop(scene, "splendor_retro_pixel")
        row.prop(scene, "splendor_retro_bayer")
        col.prop(scene, "splendor_retro_spread")
        col.separator()
        col.operator("splendor.retro_shade", icon='MOD_DECIM')
        col.operator("splendor.retro_render", icon='IMAGE_RGB').render_first = True
        col.operator("splendor.retro_affine", icon='MOD_UVPROJECT')
        col.prop(scene, "splendor_affine_texture")
        if scene.splendor_retro_last:
            col.label(text=f"→ {scene.splendor_retro_last}", icon='IMAGE_DATA')


CLASSES = (SPLENDOR_OT_retro_shade, SPLENDOR_OT_retro_render, SPLENDOR_OT_retro_affine,
           SPLENDOR_PT_retro)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
