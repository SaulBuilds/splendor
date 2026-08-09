# SPDX-License-Identifier: GPL-2.0-or-later
"""The node/edge workflow model (P5).

One visual language, two homes: the Blender node editor and the MCP harness
(D-6.2). A :class:`WorkflowGraph` is nodes (typed, with config) + edges (data
flow / transitions — "edges"). It expresses LangGraph-style agent patterns
(prompt → model → eval → apply, with conditional routing) and round-trips to a
LangGraph-compatible artifact (see :mod:`splendor.graph.serialize`). Pure data —
execution is :mod:`splendor.graph.run`, validation is
:mod:`splendor.graph.validate`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# LangGraph sentinels — the graph's entry and terminal.
START = "__start__"
END = "__end__"

# Node types this seam understands. The Router (P3), Eval SDK (P4), and action
# API (P2/P6) back the model/eval/apply nodes respectively.
KNOWN_TYPES = frozenset({"prompt", "model", "eval", "apply", "branch"})


@dataclass
class Node:
    id: str
    type: str
    config: dict = field(default_factory=dict)


@dataclass
class Edge:
    source: str
    target: str
    # A conditional edge: {"when": <state key>, "else": <target>}. When present,
    # `target` is taken if state[when] is truthy, else the "else" target.
    condition: Optional[dict] = None


@dataclass
class WorkflowGraph:
    nodes: list = field(default_factory=list)   # list[Node]
    edges: list = field(default_factory=list)   # list[Edge]

    def node_ids(self):
        return [n.id for n in self.nodes]

    def node(self, node_id):
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None
