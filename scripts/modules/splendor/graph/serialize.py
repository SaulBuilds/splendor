# SPDX-License-Identifier: GPL-2.0-or-later
"""LangGraph-compatible serialization (D-6.2 / D-7.1).

The artifact maps 1:1 onto a LangGraph ``StateGraph``: the ``nodes`` list →
``add_node``; ``edges`` with plain ``source``/``target`` → ``add_edge`` (using
LangGraph's ``__start__`` / ``__end__`` sentinels); edges carrying a
``condition`` → ``add_conditional_edges``. So a Splendor node graph authored in
the Blender node editor exports to something the AI-dev ecosystem can run, and
round-trips back byte-for-byte.
"""
from __future__ import annotations

import json

from .model import Edge, Node, WorkflowGraph, START, END
from .validate import validate

SCHEMA = "splendor.workflow/v1"


def to_langgraph(graph) -> dict:
    return {
        "schema": SCHEMA,
        "start": START,
        "end": END,
        "nodes": [{"id": n.id, "type": n.type, "config": n.config} for n in graph.nodes],
        "edges": [
            {"source": e.source, "target": e.target, "condition": e.condition}
            for e in graph.edges
        ],
    }


def from_langgraph(data, do_validate: bool = True) -> WorkflowGraph:
    if isinstance(data, str):
        data = json.loads(data)
    if data.get("schema") != SCHEMA:
        # Not fatal, but be explicit about what we're reading.
        pass
    try:
        nodes = [Node(n["id"], n["type"], dict(n.get("config") or {})) for n in data["nodes"]]
        edges = [
            Edge(e["source"], e["target"], e.get("condition"))
            for e in data["edges"]
        ]
    except (KeyError, TypeError) as exc:
        from .validate import GraphValidationError
        raise GraphValidationError(f"malformed workflow artifact: {exc}") from exc
    graph = WorkflowGraph(nodes, edges)
    if do_validate:
        validate(graph)   # fail on import, don't load a broken graph
    return graph


def dumps(graph) -> str:
    return json.dumps(to_langgraph(graph), sort_keys=True, separators=(",", ":"))
