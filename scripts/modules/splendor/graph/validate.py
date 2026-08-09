# SPDX-License-Identifier: GPL-2.0-or-later
"""Workflow-graph validation.

A hand-edited or malformed graph must fail *on import*, not load as a broken
graph that misbehaves later (the S0.7 negative control). Checks: unique non-empty
non-sentinel node ids; known node types; every edge references a real node or the
right sentinel; a start edge and a reachable end; no dangling (unreachable) nodes.
"""
from __future__ import annotations

from .model import END, KNOWN_TYPES, START


class GraphValidationError(ValueError):
    pass


def validate(graph, known_types=KNOWN_TYPES):
    ids = graph.node_ids()

    # 1. Node ids: unique, non-empty, not sentinels.
    seen = set()
    for n in graph.nodes:
        if not n.id:
            raise GraphValidationError("node with empty id")
        if n.id in (START, END):
            raise GraphValidationError(f"node id may not be a sentinel: {n.id!r}")
        if n.id in seen:
            raise GraphValidationError(f"duplicate node id: {n.id!r}")
        seen.add(n.id)
        if n.type not in known_types:
            raise GraphValidationError(f"unknown node type {n.type!r} (node {n.id!r})")

    valid_sources = set(ids) | {START}
    valid_targets = set(ids) | {END}

    # 2. Edges reference real nodes / correct sentinels.
    start_edges = 0
    end_edges = 0
    for e in graph.edges:
        if e.source not in valid_sources:
            raise GraphValidationError(f"edge from unknown node {e.source!r}")
        if e.target not in valid_targets:
            raise GraphValidationError(f"edge to unknown node {e.target!r}")
        if e.source == START:
            start_edges += 1
        if e.target == END:
            end_edges += 1
        if e.condition is not None:
            if "when" not in e.condition or "else" not in e.condition:
                raise GraphValidationError(
                    f"conditional edge {e.source!r}->{e.target!r} needs 'when' and 'else'")
            alt = e.condition["else"]
            if alt not in valid_targets:
                raise GraphValidationError(f"conditional 'else' targets unknown node {alt!r}")

    if start_edges == 0:
        raise GraphValidationError(f"no edge from {START}")
    if end_edges == 0:
        raise GraphValidationError(f"no edge reaches {END}")

    # 3. Reachability from START (dangling nodes are a defect).
    reachable = _reachable_from(START, graph)
    dangling = set(ids) - reachable
    if dangling:
        raise GraphValidationError(f"unreachable node(s): {sorted(dangling)}")
    if END not in reachable:
        raise GraphValidationError(f"{END} is not reachable")

    return True


def _reachable_from(start, graph):
    adj = {}
    for e in graph.edges:
        adj.setdefault(e.source, [])
        adj[e.source].append(e.target)
        if e.condition is not None:
            adj[e.source].append(e.condition["else"])
    seen = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        for nxt in adj.get(cur, []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen
