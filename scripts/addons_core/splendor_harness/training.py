# SPDX-License-Identifier: GPL-2.0-or-later
"""Training Panel (SPL-S3) — modality picker · compute source · dataset · job queue.

Workflow capture is real (saves the current run's workflow to a content-hashed
library — weightless training, D-3.1). Weight-based modalities enqueue an honest
job ("trainer not yet wired"); cloud / Citrate-DePIN compute (D-3.2) reports
availability truthfully. Nothing here fakes a trained model.
"""
from __future__ import annotations

import json
import os

import bpy
from bpy.props import CollectionProperty, EnumProperty, StringProperty

from splendor import train as _train
from splendor.graph import END, START, Edge, Node, WorkflowGraph

_MODALITY_ENUM = [
    ('diffusion_lora', "Diffusion LoRA", "Train a style LoRA from your renders"),
    ('llm_lora', "LLM LoRA", "Fine-tune the local model on your workflows"),
    ('workflow_lora', "Workflow LoRA", "Low-rank adapter: learn prompt→params from eval-scored runs"),
    ('workflow_capture', "Workflow capture", "Weightless — save a run as a reusable workflow"),
    ('geometry_model', "3D / geometry model", "Train a small mesh/animation model"),
]
_COMPUTE_ENUM = [
    ('local', "Local GPU", "This machine"),
    ('cloud', "Cloud", "Managed cloud training (config-gated)"),
    ('depin', "Citrate DePIN", "Compute sourced from the CitrateNetwork DePIN market"),
]

# Process-wide captured-workflow library (later persisted + pinned as provenance).
LIBRARY = _train.WorkflowLibrary()


def workflow_from_scene(scene) -> WorkflowGraph:
    """The current harness run as a reusable workflow (prompt→model→eval→apply)."""
    return WorkflowGraph(
        [Node("prompt", "prompt", {"text": scene.splendor_prompt or "run"}),
         Node("model", "model", {}),
         Node("eval", "eval", {"subject": {"tri_count": int(scene.splendor_eval_tris),
                                           "palette_colors": int(scene.splendor_palette_size)},
                               "subject_id": "run"}),
         Node("apply", "apply", {})],
        [Edge(START, "prompt"), Edge("prompt", "model"), Edge("model", "eval"),
         Edge("eval", "apply", condition={"when": "eval_passed", "else": END}), Edge("apply", END)])


def samples_from_library():
    """Extract (prompt, palette, limit) training samples from captured workflows.

    Each captured run's prompt text + the palette it used become one sample; the used
    palette is the target ('what a good run picked for this prompt')."""
    out = []
    for entry in LIBRARY.all():
        try:
            g = json.loads(entry.artifact)
        except (ValueError, TypeError):
            continue
        prompt, palette = None, None
        for node in g.get("nodes", []):
            if node.get("type") == "prompt":
                prompt = (node.get("config") or {}).get("text")
            elif node.get("type") == "eval":
                palette = ((node.get("config") or {}).get("subject") or {}).get("palette_colors")
        if prompt and palette:
            out.append(_train.Sample(prompt=str(prompt), palette=int(palette), limit=int(palette)))
    return out


class SplendorTrainJob(bpy.types.PropertyGroup):
    modality: StringProperty(default="")
    compute: StringProperty(default="")
    status: StringProperty(default="")
    digest: StringProperty(default="")


class SPLENDOR_OT_train_enqueue(bpy.types.Operator):
    """Enqueue a training job (workflow capture runs now; weights are honest)."""

    bl_idname = "splendor.train_enqueue"
    bl_label = "Enqueue training job"

    def execute(self, context):
        scene = context.scene
        mod, comp = scene.splendor_train_modality, scene.splendor_train_compute
        job = scene.splendor_train_jobs.add()
        job.modality, job.compute = mod, comp
        if mod == "workflow_capture":
            entry = LIBRARY.capture(workflow_from_scene(scene))
            job.status = f"captured {entry.digest[:14]}…"
            job.digest = entry.digest
            self.report({'INFO'}, f"Captured workflow · library has {len(LIBRARY)}")
        elif mod == "llm_lora":
            job.status = _train_llm_lora(scene, job)
            self.report({'INFO'}, job.status)
        elif mod == "diffusion_lora":
            job.status = _train_diffusion_lora(scene, job)
            self.report({'INFO'}, job.status)
        elif mod == "geometry_model":
            job.status = _train_geometry(scene, job)
            self.report({'INFO'}, job.status)
        else:
            job.status = _train.job_status(mod, comp, os.environ)
            self.report({'INFO'}, job.status)
        return {'FINISHED'}


def _train_llm_lora(scene, job) -> str:
    """Delegate a real LLM-LoRA finetune to the trainer process; honest if unavailable.

    Dataset = each captured run's prompt → the parameters it used (teach the local
    model to emit Splendor params for a prompt). Never fabricates an adapter."""
    samples = samples_from_library()
    if len(samples) < 2:
        return f"capture ≥2 runs first (have {len(samples)})"
    dataset = [{"prompt": s.prompt, "completion": json.dumps({"palette": s.palette})} for s in samples]
    trainer = _train.resolve_trainer(os.environ)
    if trainer is None:
        return "no LLM-LoRA trainer configured (set SPLENDOR_LORA_TRAINER)"
    steps = int(os.environ.get("SPLENDOR_LORA_STEPS", "60"))
    try:
        res = trainer.train(dataset, rank=8, steps=steps, lr=5e-3, seed=0)
    except _train.TrainerUnavailable as exc:
        return f"trainer unavailable: {str(exc)[:60]}"
    job.digest = res["adapter_digest"]
    scene.splendor_lora_digest = res["adapter_digest"]
    return (f"trained · loss {res['initial_loss']:.2f}→{res['final_loss']:.2f} · "
            f"{res['trainable_params']}/{res['total_params']} LoRA · {res['adapter_digest'][:14]}…")


def _img_to_gray8(name):
    """Downsample a bpy image to an 8×8 grayscale flat vector (nearest) for a style LoRA."""
    img = bpy.data.images.get(name)
    if img is None or int(img.size[0]) == 0:
        return None
    w, h = int(img.size[0]), int(img.size[1])
    px = list(img.pixels)
    out = []
    for gy in range(8):
        for gx in range(8):
            sx, sy = min(w - 1, gx * w // 8), min(h - 1, gy * h // 8)
            i = (sy * w + sx) * 4
            out.append((px[i] + px[i + 1] + px[i + 2]) / 3.0)
    return out


def _train_diffusion_lora(scene, job) -> str:
    """Delegate a real diffusion (style) LoRA over the gallery/render images. Honest."""
    names = [p.image for p in scene.splendor_gallery_items] or [scene.splendor_retro_last or "Splendor Retro"]
    images = [g for g in (_img_to_gray8(n) for n in names) if g]
    if not images:
        return "no images (render or add pieces to the gallery first)"
    trainer = _train.resolve_trainer(os.environ, kind="diffusion")
    if trainer is None:
        return "no diffusion trainer configured (set SPLENDOR_DIFFUSION_TRAINER)"
    steps = int(os.environ.get("SPLENDOR_DIFFUSION_STEPS", "100"))
    try:
        res = trainer.train_diffusion(images, rank=8, steps=steps, lr=8e-3, seed=0)
    except _train.TrainerUnavailable as exc:
        return f"trainer unavailable: {str(exc)[:60]}"
    job.digest = res["adapter_digest"]
    scene.splendor_lora_digest = res["adapter_digest"]
    return (f"trained · {len(images)} img · loss {res['initial_loss']:.2f}→{res['final_loss']:.2f} · "
            f"{res['trainable_params']}/{res['total_params']} LoRA · {res['adapter_digest'][:14]}…")


# Captured meshes (equal topology) for the geometry model — process-wide, like LIBRARY.
GEO_MESHES = []


def _train_geometry(scene, job) -> str:
    """Capture the active mesh and (re)fit a PCA shape basis over captured meshes."""
    obj = bpy.context.active_object
    if obj is None or obj.type != 'MESH':
        return "select a mesh to capture"
    verts = [c for v in obj.data.vertices for c in v.co]
    GEO_MESHES.append(verts)
    lengths = {len(m) for m in GEO_MESHES}
    if len(GEO_MESHES) < 2:
        return f"captured 1 mesh — need ≥2 same-topology meshes to fit"
    if len(lengths) != 1:
        return f"captured {len(GEO_MESHES)} meshes but topologies differ ({sorted(lengths)}) — same vert count needed"
    model, info = _train.fit_shape_basis(GEO_MESHES, k=4)
    err = _train.reconstruction_error(model, GEO_MESHES)
    job.digest = model.digest()
    return (f"fit · {info['n']} meshes · k={info['k']} · var {info['variance_explained']:.2f} · "
            f"err {err:.3f} · {model.digest()[:14]}…")


class SPLENDOR_OT_train_lora(bpy.types.Operator):
    """Train a Workflow LoRA on the captured runs (real gradients, Eval-SDK-scored)."""

    bl_idname = "splendor.train_lora"
    bl_label = "Train Workflow LoRA"

    def execute(self, context):
        scene = context.scene
        samples = samples_from_library()
        if len(samples) < 4:
            self.report({'WARNING'}, f"capture ≥4 runs first (have {len(samples)})")
            return {'CANCELLED'}
        # A held-out split when there's enough; otherwise honest in-sample.
        if len(samples) >= 8:
            train = [s for i, s in enumerate(samples) if i % 2 == 0]
            holdout = [s for i, s in enumerate(samples) if i % 2 == 1]
            split = "held-out"
        else:
            train = holdout = samples
            split = "in-sample"
        out = _train.run_training_loop(train, holdout, epochs=400, lr=0.4, seed=0)
        job = scene.splendor_train_jobs.add()
        job.modality, job.compute = "workflow_lora", scene.splendor_train_compute
        job.digest = out["adapter_digest"]
        job.status = (f"trained ({split}) · loss {out['final_loss']:.3f} · "
                      f"eval {out['eval_pass_lora']:.2f} vs {out['eval_pass_baseline']:.2f} "
                      f"(+{out['improvement']:.2f}) · {out['adapter_digest'][:14]}…")
        scene.splendor_lora_digest = out["adapter_digest"]
        self.report({'INFO'}, f"Workflow LoRA trained · {out['adapter_digest'][:16]}… "
                              f"(eval +{out['improvement']:.2f})")
        return {'FINISHED'}


class SPLENDOR_OT_train_clear(bpy.types.Operator):
    """Clear the job queue."""

    bl_idname = "splendor.train_clear"
    bl_label = "Clear jobs"

    def execute(self, context):
        context.scene.splendor_train_jobs.clear()
        return {'FINISHED'}


class SPLENDOR_PT_training(bpy.types.Panel):
    bl_label = "Training"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Splendor"
    bl_parent_id = "SPLENDOR_PT_harness"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.prop(scene, "splendor_train_modality", text="Modality")
        layout.prop(scene, "splendor_train_compute", text="Compute")
        layout.label(text="Dataset · captured runs + eval-scored outputs", icon='FILE_CACHE')
        row = layout.row(align=True)
        row.operator("splendor.train_enqueue", icon='PLAY')
        row.operator("splendor.train_lora", icon='OUTLINER_DATA_POINTCLOUD')
        if scene.splendor_lora_digest:
            layout.label(text=f"LoRA {scene.splendor_lora_digest[7:21]}…", icon='OUTLINER_OB_POINTCLOUD')

        for j in scene.splendor_train_jobs:
            box = layout.box()
            box.label(text=f"{j.modality} · {j.compute}")
            icon = ('CHECKMARK' if 'captured' in j.status
                    else 'ERROR' if 'unavailable' in j.status else 'TIME')
            box.label(text=j.status, icon=icon)
        if len(scene.splendor_train_jobs):
            layout.operator("splendor.train_clear", icon='X')
        layout.label(text=f"Captured library · {len(LIBRARY)} workflow(s)")


_UI = (SPLENDOR_OT_train_enqueue, SPLENDOR_OT_train_lora, SPLENDOR_OT_train_clear, SPLENDOR_PT_training)


def register():
    bpy.utils.register_class(SplendorTrainJob)
    bpy.types.Scene.splendor_train_jobs = CollectionProperty(type=SplendorTrainJob)
    bpy.types.Scene.splendor_train_modality = EnumProperty(items=_MODALITY_ENUM, default='workflow_capture')
    bpy.types.Scene.splendor_train_compute = EnumProperty(items=_COMPUTE_ENUM, default='local')
    bpy.types.Scene.splendor_lora_digest = StringProperty(name="Workflow LoRA", default="")
    for cls in _UI:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_UI):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.splendor_lora_digest
    del bpy.types.Scene.splendor_train_compute
    del bpy.types.Scene.splendor_train_modality
    del bpy.types.Scene.splendor_train_jobs
    bpy.utils.unregister_class(SplendorTrainJob)
