# SPDX-License-Identifier: GPL-2.0-or-later
"""Convert a Splendor node tree ⇄ a `splendor.graph.WorkflowGraph`.

The node editor is a *view*; the WorkflowGraph is the canonical model that
serializes to LangGraph (S0.7). `tree_to_workflow` reads the flow links, turns the
eval node's ``pass``/``else`` outputs into a **conditional edge**
(``when: eval_passed``, else → the else-target or ``__end__``), and adds the
``__start__``/``__end__`` sentinels. `workflow_to_tree` rebuilds the visual graph
(used by import + round-trip).
"""
from __future__ import annotations

from collections import defaultdict

from splendor.graph import END, START, Edge, Node, WorkflowGraph


def _splendor_nodes(tree):
    return {n: n.name for n in tree.nodes if getattr(n, "splendor_type", None) not in (None, "generic")}


def tree_to_workflow(tree) -> WorkflowGraph:
    ids = _splendor_nodes(tree)
    nodes = [Node(name, n.splendor_type, n.to_config()) for n, name in ids.items()]

    # from_node -> [(from_socket_name, to_node)]
    out_links = defaultdict(list)
    for link in tree.links:
        fn, tn = link.from_node, link.to_node
        if fn in ids and tn in ids:
            out_links[fn].append((link.from_socket.name, tn))

    edges = []
    has_incoming, has_outgoing = set(), set()
    for n, name in ids.items():
        outs = out_links.get(n, [])
        if n.splendor_type == "eval":
            pass_t = next((ids[tn] for sock, tn in outs if sock == "pass"), None)
            else_t = next((ids[tn] for sock, tn in outs if sock == "else"), None)
            if pass_t is not None:
                edges.append(Edge(name, pass_t, condition={
                    "when": "eval_passed", "else": else_t if else_t is not None else END}))
                has_outgoing.add(name)
                has_incoming.add(pass_t)
                if else_t is not None:
                    has_incoming.add(else_t)
            elif else_t is not None:   # only the else wire is connected
                edges.append(Edge(name, else_t))
                has_outgoing.add(name)
                has_incoming.add(else_t)
        else:
            for _sock, tn in outs:
                edges.append(Edge(name, ids[tn]))
                has_outgoing.add(name)
                has_incoming.add(ids[tn])

    all_ids = set(ids.values())
    starts = [Edge(START, nid) for nid in sorted(all_ids - has_incoming)]
    ends = [Edge(nid, END) for nid in sorted(all_ids - has_outgoing)]
    return WorkflowGraph(nodes, starts + edges + ends)


_TYPE_TO_BL = {
    "prompt": "SPLENDOR_ND_prompt",
    "model": "SPLENDOR_ND_model",
    "eval": "SPLENDOR_ND_eval",
    "apply": "SPLENDOR_ND_apply",
}


def _socket(node, name):
    return node.outputs.get(name) or (node.outputs[0] if node.outputs else None)


def workflow_to_tree(tree, workflow) -> None:
    """Rebuild the node tree from a workflow (clears the tree first)."""
    tree.nodes.clear()
    made = {}
    x = 0
    for node in workflow.nodes:
        bl = _TYPE_TO_BL.get(node.type)
        if bl is None:
            continue
        bn = tree.nodes.new(bl)
        bn.name = node.id
        bn.label = node.id
        bn.location = (x, 0)
        x += 220
        if node.type == "prompt":
            bn.text = node.config.get("text", bn.text)
        elif node.type == "eval":
            subj = node.config.get("subject", {})
            bn.palette = int(node.config.get("palette_cap", bn.palette))
            bn.tri_budget = int(node.config.get("tri_budget", bn.tri_budget))
            bn.measured_tris = int(subj.get("tri_count", bn.measured_tris))
            bn.measured_palette = int(subj.get("palette_colors", bn.measured_palette))
        made[node.id] = bn

    for edge in workflow.edges:
        a = made.get(edge.source)
        if a is None:   # __start__
            continue
        if edge.condition is not None and a.bl_idname == "SPLENDOR_ND_eval":
            pass_t = made.get(edge.target)
            if pass_t:
                tree.links.new(_socket(a, "pass"), pass_t.inputs[0])
            else_t = made.get(edge.condition.get("else"))
            if else_t:
                tree.links.new(_socket(a, "else"), else_t.inputs[0])
        else:
            b = made.get(edge.target)
            if b is None:   # __end__
                continue
            if a.outputs and b.inputs:
                tree.links.new(a.outputs[0], b.inputs[0])
