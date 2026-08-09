# SPDX-License-Identifier: GPL-2.0-or-later
"""A small, LangGraph-shaped executor for a workflow graph.

Walks from ``__start__`` to ``__end__``, running each node's handler and taking
conditional edges by state. Handlers are pluggable so the graph module stays
decoupled: :func:`default_handlers` wires ``model`` → the Router (P3), ``eval`` →
the Eval SDK (P4), and ``apply`` → a caller-supplied function (which in Splendor
wraps ``action_api.execute``, P2/P6). That's how one graph composes all four
pillars — the point of the node/edge language.
"""
from __future__ import annotations

from collections import defaultdict

from .model import END, START
from .validate import validate


class GraphExecutionError(RuntimeError):
    pass


def _choose(edges, state):
    for e in edges:
        if e.condition is not None:
            return e.target if state.get(e.condition["when"]) else e.condition["else"]
    return edges[0].target


def run(graph, handlers, state=None, max_steps: int = 1000):
    validate(graph)
    nodes = {n.id: n for n in graph.nodes}
    adj = defaultdict(list)
    for e in graph.edges:
        adj[e.source].append(e)

    state = dict(state or {})
    trace = []
    cur = START
    steps = 0
    while cur != END:
        steps += 1
        if steps > max_steps:
            raise GraphExecutionError("max steps exceeded (cycle without reaching __end__?)")
        if cur != START:
            node = nodes[cur]
            handler = handlers.get(node.type)
            if handler is None:
                raise GraphExecutionError(f"no handler for node type {node.type!r}")
            state = handler(node, state)
            trace.append(cur)
        outs = adj.get(cur)
        if not outs:
            raise GraphExecutionError(f"no outgoing edge from {cur!r}")
        cur = _choose(outs, state)
    state["_trace"] = trace
    return state


def default_handlers(router=None, harness=None, apply_fn=None):
    """Handlers that back the node types with the real pillars."""

    def h_prompt(node, state):
        state["prompt"] = node.config.get("text", state.get("prompt", ""))
        return state

    def h_model(node, state):
        from splendor.models import CompletionRequest, Message
        if router is None:
            raise GraphExecutionError("model node needs a router")
        res = router.complete(CompletionRequest(messages=[Message("user", state.get("prompt", ""))]))
        state["completion"] = res.text
        state["model_backend"] = res.backend
        return state

    def h_eval(node, state):
        if harness is None:
            raise GraphExecutionError("eval node needs an eval harness")
        subject = node.config.get("subject") or state.get("subject") or {}
        rec = harness.evaluate(subject, node.config.get("subject_id", "wf"),
                               seed=node.config.get("seed", 0))
        state["eval_passed"] = rec.passed_all
        state["eval_digest"] = rec.digest
        return state

    def h_apply(node, state):
        state["applied"] = True
        if apply_fn is not None:
            state["apply_result"] = apply_fn(node, state)
        return state

    return {"prompt": h_prompt, "model": h_model, "eval": h_eval, "apply": h_apply}
