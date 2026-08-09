# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S2 node editor test — the visual workflow editor wired to splendor.graph.

    blender --background --factory-startup --python tests/splendor/test_spl_s2_nodes.py

Exits non-zero on any failure. A prompt→model→eval→apply node tree round-trips to
a LangGraph artifact, runs across the Router (P3) + Eval SDK (P4), reports honestly
when offline, and a cyclic/no-entry tree fails validation on export.
"""
import json
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))
sys.path.insert(0, os.path.dirname(__file__))

import bpy  # noqa: E402
import splendor_nodes  # noqa: E402
from splendor_nodes import convert, ops  # noqa: E402
from splendor.graph import dumps, from_langgraph  # noqa: E402
from splendor.graph.validate import GraphValidationError  # noqa: E402
from splendor.models import OpenAICompatBackend, Router  # noqa: E402
import _openai_compat_server  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    os.environ.pop("SPLENDOR_MODEL_URL", None)
    splendor_nodes.register()
    try:
        # Registration proven functionally (bpy.types.hasattr is unreliable for node types).
        reg = bpy.data.node_groups.new("reg-check", "SplendorNodeTree")
        check(reg.bl_idname == "SplendorNodeTree", "SplendorNodeTree registered (creatable)")
        for bl in ("SPLENDOR_ND_prompt", "SPLENDOR_ND_model", "SPLENDOR_ND_eval", "SPLENDOR_ND_apply"):
            check(reg.nodes.new(bl).bl_idname == bl, f"{bl} registered")
        bpy.data.node_groups.remove(reg)
        check(hasattr(bpy.types, "SPLENDOR_PT_nodes"), "SPLENDOR_PT_nodes registered")

        print("[1] Starter tree: prompt → model → eval → apply")
        tree = ops.new_starter_tree("wf-test")
        types = sorted(getattr(n, "splendor_type", "?") for n in tree.nodes)
        check(len(tree.nodes) == 4 and len(tree.links) == 3, f"4 nodes, 3 links ({types})")

        print("[2] Tree → WorkflowGraph → LangGraph artifact, validates + round-trips")
        artifact, workflow = ops.serialize_tree(tree)
        check(len(workflow.nodes) == 4, "workflow has 4 nodes")
        srcs = {e.source for e in workflow.edges}
        tgts = {e.target for e in workflow.edges}
        check("__start__" in srcs and "__end__" in tgts, "START/END sentinels added from the flow links")
        back = from_langgraph(json.dumps(artifact))
        check(dumps(workflow) == dumps(back), "round-trips byte-identically (S0.7 seam)")
        check(any(e.condition for e in workflow.edges), "eval emits a conditional edge (pass / else→__end__)")

        print("[3] Visual round-trip: workflow → tree → workflow is stable")
        tree2 = bpy.data.node_groups.new("wf-rebuilt", "SplendorNodeTree")
        convert.workflow_to_tree(tree2, workflow)
        check(len(tree2.nodes) == 4 and len(tree2.links) == 3, "rebuilt tree has 4 nodes, 3 links")
        check(dumps(convert.tree_to_workflow(tree2)) == dumps(workflow), "rebuilt tree yields the same workflow")

        print("[4] Run online: executes across Router (P3) + Eval SDK (P4)")
        _srv, port = _openai_compat_server.start(reply="PLAN: box, snap, palette 16")
        router = Router([OpenAICompatBackend("fix", f"http://127.0.0.1:{port}/v1", "m", is_local=True)])
        res = ops.run_workflow(tree, router=router)
        check(res.get("ok") and res.get("backend") == "fix", "ran; model node used the local backend")
        check(res.get("eval_passed") is True and res.get("applied") is True, "eval passed + apply ran")
        tmap = {n.id: n.type for n in workflow.nodes}
        check([tmap[i] for i in (res.get("trace") or [])] == ["prompt", "model", "eval", "apply"],
              "PASS path trace: prompt→model→eval→apply (eval passed → apply)")

        print("[4b] Conditional FALSE path: eval fails → routes to __end__, apply skipped")
        tree_f = ops.new_starter_tree("wf-fail")
        for n in tree_f.nodes:
            if getattr(n, "splendor_type", "") == "eval":
                n.measured_palette = 20   # > cap 16 → fails PaletteAdherence
        res_f = ops.run_workflow(tree_f, router=router)
        check(res_f.get("ok") and res_f.get("eval_passed") is False, "eval failed (20 > 16 cap)")
        wf_f = convert.tree_to_workflow(tree_f)
        tmap_f = {n.id: n.type for n in wf_f.nodes}
        check([tmap_f[i] for i in (res_f.get("trace") or [])] == ["prompt", "model", "eval"],
              "FALSE path trace stops at eval (routed to __end__)")
        check(res_f.get("applied") is False, "apply did NOT run on the fail path")

        print("[5] Run offline: honest, no fabricated run")
        dead = Router([OpenAICompatBackend("dead", "http://127.0.0.1:1/v1", "x", is_local=True)])
        res_off = ops.run_workflow(tree, router=dead)
        check(not res_off.get("ok") and res_off.get("offline"), "no reachable model → offline (honest)")

        print("[6] NEG CONTROL: a cyclic / no-entry tree fails validation on export")
        bad = bpy.data.node_groups.new("wf-bad", "SplendorNodeTree")
        m = bad.nodes.new("SPLENDOR_ND_model")
        e = bad.nodes.new("SPLENDOR_ND_eval")
        bad.links.new(m.outputs[0], e.inputs[0])
        bad.links.new(e.outputs[0], m.inputs[0])   # cycle → no __start__, no __end__
        try:
            ops.serialize_tree(bad)
            check(False, "cyclic tree should fail validation")
        except GraphValidationError:
            check(True, "cyclic/no-entry tree → GraphValidationError on export (not a broken graph)")
    finally:
        splendor_nodes.unregister()
        check(not hasattr(bpy.types, "SPLENDOR_PT_nodes"), "clean unregister")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — SPL-S2 node editor ⇄ LangGraph + run across pillars verified")
    sys.exit(0)


if __name__ == "__main__":
    main()
