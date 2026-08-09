# SPDX-License-Identifier: GPL-2.0-or-later
"""The SPL-S1 flow operators — the 6 steps wired to the real seams.

Describe → Plan → Build → Score → Approve → Ship. Each drives a verified backend:
the model Router (P3, the Plan step), the governed action API (P2/P6, Build), the
Eval SDK (P4, Score), the deploy layer (P7, Ship). Nothing fakes a result: an
offline Plan says so, a governed Build reports honestly, an unreachable pin
reports honestly, mint (sensitive) requires HIC-1 approval.
"""
from __future__ import annotations

import os

import bpy
from bpy.props import FloatProperty, IntProperty, StringProperty

import splendor
import splendor_eval as ev
from splendor import dsl, hic
from splendor.deploy import (
    HttpPinning, MemoryChainAdapter, PinUnavailable, content_address, make_provenance,
)
from splendor.models import (
    BackendUnavailable, CompletionRequest, Message, OpenAICompatBackend, Router,
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


def build_router():
    """Local-first Router: a configured endpoint (env), then Ollama, then llama.cpp."""
    router = Router()
    url = os.environ.get("SPLENDOR_MODEL_URL")
    if url:
        router.register(OpenAICompatBackend("configured", url,
                                            os.environ.get("SPLENDOR_MODEL", "local"), is_local=True))
    router.register(OpenAICompatBackend("ollama", "http://127.0.0.1:11434/v1", "llama3", is_local=True))
    router.register(OpenAICompatBackend("llama.cpp", "http://127.0.0.1:8080/v1", "local", is_local=True))
    return router


def _ensure_target(context):
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
    """Describe a PS1 asset (captures the prompt + retro parameters)."""

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
        scene.splendor_prompt = self.prompt
        scene.splendor_palette_size = self.colors
        scene.splendor_snap_grid = self.grid
        _ensure_target(context)
        scene.splendor_run_state = 'DESCRIBED'
        self.report({'INFO'}, f"Described · palette {self.colors} · snap {self.grid}")
        return {'FINISHED'}


class SPLENDOR_OT_plan(bpy.types.Operator):
    """Plan the build with a local model (Router, local-first). Honest if offline."""

    bl_idname = "splendor.plan"
    bl_label = "Plan (local model)"

    def execute(self, context):
        scene = context.scene
        prompt = scene.splendor_prompt or "a low-poly PS1 asset, low palette"
        req = CompletionRequest(messages=[
            Message("system", "You plan retro PS1-style 3D asset builds as terse ordered steps."),
            Message("user", prompt)], max_tokens=120)
        try:
            res = build_router().complete(req)
            scene.splendor_plan = res.text[:400]
            scene.splendor_plan_backend = res.backend
            scene.splendor_run_state = 'PLANNED'
            self.report({'INFO'}, f"Planned via {res.backend}")
        except BackendUnavailable:
            scene.splendor_plan = ("(no local model reachable — offline. Run a llama.cpp/Ollama "
                                   "server or set SPLENDOR_MODEL_URL.)")
            scene.splendor_plan_backend = "offline"
            scene.splendor_run_state = 'PLAN_OFFLINE'
            self.report({'WARNING'}, "No local model reachable — offline (honest)")
        return {'FINISHED'}


class SPLENDOR_OT_build(bpy.types.Operator):
    """Build the asset through the governed action API (respects the HIC level)."""

    bl_idname = "splendor.build"
    bl_label = "Build (governed)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        obj = _ensure_target(context)
        grant = grant_for(scene)
        r1 = splendor.action_api.execute(dsl.SetPalette(colors=int(scene.splendor_palette_size)),
                                         principal="user", grant=grant, ctx={"scene": scene})
        r2 = splendor.action_api.execute(dsl.SnapVertices(grid=float(scene.splendor_snap_grid)),
                                         principal="user", grant=grant, ctx={"object": obj})
        built = r1.executed and r2.executed
        scene.splendor_run_state = 'BUILT' if built else 'NEEDS_APPROVAL'
        rc = f"{r1.record.rule_code}/{r2.record.rule_code}"
        if built:
            self.report({'INFO'}, f"Built [{rc}]")
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

        # Mint is sensitive → HIC-1 gate (no approval supplied here → require-approval).
        decision = hic.gate("mint", grant_for(scene, classes=("mint",)))
        scene.splendor_ship_cid = cid
        scene.splendor_ship_pin = pin_status
        if decision.verdict is hic.Verdict.PROCEED:
            ref = MemoryChainAdapter("citrate").attest({"mint": cid, "provenance": prov["digest"]})
            scene.splendor_ship_mint = f"minted {ref.id[:14]}…"
            scene.splendor_run_state = 'SHIPPED'
            self.report({'INFO'}, f"Shipped · {cid[:16]}… · pin {pin_status}")
        else:
            scene.splendor_ship_mint = decision.verdict.value
            scene.splendor_run_state = 'AWAITING_MINT_APPROVAL'
            self.report({'WARNING'}, f"Mint {decision.verdict.value} [{decision.rule_code}] · "
                                     f"attested+pin={pin_status} · needs HIC-1 approval")
        return {'FINISHED'}


class SPLENDOR_OT_approve(bpy.types.Operator):
    """Approve the pending HIC-1 action inline so it proceeds (never a bypass)."""

    bl_idname = "splendor.approve"
    bl_label = "Approve (HIC-1)"

    def execute(self, context):
        scene = context.scene
        state = scene.splendor_run_state
        if state == 'NEEDS_APPROVAL':
            approval = hic.Approval("user", frozenset({"geometry", "scene_config"}))
            obj = _ensure_target(context)
            grant = grant_for(scene)
            r1 = splendor.action_api.execute(dsl.SetPalette(colors=int(scene.splendor_palette_size)),
                                             principal="user", grant=grant, ctx={"scene": scene},
                                             approval=approval)
            r2 = splendor.action_api.execute(dsl.SnapVertices(grid=float(scene.splendor_snap_grid)),
                                             principal="user", grant=grant, ctx={"object": obj},
                                             approval=approval)
            if r1.executed and r2.executed:
                scene.splendor_run_state = 'BUILT'
                self.report({'INFO'}, f"Approved · built [{r1.record.rule_code}/{r2.record.rule_code}]")
            else:
                self.report({'WARNING'}, "Approval did not clear the build")
            return {'FINISHED'}
        if state == 'AWAITING_MINT_APPROVAL':
            approval = hic.Approval("user", frozenset({"mint"}))
            decision = hic.gate("mint", grant_for(scene, classes=("mint",)), approval)
            if decision.verdict is hic.Verdict.PROCEED:
                ref = MemoryChainAdapter("citrate").attest(
                    {"mint": scene.splendor_ship_cid, "approved_by": "user"})
                scene.splendor_ship_mint = f"minted {ref.id[:14]}… ({decision.rule_code})"
                scene.splendor_run_state = 'SHIPPED'
                self.report({'INFO'}, f"Approved · minted {ref.id[:14]}…")
            else:
                self.report({'WARNING'}, "Mint still not permitted")
            return {'FINISHED'}
        self.report({'INFO'}, "Nothing is pending approval")
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
    SPLENDOR_OT_describe, SPLENDOR_OT_plan, SPLENDOR_OT_build,
    SPLENDOR_OT_score, SPLENDOR_OT_approve, SPLENDOR_OT_ship, SPLENDOR_OT_apply_accent,
)
