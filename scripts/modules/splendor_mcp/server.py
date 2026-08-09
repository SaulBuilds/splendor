# SPDX-License-Identifier: GPL-2.0-or-later
"""The Splendor MCP server.

Handles the MCP method set (``initialize`` / ``notifications/initialized`` /
``tools/list`` / ``tools/call``) as JSON-RPC 2.0, newline-delimited, over a
socket. Every ``tools/call`` is dispatched to :func:`splendor.action_api.execute`
with the session's grant — so an external agent is governed by the *same* HIC
gate as an in-app action (I-1). A blocked verdict returns ``isError: true`` with
the rule code, so the agent learns it needs approval rather than being silently
denied.

The session grant comes from ``SPLENDOR_MCP_GRANT`` (e.g. ``budgeted:geometry,
scene_config``). **Default is no grant** — external agents are ungoverned by
default, so their actions require approval (HIC-1). Safe by default, on purpose.
"""
from __future__ import annotations

import json
import os
import socket

import splendor
from splendor import hic
from . import tools as _tools

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "splendor-mcp", "version": "0.0.1"}

_LEVELS = {
    "observed": hic.HicLevel.OBSERVED,
    "approve_each": hic.HicLevel.APPROVE_EACH,
    "budgeted": hic.HicLevel.BUDGETED,
    "post_hoc": hic.HicLevel.POST_HOC,
}


def grant_from_env(env=None):
    """Build a session Grant from ``SPLENDOR_MCP_GRANT`` (``level:cls1,cls2``) or None."""
    env = env or os.environ
    spec = env.get("SPLENDOR_MCP_GRANT")
    if not spec:
        return None
    level_name, _, classes = spec.partition(":")
    level = _LEVELS.get(level_name.strip().lower(), hic.HicLevel.BUDGETED)
    cls = frozenset(c.strip() for c in classes.split(",") if c.strip())
    return hic.Grant("mcp-session", "mcp:external", level, cls)


def _result(mid, result):
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _error(mid, code, message):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


class MCPServer:
    def __init__(self, principal="mcp:external", grant=None):
        self.principal = principal
        self.grant = grant

    def handle(self, msg):
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}
        if method == "initialize":
            return _result(mid, {"protocolVersion": PROTOCOL_VERSION,
                                 "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO})
        if method == "notifications/initialized":
            return None  # a notification — no response
        if method == "tools/list":
            return _result(mid, {"tools": _tools.list_specs()})
        if method == "tools/call":
            return self._call(mid, params)
        if mid is not None:
            return _error(mid, -32601, f"method not found: {method}")
        return None

    def _call(self, mid, params):
        name = params.get("name")
        args = params.get("arguments") or {}
        spec = _tools.get(name)
        if spec is None:
            return _error(mid, -32602, f"unknown tool: {name}")
        try:
            intent, ctx = spec.build(args)
        except Exception as exc:
            return _result(mid, {"content": [{"type": "text", "text": f"invalid arguments: {exc}"}],
                                 "isError": True})
        # THE governed path — identical to in-app. The gate runs before any act.
        res = splendor.action_api.execute(intent, principal=self.principal, grant=self.grant, ctx=ctx)
        payload = {
            "executed": res.executed,
            "verdict": res.verdict.value,
            "rule_code": res.record.rule_code,
            "hic_level": res.record.hic_level.name,
            "reason": res.record.reason,
            "outcome": res.outcome,
        }
        if spec.verify is not None:
            try:
                payload["verify"] = spec.verify(ctx)
            except Exception as exc:
                payload["verify_error"] = str(exc)
        return _result(mid, {"content": [{"type": "text", "text": json.dumps(payload)}],
                             "isError": not res.executed})


def serve_socket(host="127.0.0.1", port=0, port_file=None, principal="mcp:external", grant=None):
    """Serve one MCP client connection over a socket. Returns the bound port.

    Runs on the calling (main) thread — intended for ``blender --background`` where
    no GUI loop competes and ``bpy`` runs synchronously on this thread.
    """
    srv = MCPServer(principal, grant)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(1)
    bound = sock.getsockname()[1]
    if port_file:
        with open(port_file, "w") as fh:
            fh.write(str(bound))
    conn, _ = sock.accept()
    reader = conn.makefile("rb")
    writer = conn.makefile("wb")
    try:
        while True:
            line = reader.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            resp = srv.handle(msg)
            if resp is not None:
                writer.write((json.dumps(resp) + "\n").encode())
                writer.flush()
    finally:
        conn.close()
        sock.close()
    return bound
