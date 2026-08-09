# SPDX-License-Identifier: GPL-2.0-or-later
"""A minimal MCP client — Splendor consuming an MCP server.

Pure Python (no ``bpy``): the in-app agent / harness uses this to reach external
MCP servers, and the S0.4 test uses it to drive the Splendor server. Speaks
MCP-shaped JSON-RPC 2.0, newline-delimited, over a socket.
"""
from __future__ import annotations

import json
import socket


class MCPClient:
    def __init__(self, sock: socket.socket):
        self._sock = sock
        self._reader = sock.makefile("rb")
        self._writer = sock.makefile("wb")
        self._id = 0

    @classmethod
    def connect(cls, host="127.0.0.1", port=0, timeout=10.0):
        return cls(socket.create_connection((host, port), timeout=timeout))

    def _send(self, method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self._id += 1
            msg["id"] = self._id
        self._writer.write((json.dumps(msg) + "\n").encode())
        self._writer.flush()
        if notify:
            return None
        line = self._reader.readline()
        if not line:
            raise ConnectionError("MCP server closed the connection")
        return json.loads(line)

    def initialize(self):
        res = self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "splendor-client", "version": "0.0.1"},
        })
        self._send("notifications/initialized", notify=True)
        return res

    def list_tools(self):
        return self._send("tools/list")

    def call_tool(self, name, arguments):
        return self._send("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        for closable in (self._writer, self._reader, self._sock):
            try:
                closable.close()
            except Exception:
                pass
