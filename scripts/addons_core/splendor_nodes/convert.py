# SPDX-License-Identifier: GPL-2.0-or-later
"""Convert a Splendor node tree ⇄ a `splendor.graph.WorkflowGraph`.

The node editor is a *view*; the WorkflowGraph is the canonical model that
serializes to LangGraph (S0.7). `tree_to_workflow` reads the flow links and adds
the `__start__`/`__end__` sentinels; `workflow_to_tree` rebuilds the visual graph
from a workflow (used by import + round-trip). Linear flows for v1; conditional
routing (eval → apply / __end__) is a documented follow-up — the model already
supports it.
"""
from __future__ import annotations

from splendor.graph import END, START, Edge, Node, WorkflowGraph


def tree_to_workflow(tree) -> WorkflowGraph:
    ids = {}
    nodes = []
    for n in tree.nodes:
        st = getattr(n, "splendor_type", None)
        if st in (None, "generic"):
            continue
        ids[n] = n.name
        nodes.append(Node(n.name, st, n.to_config()))

    edges = []
    has_incoming, has_outgoing = set(), set()
    for link in tree.links:
        fn, tn = link.from_node, link.to_node
        if fn in ids and tn in ids:
            edges.append(Edge(ids[fn], ids[tn]))
            has_outgoing.add(ids[fn])
            has_incoming.add(ids[tn])

    all_ids = set(ids.values())
    # __start__ → every entry (no incoming); every terminal (no outgoing) → __end__.
    starts = [Edge(START, nid) for nid in sorted(all_ids - has_incoming)]
    ends = [Edge(nid, END) for nid in sorted(all_ids - has_outgoing)]
    return WorkflowGraph(nodes, starts + edges + ends)


_TYPE_TO_BL = {
    "prompt": "SPLENDOR_ND_prompt",
    "model": "SPLENDOR_ND_model",
    "eval": "SPLENDOR_ND_eval",
    "apply": "SPLENDOR_ND_apply",
}


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
        # restore known config
        if node.type == "prompt":
            bn.text = node.config.get("text", bn.text)
        elif node.type == "eval":
            bn.palette = int(node.config.get("subject", {}).get("palette_colors", bn.palette))
            bn.tri_budget = int(node.config.get("tri_budget", bn.tri_budget))
        made[node.id] = bn

    for edge in workflow.edges:
        if edge.source in (START,) or edge.target in (END,):
            continue
        a, b = made.get(edge.source), made.get(edge.target)
        if a and b and a.outputs and b.inputs:
            tree.links.new(a.outputs[0], b.inputs[0])
