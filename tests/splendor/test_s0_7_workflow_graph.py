# SPDX-License-Identifier: GPL-2.0-or-later
"""S0.7 acceptance test — node/edge workflow graph ⇄ LangGraph.

Pure Python:  python3 tests/splendor/test_s0_7_workflow_graph.py

Exits non-zero on any failure. Acceptance: a prompt→model→eval→apply graph
serializes to a LangGraph-compatible artifact and round-trips back identically;
a hand-edited invalid graph fails validation ON IMPORT (not loaded broken). Bonus
integration: the graph executes across the Router (P3) + Eval SDK (P4).
"""
import json
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.dirname(__file__))

from splendor.graph import (  # noqa: E402
    Edge, END, Node, START, WorkflowGraph, default_handlers, dumps, from_langgraph,
    run_graph, to_langgraph, validate_graph,
)
from splendor.graph.validate import GraphValidationError  # noqa: E402
from splendor.models import OpenAICompatBackend, Router  # noqa: E402
from splendor_eval import EvalHarness, PaletteAdherence  # noqa: E402
import _openai_compat_server  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def build_graph(eval_subject):
    return WorkflowGraph(
        nodes=[
            Node("prompt", "prompt", {"text": "make a PS1 potion, ≤16 colors"}),
            Node("model", "model", {}),
            Node("eval", "eval", {"subject": eval_subject, "subject_id": "potion"}),
            Node("apply", "apply", {}),
        ],
        edges=[
            Edge(START, "prompt"),
            Edge("prompt", "model"),
            Edge("model", "eval"),
            Edge("eval", "apply", condition={"when": "eval_passed", "else": END}),
            Edge("apply", END),
        ],
    )


def test_validates_and_roundtrips():
    print("[1] Graph validates + round-trips to a LangGraph-compatible artifact")
    g = build_graph({"palette_colors": 16})
    check(validate_graph(g), "prompt→model→eval→apply validates")
    art = to_langgraph(g)
    check(art["start"] == START and art["end"] == END, "artifact uses LangGraph __start__/__end__ sentinels")
    check(isinstance(art["nodes"], list) and isinstance(art["edges"], list), "nodes[] + edges[] lists")
    cond = [e for e in art["edges"] if e["condition"]]
    check(len(cond) == 1 and cond[0]["condition"]["when"] == "eval_passed", "conditional edge preserved")
    g2 = from_langgraph(json.dumps(art))
    check(dumps(g) == dumps(g2), "round-trip is byte-identical (graph → artifact → graph)")


def test_invalid_graph_fails_on_import():
    print("[2] NEG CONTROL: hand-edited invalid graphs fail validation ON IMPORT")
    good = to_langgraph(build_graph({"palette_colors": 16}))

    dangling = json.loads(json.dumps(good))
    dangling["edges"][1]["target"] = "ghost_node"   # points at a nonexistent node
    try:
        from_langgraph(dangling); check(False, "dangling edge should raise")
    except GraphValidationError:
        check(True, "edge to unknown node → GraphValidationError")

    bad_type = json.loads(json.dumps(good))
    bad_type["nodes"][1]["type"] = "wormhole"        # unknown node type
    try:
        from_langgraph(bad_type); check(False, "unknown type should raise")
    except GraphValidationError:
        check(True, "unknown node type → GraphValidationError")

    no_start = json.loads(json.dumps(good))
    no_start["edges"] = [e for e in no_start["edges"] if e["source"] != START]
    try:
        from_langgraph(no_start); check(False, "missing start edge should raise")
    except GraphValidationError:
        check(True, "no edge from __start__ → GraphValidationError")

    malformed = {"schema": "splendor.workflow/v1", "nodes": [{"id": "x"}], "edges": []}
    try:
        from_langgraph(malformed); check(False, "malformed artifact should raise")
    except GraphValidationError:
        check(True, "malformed artifact (missing keys) → GraphValidationError")


def _router():
    _srv, port = _openai_compat_server.start(reply="PLAN: box → snap → palette 16")
    return Router([OpenAICompatBackend("local", f"http://127.0.0.1:{port}/v1", "m", is_local=True)])


def test_executes_across_pillars_pass_path():
    print("[3] Executes across Router (P3) + Eval SDK (P4): eval passes → apply runs")
    applied = []
    handlers = default_handlers(
        router=_router(),
        harness=EvalHarness([PaletteAdherence(16)]),
        apply_fn=lambda node, state: applied.append(state["completion"]) or "ok")
    g = build_graph({"palette_colors": 16})     # within cap → eval passes
    state = run_graph(g, handlers)
    check("PLAN" in state.get("completion", ""), "model node called the Router (real completion)")
    check(state.get("eval_passed") is True, "eval node passed via the Eval SDK")
    check(state.get("applied") is True and applied, "conditional routed to apply; apply ran")
    check(state["_trace"] == ["prompt", "model", "eval", "apply"], "full trace prompt→model→eval→apply")


def test_conditional_false_path_skips_apply():
    print("[4] NEG CONTROL: eval fails → conditional routes to __end__, apply is skipped")
    handlers = default_handlers(
        router=_router(),
        harness=EvalHarness([PaletteAdherence(16)]),
        apply_fn=lambda node, state: "should-not-run")
    g = build_graph({"palette_colors": 17})     # over cap → eval fails
    state = run_graph(g, handlers)
    check(state.get("eval_passed") is False, "eval failed (17 > 16)")
    check("applied" not in state, "apply node did NOT run")
    check(state["_trace"] == ["prompt", "model", "eval"], "trace stops at eval (routed to __end__)")


def main():
    for t in (test_validates_and_roundtrips, test_invalid_graph_fails_on_import,
              test_executes_across_pillars_pass_path, test_conditional_false_path_skips_apply):
        t()
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — S0.7 node/edge ⇄ LangGraph verified (round-trip, validate-on-import, execution)")
    sys.exit(0)


if __name__ == "__main__":
    main()
