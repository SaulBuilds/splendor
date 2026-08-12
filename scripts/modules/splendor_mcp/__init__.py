# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor MCP — expose the governed action API to external agents, and consume
external MCP servers.

Splendor is **both** an MCP server (external agents — Claude Code, Cursor, … —
drive the scene through it) and an MCP client (it reaches other MCP servers).
Both sides speak MCP-shaped JSON-RPC 2.0 (``initialize`` / ``tools/list`` /
``tools/call``). The server routes every ``tools/call`` through the single
governed path :func:`splendor.action_api.execute` — so an external agent gets the
*same* HIC gate an in-app action does (invariant I-1). No tool is a bypass.

Surface (depth): governed tools (``set_palette``, ``snap_vertices``, ``flat_shade``),
read-only tools (``get_state``, ``eval_run`` — no gate, they never mutate), and MCP
**resources** (``resources/list`` / ``resources/read``: ``splendor://state`` ·
``tools`` · ``eval``) so an agent can read context, not just act.

Transport: the server runs inside Blender over a local TCP socket (so Blender's own
stdout logging can't corrupt the JSON-RPC stream). ``python -m splendor_mcp bridge``
is the pure-Python **stdio↔TCP bridge** real MCP clients (Claude Code, Cursor,
llama.cpp agents) launch to talk to a running Blender instance natively;
``python -m splendor_mcp config`` emits the client stanza. An in-GUI
(threaded, main-thread-marshalled) persistent server remains a follow-up.
"""
from __future__ import annotations

from . import client, server, threaded, tools

__all__ = ["client", "server", "threaded", "tools"]
__version__ = (0, 0, 3)
