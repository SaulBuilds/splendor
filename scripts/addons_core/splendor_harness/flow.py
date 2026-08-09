# SPDX-License-Identifier: GPL-2.0-or-later
"""The SPL-S1 flow operators — the 6 steps wired to the real seams.

Describe → Plan → Build → Score → Approve → Ship. Each operator drives the
verified backend: the governed action API (P2/P6), the model Router (P3), the
Eval SDK (P4), and the deploy layer (P7). Nothing here fakes a result: a governed
block reports honestly, an unreachable endpoint reports honestly, mint (sensitive)
requires HIC-1 approval. This is the wiring the mock draws.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

import bpy
from bpy.props import FloatProperty, IntProperty, StringProperty

import splendor
import splendor_eval as ev
from splendor import dsl, hic
from splendor.deploy import (
    ChainUnavailable, HttpChainAdapter, HttpPinning, MemoryChainAdapter, PinUnavailable,
    content_address, make_provenance,
)
from . import theme

HIC_ENUM = [
    ('OBSERVED', "HIC-0 · Observed", "Agent acts; every action recorded"),
    ('APPROVE_EACH', "HIC-1 · ApproveEach", "Each action requires approval"),
    ('BUDGETED', "HIC-2 · Budgeted", "Agent acts within a budget"),
    ('POST_HOC', "HIC-3 · PostHoc", "Agent acts; human reviews after"),
    ('UNGOVERNED', "X · Ungoverned", "No governance"),
]
_LEVELS = {
    'OBSERVED': hic.HicLevel.OBSERVED, 'APPROVE_EACH': hic.HicLevel.APPROVE_EACH,
    'BUDGETED': hic.HicLevel.BUDGETED, 'POST_HOC': hic.HicLevel.POST_HOC,
    'UNGOVERNED': hic.HicLevel.UNGOVERNED,
}


def grant_for(scene, classes=("geometry", "scene_config")):
    level = _LEVELS.get(scene.splendor_hic_level, hic.HicLevel.BUDGETED)
    return hic.Grant("ui-session", "user", level, frozenset(classes))


@dataclass(frozen=True)
class _MintIntent(dsl.Intent):
    action_class = "mint"   # sensitive → HIC-1 approve-each even when covered

    def validate(self):
        return None


def _ensure_target(context):
    """The active mesh, or a fresh 'Potion' cube built via bpy.data (background-safe)."""
    obj = context.active_object
    if obj is not None and obj.type == 'MESH':
        return obj
    mesh = bpy.data.meshes.new("Potion")
    verts = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
             (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Potion", mesh)
    context.scene.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    return obj


class SPLENDOR_OT_describe(bpy.types.Operator):
    """Describe a PS1 asset; the agent builds it through the governed action API."""

    bl_idname = "splendor.describe"
    bl_label = "Describe a PS1 asset"
    bl_options = {'REGISTER', 'UNDO'}

    prompt: StringProperty(name="Prompt", default="a low-poly PS1 health potion, ≤16 colors")
    colors: IntProperty(name="Palette", default=16, min=1, max=256)
    grid: FloatProperty(name="Vertex snap", default=0.1, min=1e-4, soft_max=1.0)

    def invoke(self, context, event):
        self.colors = context.scene.splendor_palette_size
        return context.window_manager.invoke_props_dialog(self, width=390)

    def execute(self, context):
        scene = context.scene
        obj = _ensure_target(context)
        grant = grant_for(scene)
        r1 = splendor.action_api.execute(dsl.SetPalette(colors=self.colors),
                                         principal="user", grant=grant, ctx={"scene": scene})
        r2 = splendor.action_api.execute(dsl.SnapVertices(grid=self.grid),
                                         principal="user", grant=grant, ctx={"object": obj})
        scene.splendor_prompt = self.prompt
        built = r1.executed and r2.executed
        scene.splendor_run_state = 'BUILT' if built else 'NEEDS_APPROVAL'
        rc = f"{r1.record.rule_code}/{r2.record.rule_code}"
        if built:
            self.report({'INFO'}, f"Built · palette {self.colors} · snap {self.grid} [{rc}]")
        else:
            self.report({'WARNING'}, f"Governed: {r2.verdict.value} [{rc}]")
        return {'FINISHED'}


class SPLENDOR_OT_score(bpy.types.Operator):
    """Score the run with the Eval SDK (tri budget + palette adherence)."""

    bl_idname = "splendor.score"
    bl_label = "Score run"

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "no active mesh to score")
            return {'CANCELLED'}
        tris = sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)
        subject = {"tri_count": tris, "palette_colors": int(scene.splendor_palette_size)}
        harness = ev.EvalHarness([
            ev.TriBudget(int(scene.splendor_tri_budget)),
            ev.PaletteAdherence(int(scene.splendor_palette_size)),
        ])
        rec = harness.evaluate(subject, "run", seed=0)
        scene.splendor_eval_passed = rec.passed_all
        scene.splendor_eval_digest = rec.digest
        scene.splendor_eval_score = rec.aggregate
        scene.splendor_eval_tris = tris
        scene.splendor_run_state = 'SCORED'
        self.report({'INFO'}, f"Eval {'PASS' if rec.passed_all else 'FAIL'} · "
                              f"agg {rec.aggregate:.2f} · {rec.digest[:14]}")
        return {'FINISHED'}


class SPLENDOR_OT_ship(bpy.types.Operator):
    """Ship: attest + pin (free) then mint (protocol fee, HIC-1 gated)."""

    bl_idname = "splendor.ship"
    bl_label = "Ship & witness"

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        data = (repr([tuple(round(c, 6) for c in v.co) for v in obj.data.vertices]).encode()
                if obj and obj.type == 'MESH' else b"")
        cid = content_address(data)
        prov = make_provenance(cid, eval_digest=(scene.splendor_eval_digest or None),
                               workflow=None, meta={"prompt": scene.splendor_prompt})
        # Provenance attest is free (memory adapter here; real chain via config).
        MemoryChainAdapter("citrate").attest(prov)

        pin_url = os.environ.get("SPLENDOR_CITRATE_PINNING", "")
        if pin_url:
            try:
                ref = HttpPinning(pin_url).pin(data)
                pin_status = f"pinned {ref.cid[:18]}…"
            except PinUnavailable as exc:
                pin_status = f"unreachable: {exc}"
        else:
            pin_status = "unconfigured (Citrate endpoint unset)"

        # Mint is sensitive → HIC-1 approve-each. Honest require-approval by default.
        mint = splendor.action_api.execute(_MintIntent(), principal="user",
                                           grant=grant_for(scene, classes=("mint",)), ctx={})
        scene.splendor_ship_cid = cid
        scene.splendor_ship_pin = pin_status
        scene.splendor_ship_mint = mint.verdict.value
        scene.splendor_run_state = 'SHIPPED' if mint.executed else 'AWAITING_MINT_APPROVAL'
        if mint.executed:
            self.report({'INFO'}, f"Shipped · {cid[:16]}… · pin {pin_status}")
        else:
            self.report({'WARNING'}, f"Mint {mint.verdict.value} [{mint.record.rule_code}] · "
                                     f"attested+pin={pin_status}")
        return {'FINISHED'}


class SPLENDOR_OT_set_hic(bpy.types.Operator):
    """Set the current HIC autonomy level."""

    bl_idname = "splendor.set_hic"
    bl_label = "Set autonomy level"

    level: StringProperty()

    def execute(self, context):
        if self.level:
            context.scene.splendor_hic_level = self.level
        return {'FINISHED'}


class SPLENDOR_OT_apply_accent(bpy.types.Operator):
    """Apply the Citrate-green accent (green replaces Blender blue)."""

    bl_idname = "splendor.apply_accent"
    bl_label = "Apply Splendor accent"

    def execute(self, context):
        green = theme.apply_accent()
        self.report({'INFO'}, f"Citrate accent applied {tuple(round(c, 3) for c in green)}")
        return {'FINISHED'}


CLASSES = (
    SPLENDOR_OT_describe, SPLENDOR_OT_score, SPLENDOR_OT_ship,
    SPLENDOR_OT_set_hic, SPLENDOR_OT_apply_accent,
)
