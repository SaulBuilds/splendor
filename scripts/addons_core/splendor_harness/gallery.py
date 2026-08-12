# SPDX-License-Identifier: GPL-2.0-or-later
"""Gallery collection + index publish (P7) — assemble many pieces into one page.

Accumulate finished pieces (each already a `Splendor Retro`/`Affine` image + scene
provenance) into a per-scene collection, then publish them as N pinned pages plus a
pinned **index** that links them all (relative `/ipfs/<cid>` links, portable across
gateways). Honest: unreachable pinning fails loudly, never a fabricated URL.
"""
from __future__ import annotations

import os
import tempfile

import bpy
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, IntProperty, StringProperty

from splendor.deploy import GalleryItem, IpfsPinning, PinUnavailable, publish_gallery


def _png_bytes(name: str) -> bytes:
    img = bpy.data.images.get(name)
    if img is None or int(img.size[0]) == 0:
        return b""
    path = os.path.join(tempfile.gettempdir(), f"spl_gal_{abs(hash(name)) % 10_000_000}.png")
    img.filepath_raw = path
    img.file_format = 'PNG'
    try:
        img.save()
        with open(path, "rb") as fh:
            return fh.read()
    except (RuntimeError, OSError):
        return b""


class SplendorGalleryPiece(bpy.types.PropertyGroup):
    title: StringProperty(default="")
    image: StringProperty(default="")   # bpy image datablock name
    prompt: StringProperty(default="")
    eval_score: FloatProperty(default=0.0)
    eval_passed: BoolProperty(default=False)
    palette: IntProperty(default=0)
    tris: IntProperty(default=0)
    asset_cid: StringProperty(default="")


class SPLENDOR_OT_gallery_add(bpy.types.Operator):
    """Add the current piece (last retro/affine image + scene provenance) to the gallery."""

    bl_idname = "splendor.gallery_add"
    bl_label = "Add to Gallery"

    def execute(self, context):
        scene = context.scene
        p = scene.splendor_gallery_items.add()
        p.image = scene.splendor_retro_last or "Splendor Retro"
        p.title = (scene.splendor_prompt or f"Piece {len(scene.splendor_gallery_items)}")[:80]
        p.prompt = scene.splendor_prompt or ""
        p.eval_score = float(scene.splendor_eval_score)
        p.eval_passed = bool(scene.splendor_eval_passed)
        p.palette = int(scene.splendor_palette_size)
        p.tris = int(scene.splendor_eval_tris)
        p.asset_cid = scene.splendor_ship_cid or ""
        self.report({'INFO'}, f"Added · {len(scene.splendor_gallery_items)} piece(s) in the gallery")
        return {'FINISHED'}


class SPLENDOR_OT_gallery_clear(bpy.types.Operator):
    """Empty the gallery collection."""

    bl_idname = "splendor.gallery_clear"
    bl_label = "Clear Gallery"

    def execute(self, context):
        context.scene.splendor_gallery_items.clear()
        context.scene.splendor_gallery_index_cid = ""
        context.scene.splendor_gallery_index_url = ""
        return {'FINISHED'}


class SPLENDOR_OT_publish_index(bpy.types.Operator):
    """Publish every piece + a linking index to IPFS; report the index URL."""

    bl_idname = "splendor.publish_index"
    bl_label = "Publish Gallery Index"

    def execute(self, context):
        scene = context.scene
        pieces = scene.splendor_gallery_items
        if len(pieces) == 0:
            self.report({'WARNING'}, "add pieces to the gallery first")
            return {'CANCELLED'}
        items = [GalleryItem(
            title=p.title, prompt=p.prompt, image_png=_png_bytes(p.image),
            eval_score=p.eval_score, eval_passed=p.eval_passed, palette=p.palette,
            tris=p.tris, asset_cid=p.asset_cid, workflow="retro → eval → ship") for p in pieces]
        try:
            out = publish_gallery(items, IpfsPinning(), title="Splendor Gallery")
        except PinUnavailable as exc:
            scene.splendor_gallery_index_cid = ""
            scene.splendor_gallery_index_url = f"unreachable: {exc}"[:120]
            self.report({'WARNING'}, f"Publish failed honestly: {str(exc)[:70]}")
            return {'FINISHED'}
        index_ref, index_url = out["index"]
        scene.splendor_gallery_index_cid = index_ref.cid
        scene.splendor_gallery_index_url = index_url
        self.report({'INFO'}, f"Published gallery index ({len(items)} pieces) · {index_url}")
        return {'FINISHED'}


class SPLENDOR_PT_gallery(bpy.types.Panel):
    """Gallery — collect pieces and publish a linked index."""

    bl_label = "Web Gallery Index"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splendor"
    bl_parent_id = "SPLENDOR_PT_harness"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        col = self.layout.column(align=True)
        row = col.row(align=True)
        row.operator("splendor.gallery_add", icon='ADD')
        row.operator("splendor.publish_index", icon='WORLD')
        col.label(text=f"{len(scene.splendor_gallery_items)} piece(s) in the gallery")
        for p in scene.splendor_gallery_items:
            col.label(text=f"• {p.title[:28]} · pal {p.palette}", icon='IMAGE_DATA')
        if scene.splendor_gallery_index_url:
            col.label(text=scene.splendor_gallery_index_url[:44],
                      icon=('CHECKMARK' if scene.splendor_gallery_index_cid else 'ERROR'))
        if len(scene.splendor_gallery_items):
            col.operator("splendor.gallery_clear", icon='X')


_CLASSES = (SplendorGalleryPiece, SPLENDOR_OT_gallery_add, SPLENDOR_OT_gallery_clear,
            SPLENDOR_OT_publish_index, SPLENDOR_PT_gallery)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.splendor_gallery_items = CollectionProperty(type=SplendorGalleryPiece)
    bpy.types.Scene.splendor_gallery_index_cid = StringProperty(name="Gallery Index CID", default="")
    bpy.types.Scene.splendor_gallery_index_url = StringProperty(name="Gallery Index URL", default="")


def unregister():
    del bpy.types.Scene.splendor_gallery_index_url
    del bpy.types.Scene.splendor_gallery_index_cid
    del bpy.types.Scene.splendor_gallery_items
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
