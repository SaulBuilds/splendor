# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor MCP — expose the governed action API to external agents, and consume
external MCP servers.

Splendor is **both** an MCP server (external agents — Claude Code, Cursor, … —
drive the scene through it) and an MCP client (it reaches other MCP servers).
Both sides speak MCP-shaped JSON-RPC 2.0 (``initialize`` / ``tools/list`` /
``tools/call``). The server routes every ``tools/call`` through the single
governed path :func:`splendor.action_api.execute` — so an external agent gets the
*same* HIC gate an in-app action does (invariant I-1). No tool is a bypass.

Transport note (honest): this seam uses a local TCP socket, chosen so Blender's
own stdout logging can't corrupt the JSON-RPC stream. A stdio / HTTP-SSE bridge
for native Claude Code discovery, and an in-GUI (threaded, main-thread-marshalled)
server for a persistent running instance, are documented S0.x follow-ups. The
protocol shape and the governance wiring here are the real, reusable parts.
"""
from __future__ import annotations

from . import client, server, tools

__all__ = ["client", "server", "tools"]
__version__ = (0, 0, 1)
