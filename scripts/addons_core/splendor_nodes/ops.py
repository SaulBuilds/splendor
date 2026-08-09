# SPDX-License-Identifier: GPL-2.0-or-later
"""Node-editor operators + testable helpers.

The heavy lifting is module functions (`new_starter_tree`, `serialize_tree`,
`run_workflow`) so they can be verified headlessly; the operators are thin wrappers
that read the active node tree. Serialize → S0.7 LangGraph artifact (validates on
the way out). Run → `splendor.graph.run_graph` across Router (P3) + Eval SDK (P4).
"""
from __future__ import annotations

import json
import os

import bpy

import splendor_eval as ev
from splendor.graph import GraphExecutionError, default_handlers, dumps, run_graph, to_langgraph
from splendor.graph.validate import GraphValidationError
from splendor.models import BackendUnavailable, OpenAICompatBackend, Router

from . import convert


def new_starter_tree(name="Splendor Workflow"):
    """A linked prompt → model → eval → apply starter tree (newcomer on-ramp)."""
    tree = bpy.data.node_groups.new(name, "SplendorNodeTree")
    p = tree.nodes.new("SPLENDOR_ND_prompt"); p.location = (0, 0)
    m = tree.nodes.new("SPLENDOR_ND_model"); m.location = (220, 0)
    e = tree.nodes.new("SPLENDOR_ND_eval"); e.location = (440, 0)
    a = tree.nodes.new("SPLENDOR_ND_apply"); a.location = (660, 0)
    tree.links.new(p.outputs[0], m.inputs[0])
    tree.links.new(m.outputs[0], e.inputs[0])
    tree.links.new(e.outputs["pass"], a.inputs[0])   # else → __end__ (skips apply on fail)
    return tree


def serialize_tree(tree):
    """(artifact_dict, workflow). Raises GraphValidationError on a broken graph."""
    workflow = convert.tree_to_workflow(tree)
    artifact = to_langgraph(workflow)   # to_langgraph does not validate; validate explicitly
    from splendor.graph.validate import validate as _validate
    _validate(workflow)
    return artifact, workflow


def build_router():
    router = Router()
    url = os.environ.get("SPLENDOR_MODEL_URL")
    if url:
        router.register(OpenAICompatBackend("configured", url,
                                            os.environ.get("SPLENDOR_MODEL", "local"), is_local=True))
    router.register(OpenAICompatBackend("ollama", "http://127.0.0.1:11434/v1", "llama3", is_local=True))
    router.register(OpenAICompatBackend("llama.cpp", "http://127.0.0.1:8080/v1", "local", is_local=True))
    return router


def run_workflow(tree, router=None, apply_fn=None):
    """Convert + execute the tree across the pillars. Returns a result dict.

    Honest offline: if no model is reachable the model node raises and we report
    'offline' rather than fabricating a run.
    """
    workflow = convert.tree_to_workflow(tree)
    # Build an eval harness from the first eval node's budgets.
    tri_budget, palette = 500, 16
    for node in tree.nodes:
        if getattr(node, "splendor_type", "") == "eval":
            tri_budget, palette = int(node.tri_budget), int(node.palette)
            break
    harness = ev.EvalHarness([ev.TriBudget(tri_budget), ev.PaletteAdherence(palette)])
    applied = []
    handlers = default_handlers(
        router=router or build_router(),
        harness=harness,
        apply_fn=apply_fn or (lambda node, state: applied.append(True) or "applied"))
    try:
        state = run_graph(workflow, handlers)
        return {"ok": True, "backend": state.get("model_backend"),
                "eval_passed": state.get("eval_passed"), "applied": bool(state.get("applied")),
                "trace": state.get("_trace")}
    except BackendUnavailable as exc:
        return {"ok": False, "offline": True, "reason": str(exc)}
    except (GraphExecutionError, GraphValidationError) as exc:
        return {"ok": False, "error": str(exc)}


def _active_tree(context):
    space = getattr(context, "space_data", None)
    if space and getattr(space, "type", "") == 'NODE_EDITOR':
        tree = getattr(space, "node_tree", None)
        if tree and tree.bl_idname == "SplendorNodeTree":
            return tree
    return None


class SPLENDOR_OT_graph_new(bpy.types.Operator):
    """Create a starter Splendor workflow (prompt → model → eval → apply)."""

    bl_idname = "splendor.graph_new"
    bl_label = "New Splendor workflow"

    def execute(self, context):
        tree = new_starter_tree()
        space = getattr(context, "space_data", None)
        if space and getattr(space, "type", "") == 'NODE_EDITOR':
            space.node_tree = tree
        self.report({'INFO'}, f"Created '{tree.name}' (prompt → model → eval → apply)")
        return {'FINISHED'}


class SPLENDOR_OT_graph_serialize(bpy.types.Operator):
    """Serialize the active workflow to a LangGraph artifact (validates on export)."""

    bl_idname = "splendor.graph_serialize"
    bl_label = "Export LangGraph artifact"

    def execute(self, context):
        tree = _active_tree(context)
        if tree is None:
            self.report({'ERROR'}, "no active Splendor workflow")
            return {'CANCELLED'}
        try:
            artifact, workflow = serialize_tree(tree)
        except GraphValidationError as exc:
            self.report({'ERROR'}, f"invalid workflow: {exc}")
            return {'CANCELLED'}
        text = bpy.data.texts.get("splendor_workflow.json") or bpy.data.texts.new("splendor_workflow.json")
        text.clear()
        text.write(json.dumps(artifact, indent=2))
        self.report({'INFO'}, f"Exported {len(workflow.nodes)} nodes → splendor_workflow.json")
        return {'FINISHED'}


class SPLENDOR_OT_graph_run(bpy.types.Operator):
    """Run the active workflow across the Router + Eval SDK (honest if offline)."""

    bl_idname = "splendor.graph_run"
    bl_label = "Run workflow"

    def execute(self, context):
        tree = _active_tree(context)
        if tree is None:
            self.report({'ERROR'}, "no active Splendor workflow")
            return {'CANCELLED'}
        res = run_workflow(tree)
        if res.get("ok"):
            self.report({'INFO'}, f"Ran · model {res['backend']} · eval "
                                  f"{'pass' if res['eval_passed'] else 'fail'} · applied {res['applied']}")
        elif res.get("offline"):
            self.report({'WARNING'}, "No local model reachable — offline (honest)")
        else:
            self.report({'ERROR'}, res.get("error", "run failed"))
        return {'FINISHED'}


CLASSES = (SPLENDOR_OT_graph_new, SPLENDOR_OT_graph_serialize, SPLENDOR_OT_graph_run)
