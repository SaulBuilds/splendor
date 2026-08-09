# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor node/edge workflow language (P5).

Author a prompt→model→eval→apply agent workflow as nodes + edges, round-trip it
to a LangGraph-compatible artifact, validate it on import, and execute it across
the Router (P3), Eval SDK (P4), and action API (P2/P6). One language for the
Blender node editor and the MCP harness (D-6.2). Pure Python — bpy-independent.
"""
from __future__ import annotations

from . import model, run, serialize, validate
from .model import Edge, END, KNOWN_TYPES, Node, START, WorkflowGraph
from .run import GraphExecutionError, default_handlers, run as run_graph
from .serialize import SCHEMA, dumps, from_langgraph, to_langgraph
from .validate import GraphValidationError, validate as validate_graph

__all__ = [
    "model", "run", "serialize", "validate",
    "Edge", "END", "KNOWN_TYPES", "Node", "START", "WorkflowGraph",
    "GraphExecutionError", "default_handlers", "run_graph",
    "SCHEMA", "dumps", "from_langgraph", "to_langgraph",
    "GraphValidationError", "validate_graph",
]
__version__ = (0, 0, 1)
