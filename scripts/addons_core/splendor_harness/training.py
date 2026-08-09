# SPDX-License-Identifier: GPL-2.0-or-later
"""Training Panel (SPL-S3) — modality picker · compute source · dataset · job queue.

Workflow capture is real (saves the current run's workflow to a content-hashed
library — weightless training, D-3.1). Weight-based modalities enqueue an honest
job ("trainer not yet wired"); cloud / Citrate-DePIN compute (D-3.2) reports
availability truthfully. Nothing here fakes a trained model.
"""
from __future__ import annotations

import os

import bpy
from bpy.props import CollectionProperty, EnumProperty, StringProperty

from splendor import train as _train
from splendor.graph import END, START, Edge, Node, WorkflowGraph

_MODALITY_ENUM = [
    ('diffusion_lora', "Diffusion LoRA", "Train a style LoRA from your renders"),
    ('llm_lora', "LLM LoRA", "Fine-tune the local model on your workflows"),
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
        else:
            job.status = _train.job_status(mod, comp, os.environ)
            self.report({'INFO'}, job.status)
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
        layout.operator("splendor.train_enqueue", icon='PLAY')

        for j in scene.splendor_train_jobs:
            box = layout.box()
            box.label(text=f"{j.modality} · {j.compute}")
            icon = ('CHECKMARK' if 'captured' in j.status
                    else 'ERROR' if 'unavailable' in j.status else 'TIME')
            box.label(text=j.status, icon=icon)
        if len(scene.splendor_train_jobs):
            layout.operator("splendor.train_clear", icon='X')
        layout.label(text=f"Captured library · {len(LIBRARY)} workflow(s)")


_UI = (SPLENDOR_OT_train_enqueue, SPLENDOR_OT_train_clear, SPLENDOR_PT_training)


def register():
    bpy.utils.register_class(SplendorTrainJob)
    bpy.types.Scene.splendor_train_jobs = CollectionProperty(type=SplendorTrainJob)
    bpy.types.Scene.splendor_train_modality = EnumProperty(items=_MODALITY_ENUM, default='workflow_capture')
    bpy.types.Scene.splendor_train_compute = EnumProperty(items=_COMPUTE_ENUM, default='local')
    for cls in _UI:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_UI):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.splendor_train_compute
    del bpy.types.Scene.splendor_train_modality
    del bpy.types.Scene.splendor_train_jobs
    bpy.utils.unregister_class(SplendorTrainJob)
